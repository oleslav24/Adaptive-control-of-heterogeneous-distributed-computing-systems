from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "literature"
RAW_JSONL = DATA_DIR / "google_scholar_alert_urls.jsonl"


PUBLISHERS = {
    "ieeexplore.ieee.org": "IEEE Xplore",
    "www.sciencedirect.com": "ScienceDirect",
    "link.springer.com": "Springer",
    "arxiv.org": "arXiv",
    "www.mdpi.com": "MDPI",
    "www.nature.com": "Nature",
    "pmc.ncbi.nlm.nih.gov": "PubMed Central",
    "onlinelibrary.wiley.com": "Wiley",
    "dl.acm.org": "ACM Digital Library",
    "www.computer.org": "IEEE Computer Society",
    "iopscience.iop.org": "IOPscience",
    "www.frontiersin.org": "Frontiers",
    "digital-library.theiet.org": "IET Digital Library",
    "www.researchgate.net": "ResearchGate",
    "www.researchsquare.com": "Research Square",
    "openaccess.thecvf.com": "CVF Open Access",
    "search.proquest.com": "ProQuest",
    "cyberleninka.ru": "CyberLeninka",
    "www.google.com": "Google Books",
}


COMPUTING_CONTEXT = re.compile(
    r"\b(edge|fog|cloud|mec|mobile edge|serverless|distributed|heterogeneous|"
    r"federated|iot|internet of things|iiot|vehicular|v2x|uav|sdn|network|"
    r"computing|computation|computer|wireless|service chain|iomt|iov|"
    r"multicloud|clouds|smartnic|распределенных вычислений|распределённ[а-яё ]+вычисл)\b",
    re.IGNORECASE,
)
STRONG_COMPUTING_CONTEXT = re.compile(
    r"\b(mobile edge computing|multi-access edge computing|edge computing|fog computing|"
    r"cloud computing|cloud environment|cloud-fog|fog-cloud|edge-fog|edge-cloud|"
    r"edge-cloud continuum|serverless edge|mec|vec-enabled|mec-enabled|edge ai|"
    r"edge artificial intelligence|distributed computing|heterogeneous distributed|"
    r"edge network|edge networks|edge server|edge servers|edge service|edge services|"
    r"edge device|edge devices|iot network|iiot|iomt|iov|vehicular edge|"
    r"multicloud|hybrid clouds|large-scale ai training|распределенных вычислений|"
    r"распределённ[а-яё ]+вычисл)\b",
    re.IGNORECASE,
)
TASK_CONTEXT = re.compile(
    r"\b(offload|offloading|task|scheduling|resource allocation|resource management|"
    r"load balanc|caching|orchestration|placement|trajectory|latency|throughput|"
    r"quality of service|qos|energy efficient|optimization|optimizing)\b",
    re.IGNORECASE,
)
ADAPTIVE_CONTEXT = re.compile(
    r"\b(adaptive|reinforcement learning|deep reinforcement|q-learning|multi-agent|"
    r"game theory|fuzzy|evolutionary|genetic|swarm|learning|control)\b",
    re.IGNORECASE,
)
OFF_TOPIC = re.compile(
    r"\b(carbon footprint|solar tree|photovoltaic|biofuel|hydrogen|battery energy storage|"
    r"renewable energy storage|lightning protection|coal|surface mining|coal deposit|"
    r"mining operations|methane|construction materials)\b|"
    r"(углерод|биотоплив|водород|строительств|конструкционных материал|уголь)",
    re.IGNORECASE,
)
VISION_NOISE = re.compile(
    r"\b(yolo|object detection|remote sensing|aerial image|aerial images|infrared|"
    r"camera-based|fisheye|wildlife object|urban traffic|autonomous driving)\b",
    re.IGNORECASE,
)
NETWORK_CONTEXT = re.compile(
    r"\b(network|networks|wireless|uav|vehicular|vanet|v2x|iot|internet of things|"
    r"iiot|iomt|iov|sensor network|crowdsensing|sdn|mimo|noma|ris)\b",
    re.IGNORECASE,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def normalize_title(title: str) -> str:
    text = title.casefold()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9а-яё]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stable_id(title_norm: str, fallback_url: str) -> str:
    source = title_norm or canonicalize_url(fallback_url)
    return "gsa-" + hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def canonicalize_url(url: str) -> str:
    parsed = urlparse(unquote(url))
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = quote(unquote(parsed.path), safe="/:._-~")
    query = parsed.query

    if netloc == "www.google.com" and path == "/books":
        keep = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=False):
            if key in {"id", "pg", "hl", "lr", "oi"}:
                keep.append((key, value))
        query = urlencode(keep)

    if netloc in {"arxiv.org"}:
        path = path.rstrip("/")

    return urlunparse((scheme, netloc, path, "", query, parsed.fragment))


def host_for(url: str) -> str:
    return urlparse(url).netloc.lower()


def infer_publisher(url: str) -> str:
    return PUBLISHERS.get(host_for(url), host_for(url))


def is_pdf_url(url: str, url_type: str) -> bool:
    path = urlparse(url).path.lower()
    return url_type in {"pdf", "arxiv_pdf"} or path.endswith(".pdf")


def extract_doi(url: str) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path)

    for pattern in (
        r"/(?:article|chapter)/(10\.\d{4,9}/[^/?#]+)",
        r"/doi/(?:abs|full|pdf|epdf)?/?(10\.\d{4,9}/[^/?#]+)",
        r"/articles/(10\.\d{4,9}/[^/?#]+)",
        r"/article/(10\.\d{4,9}/[^/?#]+)/",
    ):
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            return match.group(1).rstrip(".")

    nature = re.search(r"/articles/(s\d{5}-\d{3}-\d{5}-\d)", path, re.IGNORECASE)
    if nature:
        return f"10.1038/{nature.group(1)}"

    return ""


def extract_arxiv_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "arxiv.org":
        return ""
    match = re.search(r"/(?:abs|pdf)/([^/?#]+)", parsed.path)
    if not match:
        return ""
    return re.sub(r"\.pdf$", "", match.group(1), flags=re.IGNORECASE)


def extract_identifiers(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    ids: dict[str, str] = {}

    doi = extract_doi(url)
    if doi:
        ids["doi"] = doi

    arxiv_id = extract_arxiv_id(url)
    if arxiv_id:
        ids["arxiv_id"] = arxiv_id

    ieee = re.search(r"/document/(\d+)|/(\d+)\.pdf$", path)
    if parsed.netloc.lower() == "ieeexplore.ieee.org" and ieee:
        ids["ieee_document_id"] = next(group for group in ieee.groups() if group)

    pii = re.search(r"/pii/([A-Za-z0-9]+)", path)
    if parsed.netloc.lower() == "www.sciencedirect.com" and pii:
        ids["sciencedirect_pii"] = pii.group(1)

    if parsed.netloc.lower() == "www.mdpi.com":
        parts = [part for part in path.split("/") if part]
        if parts:
            ids["mdpi_path"] = "/".join(parts)

    if parsed.netloc.lower() == "www.google.com" and path == "/books":
        for key, value in parse_qsl(parsed.query):
            if key == "id":
                ids["google_books_id"] = value
            elif key == "pg":
                ids["google_books_page"] = value

    return ids


def parse_year(values: list[str]) -> str:
    years = []
    for value in values:
        years.extend(int(year) for year in re.findall(r"\b(20[0-3]\d|19[8-9]\d)\b", value))
    if not years:
        return ""
    return str(max(years))


@dataclass
class Relevance:
    is_relevant: bool
    score: int
    labels: list[str]
    reason: str


def classify_relevance(title: str, authors_venue: str) -> Relevance:
    text = f"{title} {authors_venue}"
    labels: list[str] = []
    score = 0

    if COMPUTING_CONTEXT.search(text):
        labels.append("computing_context")
        score += 3
    if TASK_CONTEXT.search(text):
        labels.append("task_resource_context")
        score += 2
    if ADAPTIVE_CONTEXT.search(text):
        labels.append("adaptive_learning_context")
        score += 1
    if OFF_TOPIC.search(text):
        labels.append("off_topic_energy_carbon")
        score -= 3
    if STRONG_COMPUTING_CONTEXT.search(text):
        labels.append("strong_computing_context")
        score += 2
    if NETWORK_CONTEXT.search(text):
        labels.append("network_context")
        score += 1
    if VISION_NOISE.search(text):
        labels.append("vision_detection_noise")
        score -= 2

    has_core = "computing_context" in labels
    has_task = "task_resource_context" in labels
    has_strong = "strong_computing_context" in labels
    has_network = "network_context" in labels
    has_adaptive = "adaptive_learning_context" in labels
    has_vision_noise = "vision_detection_noise" in labels and not (has_strong and has_task)
    has_strong_offtopic = "off_topic_energy_carbon" in labels and not (has_strong or (has_core and has_task))

    if has_strong_offtopic:
        return Relevance(False, score, labels, "energy/carbon/hydrogen topic without distributed-computing context")
    if has_vision_noise:
        return Relevance(False, score, labels, "computer-vision/object-detection topic without distributed-computing context")
    if has_strong and (has_task or has_adaptive or re.search(r"\bfederated learning\b", text, re.IGNORECASE)):
        return Relevance(True, score, labels, "")
    if has_task and has_network:
        return Relevance(True, score, labels, "")
    if has_core and (has_task or has_adaptive):
        return Relevance(True, score, labels, "")
    if has_strong and score >= 4:
        return Relevance(True, score, labels, "")
    return Relevance(False, score, labels, "missing clear distributed/edge/cloud computing context")


def dedupe_articles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        title_norm = normalize_title(row["title"])
        key = title_norm or canonicalize_url(row["direct_url"])
        groups[key].append(row)

    articles = []
    for group_rows in groups.values():
        group_rows = sorted(group_rows, key=lambda item: (item["email_ts"], item["source_email_id"]))
        title_counts = Counter(row["title"] for row in group_rows)
        title = title_counts.most_common(1)[0][0]
        title_norm = normalize_title(title)
        urls = []
        seen_urls = set()
        identifiers: dict[str, list[str]] = defaultdict(list)

        for row in group_rows:
            url = canonicalize_url(row["direct_url"])
            if url in seen_urls:
                continue
            seen_urls.add(url)
            url_ids = extract_identifiers(url)
            for key, value in url_ids.items():
                if value not in identifiers[key]:
                    identifiers[key].append(value)
            urls.append(
                {
                    "url": url,
                    "url_type": row["url_type"],
                    "access_hint": row.get("access_hint", ""),
                    "host": host_for(url),
                    "publisher": infer_publisher(url),
                    "is_pdf": is_pdf_url(url, row["url_type"]),
                    "identifiers": url_ids,
                }
            )

        pdf_urls = [item["url"] for item in urls if item["is_pdf"]]
        publisher_urls = [item["url"] for item in urls if not item["is_pdf"]]
        primary_url = publisher_urls[0] if publisher_urls else pdf_urls[0] if pdf_urls else urls[0]["url"]
        author_samples = sorted({row["authors_venue"] for row in group_rows if row.get("authors_venue")})
        source_ids = sorted({row["source_email_id"] for row in group_rows})
        email_times = sorted({row["email_ts"] for row in group_rows})
        relevance = classify_relevance(title, " ".join(author_samples))

        articles.append(
            {
                "article_id": stable_id(title_norm, primary_url),
                "title": title,
                "title_norm": title_norm,
                "year": parse_year([title, *author_samples, *email_times]),
                "first_seen_email_ts": email_times[0],
                "last_seen_email_ts": email_times[-1],
                "source_email_ids": source_ids,
                "source_email_count": len(source_ids),
                "raw_record_count": len(group_rows),
                "authors_venue_samples": author_samples[:5],
                "primary_url": primary_url,
                "pdf_urls": pdf_urls,
                "publisher_urls": publisher_urls,
                "urls": urls,
                "hosts": sorted({item["host"] for item in urls}),
                "publishers": sorted({item["publisher"] for item in urls}),
                "doi": first_identifier(identifiers, "doi"),
                "arxiv_id": first_identifier(identifiers, "arxiv_id"),
                "identifiers": {key: values for key, values in sorted(identifiers.items())},
                "is_relevant": relevance.is_relevant,
                "relevance_score": relevance.score,
                "relevance_labels": relevance.labels,
                "exclusion_reason": relevance.reason,
            }
        )

    return sorted(articles, key=lambda item: (item["last_seen_email_ts"], item["title"]), reverse=True)


def first_identifier(identifiers: dict[str, list[str]], key: str) -> str:
    values = identifiers.get(key, [])
    return values[0] if values else ""


def pdf_candidates(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for article in articles:
        if not article["is_relevant"]:
            continue
        for url in article["pdf_urls"]:
            seen.add((article["article_id"], url))
            rows.append(
                {
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "year": article["year"],
                    "pdf_url": url,
                    "candidate_source": "direct",
                    "host": host_for(url),
                    "arxiv_id": article["arxiv_id"],
                    "doi": article["doi"],
                    "publishers": article["publishers"],
                }
            )
        for url, source in derived_pdf_candidates(article):
            key = (article["article_id"], url)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "year": article["year"],
                    "pdf_url": url,
                    "candidate_source": source,
                    "host": host_for(url),
                    "arxiv_id": article["arxiv_id"],
                    "doi": article["doi"],
                    "publishers": article["publishers"],
                }
            )
    return rows


def derived_pdf_candidates(article: dict[str, Any]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for url in article["publisher_urls"]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/")

        if host == "arxiv.org" and path.startswith("/abs/"):
            candidates.append((urlunparse((parsed.scheme, host, path.replace("/abs/", "/pdf/", 1), "", "", "")), "derived_arxiv_abs"))
        elif host == "www.mdpi.com" and not path.endswith("/pdf"):
            candidates.append((urlunparse((parsed.scheme, host, path + "/pdf", "", "", "")), "derived_mdpi"))
        elif host == "www.nature.com" and path.startswith("/articles/"):
            candidates.append((urlunparse((parsed.scheme, host, path + ".pdf", "", "", "")), "derived_nature"))
        elif host == "www.frontiersin.org" and "/articles/" in path:
            pdf_path = path[:-5] + "pdf" if path.endswith("/full") else path + "/pdf"
            candidates.append((urlunparse((parsed.scheme, host, pdf_path, "", "", "")), "derived_frontiers"))
        elif host == "peerj.com" and re.search(r"/articles/\d+$", path):
            candidates.append((urlunparse((parsed.scheme, host, path + ".pdf", "", "", "")), "derived_peerj"))

    doi = article.get("doi", "")
    if doi:
        quoted_doi = quote(doi, safe="/")
        publishers = set(article.get("publishers", []))
        if "Springer" in publishers:
            candidates.append((f"https://link.springer.com/content/pdf/{quoted_doi}.pdf", "derived_springer_doi"))
        if "Wiley" in publishers:
            candidates.append((f"https://onlinelibrary.wiley.com/doi/pdf/{quoted_doi}", "derived_wiley_doi"))
        if "ACM Digital Library" in publishers:
            candidates.append((f"https://dl.acm.org/doi/pdf/{quoted_doi}", "derived_acm_doi"))

    return candidates


def make_summary(raw_rows: list[dict[str, Any]], articles: list[dict[str, Any]], pdf_rows: list[dict[str, Any]]) -> dict[str, Any]:
    relevant = [article for article in articles if article["is_relevant"]]
    excluded = [article for article in articles if not article["is_relevant"]]
    return {
        "raw_records": len(raw_rows),
        "deduped_articles": len(articles),
        "relevant_articles": len(relevant),
        "excluded_articles": len(excluded),
        "unique_urls": len({canonicalize_url(row["direct_url"]) for row in raw_rows}),
        "unique_source_emails": len({row["source_email_id"] for row in raw_rows}),
        "pdf_candidate_urls": len(pdf_rows),
        "articles_with_pdf_candidates": len({row["article_id"] for row in pdf_rows}),
        "raw_url_types": dict(Counter(row["url_type"] for row in raw_rows)),
        "deduped_publishers": dict(Counter(publisher for article in articles for publisher in article["publishers"])),
        "excluded_reasons": dict(Counter(article["exclusion_reason"] for article in excluded)),
    }


def main() -> None:
    raw_rows = read_jsonl(RAW_JSONL)
    articles = dedupe_articles(raw_rows)
    clean_articles = [article for article in articles if article["is_relevant"]]
    excluded = [article for article in articles if not article["is_relevant"]]
    pdf_rows = pdf_candidates(articles)
    summary = make_summary(raw_rows, articles, pdf_rows)

    write_jsonl(DATA_DIR / "google_scholar_articles_deduped.jsonl", articles)
    write_jsonl(DATA_DIR / "google_scholar_articles_clean.jsonl", clean_articles)
    write_jsonl(DATA_DIR / "google_scholar_articles_excluded.jsonl", excluded)
    write_jsonl(DATA_DIR / "google_scholar_pdf_candidates.jsonl", pdf_rows)

    article_fields = [
        "article_id",
        "title",
        "year",
        "is_relevant",
        "relevance_score",
        "relevance_labels",
        "exclusion_reason",
        "primary_url",
        "pdf_urls",
        "publisher_urls",
        "doi",
        "arxiv_id",
        "identifiers",
        "publishers",
        "source_email_count",
        "raw_record_count",
        "first_seen_email_ts",
        "last_seen_email_ts",
    ]
    write_csv(DATA_DIR / "google_scholar_articles_deduped.csv", articles, article_fields)
    write_csv(DATA_DIR / "google_scholar_articles_clean.csv", clean_articles, article_fields)
    write_csv(
        DATA_DIR / "google_scholar_pdf_candidates.csv",
        pdf_rows,
        ["article_id", "title", "year", "pdf_url", "candidate_source", "host", "arxiv_id", "doi", "publishers"],
    )

    (DATA_DIR / "google_scholar_dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
