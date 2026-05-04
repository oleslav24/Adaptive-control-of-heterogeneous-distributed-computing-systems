from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "literature"
CANDIDATES_JSONL = DATA_DIR / "google_scholar_pdf_candidates.jsonl"
DOWNLOAD_DIR = DATA_DIR / "pdfs"
MANIFEST_JSONL = DATA_DIR / "google_scholar_pdf_downloads.jsonl"
SUMMARY_JSON = DATA_DIR / "google_scholar_pdf_download_summary.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def is_pdf_bytes(payload: bytes) -> bool:
    return payload[:1024].lstrip().startswith(b"%PDF")


def safe_filename(article_id: str, url: str) -> str:
    host = re.sub(r"[^a-z0-9]+", "-", urlparse(url).netloc.lower()).strip("-")
    return f"{article_id}_{host}.pdf"


def download(url: str, timeout: int) -> tuple[str, int | None, str, bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; literature-rag-pdf-fetch/0.1)",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            content_type = response.headers.get("Content-Type", "")
            payload = response.read()
            if not is_pdf_bytes(payload):
                return "not_pdf", status, content_type, payload[:4096], "response did not start with PDF header"
            return "downloaded", status, content_type, payload, ""
    except HTTPError as exc:
        return "http_error", exc.code, exc.headers.get("Content-Type", ""), b"", str(exc)
    except URLError as exc:
        return "url_error", None, "", b"", str(exc.reason)
    except TimeoutError as exc:
        return "timeout", None, "", b"", str(exc)
    except Exception as exc:  # noqa: BLE001 - preserve batch progress.
        return "error", None, "", b"", f"{type(exc).__name__}: {exc}"


def group_candidates(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    priority = {
        "direct": 0,
        "derived_arxiv_abs": 1,
        "derived_mdpi": 2,
        "derived_nature": 3,
        "derived_frontiers": 4,
        "derived_springer_doi": 5,
        "derived_wiley_doi": 6,
        "derived_acm_doi": 7,
    }
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        groups[candidate["article_id"]].append(candidate)
    for article_id in groups:
        groups[article_id].sort(key=lambda row: (priority.get(row.get("candidate_source", ""), 99), row["pdf_url"]))
    return groups


def run(limit: int | None, timeout: int, force: bool) -> list[dict[str, Any]]:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    candidates = read_jsonl(CANDIDATES_JSONL)
    grouped = group_candidates(candidates)
    records: list[dict[str, Any]] = []
    successful_articles: set[str] = set()

    for article_index, (article_id, article_candidates) in enumerate(grouped.items(), start=1):
        if limit is not None and article_index > limit:
            break

        existing = sorted(DOWNLOAD_DIR.glob(f"{article_id}_*.pdf"))
        if existing and not force:
            successful_articles.add(article_id)
            for candidate in article_candidates:
                records.append(make_record(candidate, "already_downloaded", str(existing[0]), existing[0].stat().st_size))
            continue

        for candidate in article_candidates:
            if article_id in successful_articles:
                records.append(make_record(candidate, "skipped_after_success", "", 0))
                continue

            status, http_status, content_type, payload, error = download(candidate["pdf_url"], timeout)
            target = DOWNLOAD_DIR / safe_filename(article_id, candidate["pdf_url"])
            downloaded_path = ""
            size = 0
            if status == "downloaded":
                target.write_bytes(payload)
                downloaded_path = str(target)
                size = len(payload)
                successful_articles.add(article_id)

            record = make_record(candidate, status, downloaded_path, size)
            record.update(
                {
                    "http_status": http_status,
                    "content_type": content_type,
                    "error": error,
                }
            )
            records.append(record)
            time.sleep(0.2)

    write_jsonl(MANIFEST_JSONL, records)
    SUMMARY_JSON.write_text(
        json.dumps(make_summary(records), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return records


def make_record(candidate: dict[str, Any], status: str, downloaded_path: str, size: int) -> dict[str, Any]:
    return {
        "article_id": candidate["article_id"],
        "title": candidate["title"],
        "year": candidate.get("year", ""),
        "pdf_url": candidate["pdf_url"],
        "candidate_source": candidate.get("candidate_source", ""),
        "host": candidate.get("host", urlparse(candidate["pdf_url"]).netloc.lower()),
        "status": status,
        "downloaded_path": downloaded_path,
        "bytes": size,
    }


def make_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    downloaded = [record for record in records if record["status"] in {"downloaded", "already_downloaded"}]
    return {
        "records": len(records),
        "downloaded_records": len(downloaded),
        "downloaded_articles": len({record["article_id"] for record in downloaded}),
        "downloaded_bytes": sum(record.get("bytes", 0) for record in downloaded),
        "status_counts": dict(Counter(record["status"] for record in records)),
        "downloaded_by_host": dict(Counter(record["host"] for record in downloaded)),
        "failed_by_host": dict(
            Counter(record["host"] for record in records if record["status"] not in {"downloaded", "already_downloaded", "skipped_after_success"})
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PDF candidates for the Google Scholar Alerts corpus.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of article groups to process.")
    parser.add_argument("--timeout", type=int, default=45, help="Per-request timeout in seconds.")
    parser.add_argument("--force", action="store_true", help="Re-download PDFs even when a local file exists.")
    args = parser.parse_args()

    records = run(limit=args.limit, timeout=args.timeout, force=args.force)
    print(json.dumps(make_summary(records), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
