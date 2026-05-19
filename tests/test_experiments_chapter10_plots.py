"""Tests for Chapter 10 plot artifact generation."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.experiments.chapter10_plots import persist_chapter10_plots


def _workspace_dir(suffix: str) -> Path:
    """Create isolated writable directory for test artifacts."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_persist_chapter10_plots_writes_carbon_frontier_plot() -> None:
    """Plot exporter should include carbon/performance frontier when carbon metrics exist."""
    output_dir = _workspace_dir("chapter10-plots")
    summary = pd.DataFrame(
        [
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "min-load",
                "avg_latency_mean": 1.3,
                "throughput_mean": 2.1,
                "co2_per_completed_task_lb_mean": 1.6,
                "node_count": 50,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "carbon-aware",
                "avg_latency_mean": 1.4,
                "throughput_mean": 2.0,
                "co2_per_completed_task_lb_mean": 1.1,
                "node_count": 50,
            },
        ]
    )
    raw_runs = pd.DataFrame(
        [
            {"scenario": "dynamic-load", "throughput": 2.2, "method": "min-load", "avg_latency": 1.3},
            {"scenario": "dynamic-load", "throughput": 2.0, "method": "carbon-aware", "avg_latency": 1.4},
        ]
    )

    artifacts = persist_chapter10_plots(
        summary_df=summary,
        raw_runs_df=raw_runs,
        output_dir=output_dir,
        formats=("png",),
    )
    assert "plot_carbon_performance_frontier_png" in artifacts
    assert Path(artifacts["plot_carbon_performance_frontier_png"]).exists()


def test_persist_chapter10_plots_skips_carbon_frontier_without_metrics() -> None:
    """Carbon frontier artifact should be absent if summary has no carbon columns."""
    output_dir = _workspace_dir("chapter10-plots-empty-carbon")
    summary = pd.DataFrame([{"study_id": "E1_scalability", "method": "min-load", "avg_latency_mean": 1.2, "node_count": 10}])
    raw_runs = pd.DataFrame([{"scenario": "static", "throughput": 2.0, "method": "min-load", "avg_latency": 1.2}])

    artifacts = persist_chapter10_plots(
        summary_df=summary,
        raw_runs_df=raw_runs,
        output_dir=output_dir,
        formats=("png",),
    )
    assert "plot_carbon_performance_frontier_png" not in artifacts

