"""Unit tests for evidence-backed claim generation."""

from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.evidence_claims import (
    build_report_claims,
    build_runtime_claims,
    render_markdown_claims,
    validate_claims,
    write_claims_report,
)


def _evidence_payload() -> dict[str, object]:
    """Build normalized evidence payload with two sources."""
    return {
        "available": True,
        "query": "adaptive scheduling",
        "items": [
            {
                "rank": 1,
                "score": 0.21,
                "article_id": "doc-1",
                "title": "Adaptive Scheduling",
                "page": 3,
                "pdf_path": "C:/repo/doc-1.pdf",
                "snippet": "Evidence one.",
            },
            {
                "rank": 2,
                "score": 0.18,
                "article_id": "doc-2",
                "title": "Multi-Agent Control",
                "page": 7,
                "pdf_path": "C:/repo/doc-2.pdf",
                "snippet": "Evidence two.",
            },
        ],
    }


def test_build_runtime_claims_uses_metrics_and_evidence() -> None:
    """Runtime claims should summarize live metric trends with evidence links."""
    result = build_runtime_claims(
        {
            "time": [0, 1, 2],
            "latency": [2.0, 1.7, 1.4],
            "throughput": [1.0, 1.1, 1.2],
            "queue": [5, 4, 3],
            "avg_load": [0.5, 0.55, 0.6],
        },
        _evidence_payload(),
        scenario="dynamic-load",
        algorithm="min-load",
    )

    claims = result["claims"]
    gate = result["gate"]
    assert len(claims) >= 2
    assert claims[0]["hypothesis"] == "H1"
    assert claims[0]["status"] == "supported"
    assert claims[0]["evidence"][0]["article_id"] == "doc-1"
    assert gate["ok"] is True


def test_build_runtime_claims_marks_insufficient_evidence() -> None:
    """Claims should remain explicit when local RAG has no usable evidence."""
    result = build_runtime_claims(
        {"time": [0, 1], "latency": [1.0, 0.8], "throughput": [1.0, 1.1], "queue": [2, 1]},
        {"available": False, "items": []},
    )
    assert result["claims"][0]["status"] == "insufficient-evidence"
    assert result["gate"]["ok"] is False
    assert any("expected at least 2 evidence sources" in error for error in result["gate"]["errors"])


def test_build_report_claims_covers_h1_to_h5() -> None:
    """Report claims should emit one machine-readable claim for each hypothesis."""
    hypotheses = pd.DataFrame(
        [
            {
                "hypothesis": "H1",
                "title": "Adaptivity",
                "criterion": "Adaptive control improves latency.",
                "delta_latency": 0.4,
                "delta_load_imbalance": 0.2,
                "confirmed": True,
            },
            {
                "hypothesis": "H2",
                "title": "MAS",
                "criterion": "MAS improves robustness.",
                "delta_throughput_failures": 0.3,
                "delta_stability_failures": 0.1,
                "confirmed": True,
            },
            {
                "hypothesis": "H3",
                "title": "ML/ZNN",
                "criterion": "ML improves dynamic load.",
                "delta_latency_dynamic": 0.2,
                "confirmed": True,
            },
            {
                "hypothesis": "H4",
                "title": "Hybrid",
                "criterion": "Hybrid beats baseline.",
                "delta_latency_hybrid_vs_best_baseline": 0.1,
                "confirmed": True,
            },
            {
                "hypothesis": "H5",
                "title": "LLM",
                "criterion": "LLM improves coordination.",
                "delta_adaptivity_llm_vs_algorithmic": 0.1,
                "delta_latency_llm_vs_algorithmic": 0.1,
                "confirmed": False,
            },
        ]
    )
    summary = pd.DataFrame([{"study_id": "E1_scalability"}])

    result = build_report_claims(
        summary_df=summary,
        hypotheses_df=hypotheses,
        evidence_payload=_evidence_payload(),
    )

    assert len(result["claims"]) == 5
    assert result["gate"]["ok"] is True
    assert result["gate"]["covered_hypotheses"] == ["H1", "H2", "H3", "H4", "H5"]
    assert {claim["claim_id"] for claim in result["claims"]} == {
        "report-H1",
        "report-H2",
        "report-H3",
        "report-H4",
        "report-H5",
    }


def test_validate_claims_reports_missing_coverage_and_bad_evidence() -> None:
    """Claims gate should fail on missing hypotheses and weak citations."""
    result = validate_claims(
        [
            {
                "claim_id": "c1",
                "hypothesis": "H1",
                "statement": "s",
                "status": "supported",
                "confidence": 0.5,
                "evidence": [{"article_id": "doc", "title": "Doc", "score": 0.01}],
            }
        ],
        min_sources_per_claim=2,
        min_score=0.03,
        required_hypotheses=("H1", "H2"),
    )
    assert result["ok"] is False
    assert any("expected at least 2 evidence sources" in error for error in result["errors"])
    assert any("below 0.0300" in error for error in result["errors"])
    assert any("Missing hypothesis coverage: H2" in error for error in result["errors"])


def test_render_and_write_claims_report() -> None:
    """Claims should render to markdown and persist as JSON report."""
    claim = {
        "claim_id": "report-H1",
        "hypothesis": "H1",
        "statement": "Latency improved.",
        "status": "supported",
        "confidence": 0.75,
        "evidence": [{"article_id": "doc-1", "page": 2, "title": "Doc", "score": 0.2}],
    }
    lines = render_markdown_claims([claim])
    assert "`H1` `supported`" in lines[0]
    assert "[doc-1, p. 2]" in lines[0]

    out = Path("outputs") / "test-suite" / f"claims-{uuid4().hex[:8]}" / "claims_report.json"
    written = write_claims_report(out, claims=[claim], gate={"ok": True}, context={"mode": "test"})
    assert Path(written).exists()
    assert "Latency improved" in Path(written).read_text(encoding="utf-8")
