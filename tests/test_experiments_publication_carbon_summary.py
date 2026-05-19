"""Tests for publication carbon-summary helper contracts."""

from __future__ import annotations

import pandas as pd

import pytest

from project.experiments import publication as pub


def test_build_carbon_summary_prefers_e6_and_computes_deltas() -> None:
    """Carbon summary should focus E6 and compute deltas relative to min-load."""
    summary = pd.DataFrame(
        [
            {
                "study_id": "E1_scalability",
                "method": "greedy",
                "method_label": "Greedy",
                "avg_latency_mean": 1.1,
                "throughput_mean": 2.4,
                "co2_total_lb_mean": 500.0,
                "co2_per_completed_task_lb_mean": 5.0,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "min-load",
                "method_label": "Min-Load",
                "avg_latency_mean": 1.2,
                "throughput_mean": 2.3,
                "co2_total_lb_mean": 200.0,
                "co2_per_completed_task_lb_mean": 2.0,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "carbon-aware",
                "method_label": "Carbon-Aware",
                "avg_latency_mean": 1.3,
                "throughput_mean": 2.1,
                "co2_total_lb_mean": 140.0,
                "co2_per_completed_task_lb_mean": 1.4,
            },
        ]
    )

    table = pub._build_carbon_summary(summary)  # noqa: SLF001
    assert table["method"].tolist() == ["carbon-aware", "min-load"]
    carbon_row = table[table["method"] == "carbon-aware"].iloc[0]
    assert float(carbon_row["delta_co2_total_vs_min_load_lb"]) == pytest.approx(-60.0)
    assert float(carbon_row["delta_co2_per_task_vs_min_load_lb"]) == pytest.approx(-0.6)
    assert float(carbon_row["co2_total_reduction_vs_min_load_pct"]) == pytest.approx(30.0)


def test_build_carbon_summary_returns_empty_without_required_metrics() -> None:
    """Carbon summary should be empty when required columns are missing."""
    summary = pd.DataFrame([{"method": "min-load", "avg_latency_mean": 1.0}])
    table = pub._build_carbon_summary(summary)  # noqa: SLF001
    assert table.empty
