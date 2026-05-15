"""Tests for scalability baseline report generator."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.experiments.scalability_report import (
    generate_scalability_baseline,
    main,
    render_scalability_markdown,
)


def _sample_summary_df() -> pd.DataFrame:
    """Create compact synthetic summary dataframe."""
    return pd.DataFrame(
        [
            {
                "node_count": 10,
                "task_count": 100,
                "algorithm": "round-robin",
                "runtime_seconds_mean": 0.02,
                "avg_latency_mean": 2.0,
                "throughput_mean": 10.0,
                "avg_load_mean": 0.4,
                "pending_tasks_mean": 20.0,
                "deadline_violations_mean": 0.0,
            },
            {
                "node_count": 10,
                "task_count": 100,
                "algorithm": "min-load",
                "runtime_seconds_mean": 0.03,
                "avg_latency_mean": 3.0,
                "throughput_mean": 8.0,
                "avg_load_mean": 0.3,
                "pending_tasks_mean": 30.0,
                "deadline_violations_mean": 1.0,
            },
        ]
    )


def test_generate_scalability_baseline_builds_rows_and_winners() -> None:
    """Baseline generator should normalize rows and compute winners by point."""
    baseline = generate_scalability_baseline(
        _sample_summary_df(),
        schema_version="v-test",
        scenario="static",
        topology="ring",
        node_counts=[10],
        task_counts=[100],
        algorithms=["round-robin", "min-load"],
        source_summary_csv="outputs/sample.csv",
    )
    assert baseline["schema_version"] == "v-test"
    assert len(baseline["rows"]) == 2
    assert len(baseline["winners_by_point"]) == 1
    assert baseline["winners_by_point"][0]["algorithm"] == "round-robin"


def test_render_scalability_markdown_contains_sections() -> None:
    """Markdown renderer should include key sections and summary table."""
    baseline = generate_scalability_baseline(
        _sample_summary_df(),
        schema_version="v-test",
        scenario="static",
        topology="ring",
        node_counts=[10],
        task_counts=[100],
        algorithms=["round-robin", "min-load"],
        source_summary_csv="outputs/sample.csv",
    )
    text = render_scalability_markdown(baseline)
    assert "# Scalability Baseline Report" in text
    assert "## Summary Table" in text
    assert "| nodes | tasks | algorithm |" in text


def test_main_writes_json_and_markdown_files() -> None:
    """CLI main should persist both baseline JSON and markdown report."""
    out_dir = Path("outputs") / "test-suite" / f"scalability-report-{uuid4().hex[:8]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_csv = out_dir / "summary.csv"
    _sample_summary_df().to_csv(summary_csv, index=False)
    output_json = out_dir / "baseline.json"
    output_md = out_dir / "baseline.md"

    code = main(
        [
            "--summary-csv",
            str(summary_csv),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--nodes",
            "10",
            "--tasks",
            "100",
            "--algorithms",
            "round-robin,min-load",
        ]
    )
    assert code == 0
    assert output_json.exists()
    assert output_md.exists()
    with output_json.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["spec"]["node_counts"] == [10]
