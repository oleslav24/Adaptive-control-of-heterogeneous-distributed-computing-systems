"""Unit tests for Chapter 10 table builders."""

from __future__ import annotations

import pandas as pd

from project.experiments.chapter10_tables import (
    build_carbon_tradeoff_table,
    build_chapter10_tables,
)


def test_build_chapter10_tables_contains_carbon_tradeoff() -> None:
    """Table bundle should include carbon_tradeoff key when summary has carbon columns."""
    summary = pd.DataFrame(
        [
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "min-load",
                "method_label": "Min-Load",
                "avg_latency_mean": 1.4,
                "throughput_mean": 2.0,
                "co2_total_lb_mean": 180.0,
                "co2_per_completed_task_lb_mean": 1.8,
                "load_imbalance_mean": 0.3,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "carbon-aware",
                "method_label": "Carbon-Aware",
                "avg_latency_mean": 1.5,
                "throughput_mean": 1.9,
                "co2_total_lb_mean": 120.0,
                "co2_per_completed_task_lb_mean": 1.2,
                "load_imbalance_mean": 0.35,
            },
        ]
    )
    raw_runs = pd.DataFrame(
        [
            {
                "scenario": "dynamic-load",
                "avg_latency": 1.4,
                "throughput": 2.0,
                "sla_violations": 1,
                "load_imbalance": 0.3,
            }
        ]
    )
    hypotheses = pd.DataFrame([{"hypothesis": "H1", "title": "Adaptivity", "criterion": "c", "confirmed": True}])

    tables = build_chapter10_tables(
        summary_df=summary,
        raw_runs_df=raw_runs,
        hypotheses_df=hypotheses,
    )
    assert "carbon_tradeoff" in tables
    assert not tables["carbon_tradeoff"].empty


def test_build_carbon_tradeoff_table_uses_e6_and_orders_by_co2() -> None:
    """Carbon tradeoff table should prioritize E6 rows and sort by per-task CO2."""
    summary = pd.DataFrame(
        [
            {
                "study_id": "E1_scalability",
                "method": "greedy",
                "method_label": "Greedy",
                "avg_latency_mean": 1.2,
                "throughput_mean": 2.3,
                "co2_total_lb_mean": 400.0,
                "co2_per_completed_task_lb_mean": 4.0,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "min-load",
                "method_label": "Min-Load",
                "avg_latency_mean": 1.1,
                "throughput_mean": 2.4,
                "co2_total_lb_mean": 160.0,
                "co2_per_completed_task_lb_mean": 1.6,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "method": "carbon-aware",
                "method_label": "Carbon-Aware",
                "avg_latency_mean": 1.3,
                "throughput_mean": 2.1,
                "co2_total_lb_mean": 90.0,
                "co2_per_completed_task_lb_mean": 0.9,
            },
        ]
    )

    table = build_carbon_tradeoff_table(summary)
    assert table["method"].tolist() == ["carbon-aware", "min-load"]
    assert "co2_per_throughput_lb" in table.columns
    assert table.iloc[0]["rank_co2"] == 1

