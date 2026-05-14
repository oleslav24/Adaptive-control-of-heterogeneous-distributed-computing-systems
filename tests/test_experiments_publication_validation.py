"""Unit tests for publication summary statistics validation."""

from __future__ import annotations

import pandas as pd

from project.experiments.publication_validation import validate_summary_statistics


def _valid_summary_row(n_runs: int = 3) -> dict[str, object]:
    """Build minimal valid summary row for validator tests."""
    metrics = [
        "makespan",
        "avg_latency",
        "latency_p95",
        "load_imbalance",
        "sla_violations",
        "throughput",
        "resource_utilization",
        "adaptivity",
        "stability_latency_var",
        "stability_throughput_var",
    ]
    row: dict[str, object] = {
        "study_id": "E1_scalability",
        "scenario": "static",
        "method": "min-load",
        "n_runs": n_runs,
    }
    for metric in metrics:
        mean = 1.5
        std = 0.1 if n_runs > 1 else 0.0
        ci = 0.05 if n_runs > 1 else 0.0
        row[f"{metric}_mean"] = mean
        row[f"{metric}_std"] = std
        row[f"{metric}_ci95"] = ci
        row[f"{metric}_ci95_low"] = mean - ci
        row[f"{metric}_ci95_high"] = mean + ci
    return row


def test_validate_summary_statistics_ok() -> None:
    """Validator should pass on coherent summary table."""
    summary = pd.DataFrame([_valid_summary_row(n_runs=3), _valid_summary_row(n_runs=1)])
    result = validate_summary_statistics(summary)
    assert result.ok is True
    assert result.errors == []
    assert result.row_count == 2


def test_validate_summary_statistics_reports_contract_errors() -> None:
    """Validator should fail on missing columns and broken CI/STD contract."""
    missing_column = pd.DataFrame([_valid_summary_row(n_runs=1)]).drop(columns=["throughput_mean"])
    missing_result = validate_summary_statistics(missing_column)
    assert missing_result.ok is False
    assert any("Missing required column 'throughput_mean'" in err for err in missing_result.errors)

    row = _valid_summary_row(n_runs=1)
    row["avg_latency_std"] = 0.2  # invalid for n_runs=1
    row["avg_latency_ci95"] = -0.3
    row["avg_latency_ci95_low"] = 2.0
    row["avg_latency_ci95_high"] = 1.0
    summary = pd.DataFrame([row])
    result = validate_summary_statistics(summary)
    assert result.ok is False
    assert any("negative ci95" in err for err in result.errors)
    assert any("violates CI bounds" in err for err in result.errors)
    assert any("must have std=0 and ci95=0 when n_runs=1" in err for err in result.errors)
