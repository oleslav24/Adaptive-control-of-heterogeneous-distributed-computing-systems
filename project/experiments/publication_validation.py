"""Validation helpers for publication summary statistics."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd


SUMMARY_METRICS = [
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


@dataclass(slots=True)
class SummaryValidationResult:
    """Validation result for publication summary statistics."""

    ok: bool
    errors: list[str]
    row_count: int


def validate_summary_statistics(summary: pd.DataFrame) -> SummaryValidationResult:
    """Validate presence and consistency of mean/std/CI columns."""
    errors: list[str] = []
    if summary.empty:
        errors.append("Summary is empty.")
        return SummaryValidationResult(ok=False, errors=errors, row_count=0)

    required_base = ["study_id", "scenario", "method", "n_runs"]
    for column in required_base:
        if column not in summary.columns:
            errors.append(f"Missing required column '{column}'.")

    for metric in SUMMARY_METRICS:
        for suffix in ("mean", "std", "ci95", "ci95_low", "ci95_high"):
            column = f"{metric}_{suffix}"
            if column not in summary.columns:
                errors.append(f"Missing required column '{column}'.")

    if errors:
        return SummaryValidationResult(ok=False, errors=errors, row_count=int(len(summary)))

    for idx, row in summary.iterrows():
        try:
            n_runs = int(row["n_runs"])
        except Exception:  # noqa: BLE001
            errors.append(f"Row {idx}: n_runs is not integer-like.")
            continue
        if n_runs <= 0:
            errors.append(f"Row {idx}: n_runs must be > 0.")

        for metric in SUMMARY_METRICS:
            mean = _as_float(row[f"{metric}_mean"])
            std = _as_float(row[f"{metric}_std"])
            ci = _as_float(row[f"{metric}_ci95"])
            low = _as_float(row[f"{metric}_ci95_low"])
            high = _as_float(row[f"{metric}_ci95_high"])

            if None in {mean, std, ci, low, high}:
                errors.append(f"Row {idx}: metric '{metric}' has non-numeric values.")
                continue
            if std < 0.0:
                errors.append(f"Row {idx}: metric '{metric}' has negative std.")
            if ci < 0.0:
                errors.append(f"Row {idx}: metric '{metric}' has negative ci95.")
            if low > mean or mean > high:
                errors.append(
                    f"Row {idx}: metric '{metric}' violates CI bounds (low <= mean <= high)."
                )
            # For single-run groups CI and std should collapse to zero.
            if n_runs == 1 and (abs(std) > 1e-12 or abs(ci) > 1e-12):
                errors.append(
                    f"Row {idx}: metric '{metric}' must have std=0 and ci95=0 when n_runs=1."
                )

    return SummaryValidationResult(
        ok=not errors,
        errors=errors,
        row_count=int(len(summary)),
    )


def _as_float(value: Any) -> float | None:
    """Convert value to finite float or return None."""
    try:
        parsed = float(value)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(parsed):
        return None
    return parsed

