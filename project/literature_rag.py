from __future__ import annotations

import argparse
import json
import math
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "literature"
CLEAN_ARTICLES_JSONL = DATA_DIR / "google_scholar_articles_clean.jsonl"
PDF_DOWNLOADS_JSONL = DATA_DIR / "google_scholar_pdf_downloads.jsonl"
PDF_DIR = DATA_DIR / "pdfs"
TEXT_DIR = DATA_DIR / "texts"
RAG_DIR = DATA_DIR / "rag"
DOCUMENT_MANIFEST_JSONL = RAG_DIR / "document_manifest.jsonl"
PAGES_JSONL = RAG_DIR / "pages.jsonl"
CHUNKS_JSONL = RAG_DIR / "chunks.jsonl"
INDEX_PATH = RAG_DIR / "tfidf_index.joblib"
REPORT_JSON = RAG_DIR / "rag_report.json"


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")
LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def clean_text(text: str) -> str:
    for source, replacement in LIGATURES.items():
        text = text.replace(source, replacement)
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_stem(article_id: str, title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")[:72]
    return f"{article_id}_{slug or 'article'}"


def load_articles() -> dict[str, dict[str, Any]]:
    return {row["article_id"]: row for row in read_jsonl(CLEAN_ARTICLES_JSONL)}


def successful_downloads() -> dict[str, dict[str, Any]]:
    rows = read_jsonl(PDF_DOWNLOADS_JSONL)
    successful = [row for row in rows if row.get("status") in {"downloaded", "already_downloaded"}]
    by_article: dict[str, dict[str, Any]] = {}
    for row in successful:
        article_id = row["article_id"]
        path = Path(row.get("downloaded_path") or "")
        if not path.exists():
            fallback = sorted(PDF_DIR.glob(f"{article_id}_*.pdf"))
            if fallback:
                path = fallback[0]
        if not path.exists():
            continue
        current = by_article.get(article_id)
        if current is None or path.stat().st_size > Path(current["pdf_path"]).stat().st_size:
            by_article[article_id] = {
                "article_id": article_id,
                "pdf_path": str(path.resolve()),
                "pdf_url": row.get("pdf_url", ""),
                "download_host": row.get("host", ""),
                "download_status": row.get("status", ""),
                "download_bytes": path.stat().st_size,
            }
    return by_article


def extract_pdf_text(pdf_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # noqa: BLE001 - keep corpus build moving.
        return pages, {"status": "read_error", "page_count": 0, "error": f"{type(exc).__name__}: {exc}"}

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = clean_text(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001 - keep usable pages.
            text = ""
            errors.append(f"page {index}: {type(exc).__name__}: {exc}")
        pages.append({"page": index, "text": text, "char_count": len(text)})

    extracted_pages = sum(1 for page in pages if page["text"])
    status = "extracted" if extracted_pages else "empty_text"
    if errors and extracted_pages:
        status = "partial"
    return pages, {
        "status": status,
        "page_count": len(pages),
        "extracted_pages": extracted_pages,
        "char_count": sum(page["char_count"] for page in pages),
        "error": "; ".join(errors[:5]),
    }


def build_documents() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    articles = load_articles()
    downloads = successful_downloads()
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    RAG_DIR.mkdir(parents=True, exist_ok=True)

    documents: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []

    for article_id, download in sorted(downloads.items()):
        article = articles.get(article_id, {})
        title = article.get("title") or download.get("title") or article_id
        text_path = TEXT_DIR / f"{safe_stem(article_id, title)}.txt"
        pdf_path = Path(download["pdf_path"])
        pages, stats = extract_pdf_text(pdf_path)

        if pages:
            content_parts = []
            for page in pages:
                content_parts.append(f"\n\n[page {page['page']}]\n{page['text']}")
                page_rows.append(
                    {
                        "article_id": article_id,
                        "title": title,
                        "year": article.get("year", ""),
                        "page": page["page"],
                        "text": page["text"],
                        "char_count": page["char_count"],
                        "pdf_path": str(pdf_path.resolve()),
                        "text_path": str(text_path.resolve()),
                    }
                )
            text_path.write_text("".join(content_parts).strip() + "\n", encoding="utf-8")

        documents.append(
            {
                "article_id": article_id,
                "title": title,
                "year": article.get("year", ""),
                "doi": article.get("doi", ""),
                "arxiv_id": article.get("arxiv_id", ""),
                "publishers": article.get("publishers", []),
                "primary_url": article.get("primary_url", ""),
                "pdf_url": download.get("pdf_url", ""),
                "pdf_path": str(pdf_path.resolve()),
                "text_path": str(text_path.resolve()) if pages else "",
                "download_host": download.get("download_host", ""),
                "download_bytes": download.get("download_bytes", 0),
                "extraction_status": stats.get("status", ""),
                "page_count": stats.get("page_count", 0),
                "extracted_pages": stats.get("extracted_pages", 0),
                "char_count": stats.get("char_count", 0),
                "extraction_error": stats.get("error", ""),
            }
        )

    write_jsonl(DOCUMENT_MANIFEST_JSONL, documents)
    write_jsonl(PAGES_JSONL, page_rows)
    return documents, page_rows


def chunk_page_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            boundary = text.rfind(". ", start + int(chunk_size * 0.65), end)
            if boundary != -1:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
        if start >= len(text):
            break
    return chunks


def build_chunks(page_rows: list[dict[str, Any]], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    per_article_counter: Counter[str] = Counter()

    for page in page_rows:
        article_id = page["article_id"]
        for text in chunk_page_text(page["text"], chunk_size=chunk_size, overlap=overlap):
            per_article_counter[article_id] += 1
            chunk_index = per_article_counter[article_id]
            chunks.append(
                {
                    "chunk_id": f"{article_id}-c{chunk_index:04d}-p{page['page']:03d}",
                    "article_id": article_id,
                    "title": page["title"],
                    "year": page.get("year", ""),
                    "page_start": page["page"],
                    "page_end": page["page"],
                    "chunk_index": chunk_index,
                    "text": text,
                    "char_count": len(text),
                    "pdf_path": page["pdf_path"],
                    "text_path": page["text_path"],
                }
            )

    write_jsonl(CHUNKS_JSONL, chunks)
    return chunks


def build_index(chunks: list[dict[str, Any]]) -> None:
    if not chunks:
        raise RuntimeError("No chunks to index. Build documents first.")

    corpus = [f"{chunk['title']} {chunk['text']}" for chunk in chunks]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.92,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(corpus)
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "vectorizer": vectorizer,
            "matrix": matrix,
            "chunks": chunks,
            "metadata": {
                "chunk_count": len(chunks),
                "feature_count": len(vectorizer.vocabulary_),
            },
        },
        INDEX_PATH,
    )


def build_report(documents: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    indexed_articles = {chunk["article_id"] for chunk in chunks}
    readable_documents = [doc for doc in documents if doc.get("extraction_status") in {"extracted", "partial"}]
    report = {
        "document_manifest": str(DOCUMENT_MANIFEST_JSONL.resolve()),
        "pages_jsonl": str(PAGES_JSONL.resolve()),
        "chunks_jsonl": str(CHUNKS_JSONL.resolve()),
        "index_path": str(INDEX_PATH.resolve()),
        "pdf_documents": len(documents),
        "readable_documents": len(readable_documents),
        "indexed_articles": len(indexed_articles),
        "page_count": sum(int(doc.get("page_count", 0)) for doc in documents),
        "extracted_pages": sum(int(doc.get("extracted_pages", 0)) for doc in documents),
        "char_count": sum(int(doc.get("char_count", 0)) for doc in documents),
        "chunk_count": len(chunks),
        "status_counts": dict(Counter(doc.get("extraction_status", "") for doc in documents)),
        "publisher_counts": dict(Counter(pub for doc in documents for pub in doc.get("publishers", []))),
        "year_counts": dict(Counter(doc.get("year", "") for doc in documents)),
    }
    write_json(REPORT_JSON, report)
    return report


def build_all(chunk_size: int, overlap: int) -> dict[str, Any]:
    documents, page_rows = build_documents()
    chunks = build_chunks(page_rows, chunk_size=chunk_size, overlap=overlap)
    build_index(chunks)
    return build_report(documents, chunks)


def load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Index not found: {INDEX_PATH}. Run `python -m project.literature_rag build` first.")
    return joblib.load(INDEX_PATH)


def search_chunks(query: str, top_k: int, min_score: float = 0.0) -> list[dict[str, Any]]:
    index = load_index()
    vectorizer = index["vectorizer"]
    matrix = index["matrix"]
    chunks = index["chunks"]

    query_vector = vectorizer.transform([query])
    scores = (matrix @ query_vector.T).toarray().ravel()
    if not np.any(scores):
        return []

    limit = min(top_k, len(chunks))
    candidate_indexes = np.argpartition(scores, -limit)[-limit:]
    ranked = sorted(candidate_indexes, key=lambda item: scores[item], reverse=True)

    results = []
    for rank, idx in enumerate(ranked, start=1):
        score = float(scores[idx])
        if score < min_score:
            continue
        chunk = dict(chunks[int(idx)])
        chunk["rank"] = rank
        chunk["score"] = score
        results.append(chunk)
    return results


def query_terms(query: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(query)}


def sentence_candidates(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 60]


def select_evidence_sentences(query: str, results: list[dict[str, Any]], max_sentences: int = 6) -> list[dict[str, Any]]:
    terms = query_terms(query)
    selected: list[dict[str, Any]] = []
    seen = set()

    for result in results:
        scored_sentences = []
        for sentence in sentence_candidates(result["text"]):
            sentence_terms = query_terms(sentence)
            overlap = len(terms & sentence_terms)
            score = overlap + math.log1p(len(sentence_terms)) * 0.05
            if overlap:
                scored_sentences.append((score, sentence))
        if not scored_sentences:
            fallback = result["text"][:450].strip()
            scored_sentences.append((0.0, fallback))

        for _, sentence in sorted(scored_sentences, key=lambda item: item[0], reverse=True)[:2]:
            normalized = re.sub(r"\s+", " ", sentence.lower())
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append(
                {
                    "sentence": sentence,
                    "title": result["title"],
                    "article_id": result["article_id"],
                    "page": result["page_start"],
                    "score": result["score"],
                    "pdf_path": result["pdf_path"],
                }
            )
            if len(selected) >= max_sentences:
                return selected
    return selected


def format_search(results: list[dict[str, Any]], snippet_chars: int) -> str:
    if not results:
        return "No matching chunks found."

    lines = []
    for result in results:
        snippet = textwrap.shorten(re.sub(r"\s+", " ", result["text"]), width=snippet_chars, placeholder=" ...")
        lines.append(
            f"{result['rank']}. score={result['score']:.4f} page={result['page_start']} "
            f"article={result['article_id']}\n"
            f"   title: {result['title']}\n"
            f"   pdf: {result['pdf_path']}\n"
            f"   text: {snippet}"
        )
    return "\n\n".join(lines)


def format_answer(query: str, results: list[dict[str, Any]], min_score: float) -> str:
    if not results or results[0]["score"] < min_score:
        return (
            "Insufficient local context to answer the question.\n"
            f"Best score: {results[0]['score']:.4f}" if results else "No matching chunks found."
        )

    evidence = select_evidence_sentences(query, results)
    if not evidence:
        return "No evidence sentences found in the retrieved chunks."

    lines = ["Answer draft from local evidence only:"]
    for idx, item in enumerate(evidence, start=1):
        sentence = textwrap.shorten(re.sub(r"\s+", " ", item["sentence"]), width=420, placeholder=" ...")
        lines.append(f"{idx}. {sentence} [{item['article_id']}, p. {item['page']}]")

    lines.append("")
    lines.append("Sources:")
    seen_sources = set()
    for result in results:
        key = (result["article_id"], result["page_start"])
        if key in seen_sources:
            continue
        seen_sources.add(key)
        lines.append(
            f"- {result['article_id']} p. {result['page_start']}: {result['title']} ({result['pdf_path']})"
        )
    return "\n".join(lines)


def command_build(args: argparse.Namespace) -> None:
    report = build_all(chunk_size=args.chunk_size, overlap=args.overlap)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def command_search(args: argparse.Namespace) -> None:
    results = search_chunks(args.query, top_k=args.top_k, min_score=args.min_score)
    print(format_search(results, snippet_chars=args.snippet_chars))


def command_answer(args: argparse.Namespace) -> None:
    results = search_chunks(args.query, top_k=args.top_k, min_score=0.0)
    print(format_answer(args.query, results, min_score=args.min_score))


def command_report(_: argparse.Namespace) -> None:
    if not REPORT_JSON.exists():
        raise FileNotFoundError(f"Report not found: {REPORT_JSON}. Run build first.")
    print(REPORT_JSON.read_text(encoding="utf-8"))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Build and query a local RAG index over downloaded Scholar Alert PDFs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Extract PDF text, chunk it, and build a TF-IDF index.")
    build_parser.add_argument("--chunk-size", type=int, default=1400)
    build_parser.add_argument("--overlap", type=int, default=250)
    build_parser.set_defaults(func=command_build)

    search_parser = subparsers.add_parser("search", help="Search indexed PDF chunks.")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--min-score", type=float, default=0.0)
    search_parser.add_argument("--snippet-chars", type=int, default=500)
    search_parser.set_defaults(func=command_search)

    answer_parser = subparsers.add_parser("answer", help="Produce an extractive answer from retrieved local chunks.")
    answer_parser.add_argument("query")
    answer_parser.add_argument("--top-k", type=int, default=6)
    answer_parser.add_argument("--min-score", type=float, default=0.05)
    answer_parser.set_defaults(func=command_answer)

    report_parser = subparsers.add_parser("report", help="Print the latest build report.")
    report_parser.set_defaults(func=command_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
