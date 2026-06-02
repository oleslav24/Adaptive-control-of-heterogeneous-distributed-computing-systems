"""Validation helpers for publication summary statistics."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
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


def validate_hypotheses_table(hypotheses: pd.DataFrame) -> SummaryValidationResult:
    """Validate hypotheses table schema and H1-H5 contract."""
    errors: list[str] = []
    if hypotheses.empty:
        errors.append("Hypotheses table is empty.")
        return SummaryValidationResult(ok=False, errors=errors, row_count=0)

    required_columns = {"hypothesis", "title", "criterion", "confirmed"}
    missing = sorted(required_columns - set(hypotheses.columns))
    for column in missing:
        errors.append(f"Missing required column '{column}'.")
    if missing:
        return SummaryValidationResult(ok=False, errors=errors, row_count=int(len(hypotheses)))

    required_hypotheses = {"H1", "H2", "H3", "H4", "H5"}
    seen = [str(value).strip() for value in hypotheses["hypothesis"].tolist()]
    seen_set = set(seen)
    missing_h = sorted(required_hypotheses - seen_set)
    extra_h = sorted(seen_set - required_hypotheses)
    if missing_h:
        errors.append(f"Missing hypotheses rows: {', '.join(missing_h)}.")
    if extra_h:
        errors.append(f"Unexpected hypothesis rows: {', '.join(extra_h)}.")
    if len(seen) != len(seen_set):
        errors.append("Duplicate hypothesis identifiers are not allowed.")

    hypothesis_metric_columns: dict[str, list[str]] = {
        "H1": ["delta_latency", "delta_load_imbalance"],
        "H2": ["delta_throughput_failures", "delta_stability_failures"],
        "H3": ["delta_latency_dynamic"],
        "H4": ["delta_latency_hybrid_vs_best_baseline"],
        "H5": ["delta_adaptivity_llm_vs_algorithmic", "delta_latency_llm_vs_algorithmic"],
    }

    indexed = hypotheses.set_index("hypothesis", drop=False)
    for hypothesis, columns in hypothesis_metric_columns.items():
        if hypothesis not in indexed.index:
            continue
        row = indexed.loc[hypothesis]
        confirmed = row.get("confirmed")
        if not isinstance(confirmed, (bool, np.bool_)):
            errors.append(f"Row {hypothesis}: 'confirmed' must be boolean.")
        for column in columns:
            if column not in hypotheses.columns:
                errors.append(f"Row {hypothesis}: missing metric column '{column}'.")
                continue
            if _as_float(row.get(column)) is None:
                errors.append(f"Row {hypothesis}: metric '{column}' must be finite numeric.")
        if "significance_supported" in hypotheses.columns:
            if not isinstance(row.get("significance_supported"), (bool, np.bool_)):
                errors.append(f"Row {hypothesis}: 'significance_supported' must be boolean.")

    optional_significance_numeric_prefixes = ("p_value_", "effect_size_", "sample_size_")
    optional_significance_boolean_prefixes = ("significant_",)
    for idx, row in hypotheses.iterrows():
        for column in hypotheses.columns:
            if str(column).startswith(optional_significance_numeric_prefixes):
                value = row.get(column)
                if pd.isna(value):
                    continue
                numeric = _as_float(value)
                if numeric is None:
                    errors.append(f"Row {idx}: optional metric '{column}' must be finite numeric.")
                    continue
                if str(column).startswith("p_value_") and (numeric < 0.0 or numeric > 1.0):
                    errors.append(f"Row {idx}: optional metric '{column}' must be in [0, 1].")
                if str(column).startswith("sample_size_") and numeric < 0.0:
                    errors.append(f"Row {idx}: optional metric '{column}' must be >= 0.")
            if str(column).startswith(optional_significance_boolean_prefixes):
                value = row.get(column)
                if pd.isna(value):
                    continue
                if not isinstance(value, (bool, np.bool_)):
                    errors.append(f"Row {idx}: optional metric '{column}' must be boolean.")

    return SummaryValidationResult(
        ok=not errors,
        errors=errors,
        row_count=int(len(hypotheses)),
    )


def validate_scenario_calibration_table(
    scenario_calibration: pd.DataFrame,
) -> SummaryValidationResult:
    """Validate scenario-calibration table for H2-H5 stress-evidence contract."""
    errors: list[str] = []
    if scenario_calibration.empty:
        errors.append("Scenario calibration table is empty.")
        return SummaryValidationResult(ok=False, errors=errors, row_count=0)

    required_columns = {
        "hypothesis",
        "study_id",
        "required_scenarios",
        "observed_scenarios",
        "missing_scenarios",
        "run_count",
        "seed_count",
        "method_count",
        "generated_tasks_mean",
        "node_failure_events_mean",
        "failure_requeued_tasks_mean",
        "llm_guarded_decisions_mean",
        "calibration_supported",
        "calibration_status",
        "calibration_reason",
    }
    missing = sorted(required_columns - set(scenario_calibration.columns))
    for column in missing:
        errors.append(f"Missing required column '{column}'.")
    if missing:
        return SummaryValidationResult(
            ok=False,
            errors=errors,
            row_count=int(len(scenario_calibration)),
        )

    expected_hypotheses = {"H2", "H3", "H4", "H5"}
    seen = [str(value).strip() for value in scenario_calibration["hypothesis"].tolist()]
    seen_set = set(seen)
    missing_h = sorted(expected_hypotheses - seen_set)
    extra_h = sorted(seen_set - expected_hypotheses)
    if missing_h:
        errors.append(f"Missing calibration hypotheses rows: {', '.join(missing_h)}.")
    if extra_h:
        errors.append(f"Unexpected calibration hypotheses rows: {', '.join(extra_h)}.")
    if len(seen) != len(seen_set):
        errors.append("Duplicate calibration hypothesis identifiers are not allowed.")

    numeric_columns = (
        "run_count",
        "seed_count",
        "method_count",
        "generated_tasks_mean",
        "node_failure_events_mean",
        "failure_requeued_tasks_mean",
        "llm_guarded_decisions_mean",
    )
    for idx, row in scenario_calibration.iterrows():
        for column in numeric_columns:
            value = _as_float(row.get(column))
            if value is None:
                errors.append(f"Row {idx}: metric '{column}' must be finite numeric.")
                continue
            if value < 0.0:
                errors.append(f"Row {idx}: metric '{column}' must be >= 0.")
        supported = row.get("calibration_supported")
        if not isinstance(supported, (bool, np.bool_)):
            errors.append(f"Row {idx}: 'calibration_supported' must be boolean.")
        status = str(row.get("calibration_status", "")).strip()
        if status not in {"calibrated", "under-calibrated"}:
            errors.append(f"Row {idx}: calibration_status must be calibrated/under-calibrated.")
        reason = str(row.get("calibration_reason", "")).strip()
        if not reason:
            errors.append(f"Row {idx}: calibration_reason must be non-empty.")
        run_count = _as_float(row.get("run_count")) or 0.0
        if supported is True and run_count <= 0:
            errors.append(f"Row {idx}: calibrated row must have run_count > 0.")

    return SummaryValidationResult(
        ok=not errors,
        errors=errors,
        row_count=int(len(scenario_calibration)),
    )


def validate_carbon_summary_table(carbon_summary: pd.DataFrame) -> SummaryValidationResult:
    """Validate carbon summary table schema and numeric sanity checks."""
    errors: list[str] = []
    if carbon_summary.empty:
        return SummaryValidationResult(ok=True, errors=errors, row_count=0)

    required_columns = {
        "rank_co2",
        "method",
        "method_label",
        "baseline_method",
        "co2_per_completed_task_lb_mean",
        "co2_total_lb_mean",
        "delta_latency_vs_min_load",
        "delta_throughput_vs_min_load",
        "delta_co2_total_vs_min_load_lb",
        "delta_co2_per_task_vs_min_load_lb",
        "co2_total_reduction_vs_min_load_pct",
        "co2_per_task_reduction_vs_min_load_pct",
    }
    missing = sorted(required_columns - set(carbon_summary.columns))
    for column in missing:
        errors.append(f"Missing required column '{column}'.")
    if missing:
        return SummaryValidationResult(ok=False, errors=errors, row_count=int(len(carbon_summary)))

    seen_ranks: set[int] = set()
    for idx, row in carbon_summary.iterrows():
        rank = _as_float(row.get("rank_co2"))
        if rank is None:
            errors.append(f"Row {idx}: rank_co2 must be numeric.")
        else:
            rank_int = int(rank)
            if rank_int < 1:
                errors.append(f"Row {idx}: rank_co2 must be >= 1.")
            if rank_int in seen_ranks:
                errors.append(f"Row {idx}: duplicate rank_co2 value {rank_int}.")
            seen_ranks.add(rank_int)

        for metric in (
            "co2_per_completed_task_lb_mean",
            "co2_total_lb_mean",
            "co2_total_reduction_vs_min_load_pct",
            "co2_per_task_reduction_vs_min_load_pct",
        ):
            value = _as_float(row.get(metric))
            if value is None:
                errors.append(f"Row {idx}: metric '{metric}' must be finite numeric.")
                continue
            if metric.endswith("_pct"):
                if value < -1e-9 or value > 1000.0:
                    errors.append(f"Row {idx}: metric '{metric}' must be in [0, 1000].")
            elif value < 0.0:
                errors.append(f"Row {idx}: metric '{metric}' must be >= 0.")

        for delta in (
            "delta_latency_vs_min_load",
            "delta_throughput_vs_min_load",
            "delta_co2_total_vs_min_load_lb",
            "delta_co2_per_task_vs_min_load_lb",
        ):
            if _as_float(row.get(delta)) is None:
                errors.append(f"Row {idx}: metric '{delta}' must be finite numeric.")

        method = str(row.get("method", "")).strip()
        baseline = str(row.get("baseline_method", "")).strip()
        if not method:
            errors.append(f"Row {idx}: method must be non-empty.")
        if not baseline:
            errors.append(f"Row {idx}: baseline_method must be non-empty.")

    return SummaryValidationResult(
        ok=not errors,
        errors=errors,
        row_count=int(len(carbon_summary)),
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
