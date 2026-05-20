"""Unit tests for local literature evidence helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import project.literature_evidence as evidence


def test_build_query_from_metrics_includes_dynamic_hints() -> None:
    """Query builder should inject trend-specific retrieval hints."""
    query = evidence.build_query_from_metrics(
        {
            "latency": [1.0, 1.4],
            "queue": [2.0, 3.0],
            "throughput": [1.0, 0.8],
            "avg_load": [0.7, 0.9],
        },
        scenario="peak-load",
        algorithm="carbon-aware",
    )
    assert "latency reduction" in query
    assert "load balancing" in query
    assert "resource contention" in query
    assert "scenario peak-load" in query
    assert "algorithm carbon-aware" in query


def test_search_literature_handles_missing_index(monkeypatch) -> None:
    """Search wrapper should return unavailable payload when index is missing."""

    def _raise_missing(_query: str, top_k: int, min_score: float = 0.0):
        _ = (top_k, min_score)
        raise FileNotFoundError("index missing")

    monkeypatch.setattr(evidence, "search_chunks", _raise_missing)
    payload = evidence.search_literature("test query", top_k=3, min_score=0.1)
    assert payload["available"] is False
    assert payload["reason"] == "index-not-built"
    assert payload["items"] == []


def test_search_literature_normalizes_rows(monkeypatch) -> None:
    """Search wrapper should normalize chunk rows into compact UI-friendly payload."""
    folder = Path("outputs") / "test-suite" / f"lit-evidence-{uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    pdf = folder / "doc.pdf"
    pdf.write_text("x", encoding="utf-8")

    def _fake_search(_query: str, top_k: int, min_score: float = 0.0):
        _ = (top_k, min_score)
        return [
            {
                "rank": 1,
                "score": 0.77,
                "article_id": "A-1",
                "title": "Adaptive Scheduling",
                "page_start": 4,
                "pdf_path": str(pdf.resolve()),
                "text": "A long snippet " * 60,
            }
        ]

    monkeypatch.setattr(evidence, "search_chunks", _fake_search)
    payload = evidence.search_literature("adaptive scheduling", top_k=5, min_score=0.01)
    assert payload["available"] is True
    assert payload["reason"] == ""
    assert payload["query"] == "adaptive scheduling"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["article_id"] == "A-1"
    assert item["page"] == 4
    assert item["score"] == 0.77
    assert item["pdf_path"] == str(pdf.resolve())
    assert len(item["snippet"]) > 10


def test_validate_evidence_items_reports_schema_and_coverage_errors() -> None:
    """Validation should fail on insufficient source count and malformed entries."""
    bad_items = [
        {
            "article_id": "",
            "title": "",
            "page": 0,
            "score": -0.5,
            "pdf_path": "relative/path.txt",
            "snippet": "",
        }
    ]
    result = evidence.validate_evidence_items(bad_items, min_sources=2)
    assert result["ok"] is False
    assert result["source_count"] == 1
    assert any("Expected at least 2 sources" in err for err in result["errors"])
    assert any("pdf_path must be absolute" in err for err in result["errors"])
    assert any("must point to a .pdf" in err for err in result["errors"])
    assert any("page must be >= 1" in err for err in result["errors"])


def test_render_markdown_evidence_outputs_citations() -> None:
    """Markdown renderer should produce citation bullets with score and snippet."""
    lines = evidence.render_markdown_evidence(
        [
            {
                "article_id": "doc-1",
                "title": "Doc 1",
                "page": 3,
                "score": 0.45,
                "snippet": "Important finding.",
            }
        ],
        limit=3,
    )
    assert len(lines) == 1
    assert "[doc-1, p. 3]" in lines[0]
    assert "score=0.4500" in lines[0]
    assert "Important finding." in lines[0]
