"""Unit tests for publication summary statistics validation."""

from __future__ import annotations

import pandas as pd

from project.experiments.publication_validation import (
    validate_carbon_summary_table,
    validate_hypotheses_table,
    validate_scenario_calibration_table,
    validate_summary_statistics,
)


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


def _valid_hypotheses_df() -> pd.DataFrame:
    """Build valid H1-H5 hypothesis table for validator tests."""
    return pd.DataFrame(
        [
            {
                "hypothesis": "H1",
                "title": "Adaptivity",
                "criterion": "c",
                "delta_latency": 0.2,
                "delta_load_imbalance": 0.1,
                "confirmed": True,
                "significance_supported": True,
                "p_value_core": 0.03,
                "effect_size_core_cliffs_delta": 0.4,
                "sample_size_core_left": 12.0,
                "sample_size_core_right": 12.0,
                "significant_core": True,
            },
            {
                "hypothesis": "H2",
                "title": "MAS",
                "criterion": "c",
                "delta_throughput_failures": 0.3,
                "delta_stability_failures": 0.15,
                "confirmed": True,
                "significance_supported": True,
                "p_value_core": 0.02,
                "effect_size_core_cliffs_delta": 0.45,
                "sample_size_core_left": 10.0,
                "sample_size_core_right": 10.0,
                "significant_core": True,
            },
            {
                "hypothesis": "H3",
                "title": "ML/ZNN",
                "criterion": "c",
                "delta_latency_dynamic": 0.05,
                "confirmed": True,
                "significance_supported": True,
                "p_value_core": 0.04,
                "effect_size_core_cliffs_delta": 0.3,
                "sample_size_core_left": 8.0,
                "sample_size_core_right": 8.0,
                "significant_core": True,
            },
            {
                "hypothesis": "H4",
                "title": "Hybrid",
                "criterion": "c",
                "delta_latency_hybrid_vs_best_baseline": 0.07,
                "confirmed": True,
                "significance_supported": True,
                "p_value_core": 0.01,
                "effect_size_core_cliffs_delta": 0.5,
                "sample_size_core_left": 6.0,
                "sample_size_core_right": 6.0,
                "significant_core": True,
            },
            {
                "hypothesis": "H5",
                "title": "LLM",
                "criterion": "c",
                "delta_adaptivity_llm_vs_algorithmic": 0.12,
                "delta_latency_llm_vs_algorithmic": 0.04,
                "confirmed": False,
                "significance_supported": False,
                "p_value_core": 0.30,
                "effect_size_core_cliffs_delta": 0.15,
                "sample_size_core_left": 6.0,
                "sample_size_core_right": 6.0,
                "significant_core": False,
            },
        ]
    )


def test_validate_hypotheses_table_ok() -> None:
    """Hypotheses validator should pass for complete H1-H5 table."""
    result = validate_hypotheses_table(_valid_hypotheses_df())
    assert result.ok is True
    assert result.errors == []
    assert result.row_count == 5


def test_validate_hypotheses_table_reports_contract_errors() -> None:
    """Hypotheses validator should fail on schema and value violations."""
    bad = _valid_hypotheses_df().copy()
    bad["confirmed"] = bad["confirmed"].astype(object)
    bad.loc[0, "hypothesis"] = "HX"
    bad.loc[1, "confirmed"] = "yes"
    bad.loc[2, "delta_latency_dynamic"] = float("nan")
    bad.loc[3, "p_value_core"] = 1.5
    bad["significant_core"] = bad["significant_core"].astype(object)
    bad.loc[4, "significant_core"] = "yes"
    bad = bad.drop(columns=["delta_latency_hybrid_vs_best_baseline"])
    result = validate_hypotheses_table(bad)
    assert result.ok is False
    assert any("Missing hypotheses rows" in err for err in result.errors)
    assert any("Unexpected hypothesis rows" in err for err in result.errors)
    assert any("missing metric column 'delta_latency_hybrid_vs_best_baseline'" in err for err in result.errors)
    assert any("'confirmed' must be boolean" in err for err in result.errors)
    assert any("optional metric 'p_value_core' must be in [0, 1]" in err for err in result.errors)
    assert any("optional metric 'significant_core' must be boolean" in err for err in result.errors)


def _valid_scenario_calibration_df() -> pd.DataFrame:
    """Build valid scenario-calibration table rows for H2-H5."""
    return pd.DataFrame(
        [
            {
                "hypothesis": "H2",
                "study_id": "E3_robustness",
                "required_scenarios": "node-failures",
                "observed_scenarios": "node-failures",
                "missing_scenarios": "",
                "run_count": 12,
                "seed_count": 3,
                "method_count": 4,
                "generated_tasks_mean": 20.0,
                "node_failure_events_mean": 1.5,
                "failure_requeued_tasks_mean": 3.0,
                "llm_guarded_decisions_mean": 0.0,
                "calibration_supported": True,
                "calibration_status": "calibrated",
                "calibration_reason": "calibrated stress coverage confirmed",
            },
            {
                "hypothesis": "H3",
                "study_id": "E2_adaptivity",
                "required_scenarios": "dynamic-load,peak-load",
                "observed_scenarios": "dynamic-load,peak-load",
                "missing_scenarios": "",
                "run_count": 18,
                "seed_count": 3,
                "method_count": 6,
                "generated_tasks_mean": 32.0,
                "node_failure_events_mean": 0.0,
                "failure_requeued_tasks_mean": 0.0,
                "llm_guarded_decisions_mean": 0.0,
                "calibration_supported": True,
                "calibration_status": "calibrated",
                "calibration_reason": "calibrated stress coverage confirmed",
            },
            {
                "hypothesis": "H4",
                "study_id": "E4_hybrid_vs_classical",
                "required_scenarios": "dynamic-load",
                "observed_scenarios": "dynamic-load",
                "missing_scenarios": "",
                "run_count": 15,
                "seed_count": 3,
                "method_count": 5,
                "generated_tasks_mean": 25.0,
                "node_failure_events_mean": 0.0,
                "failure_requeued_tasks_mean": 0.0,
                "llm_guarded_decisions_mean": 0.0,
                "calibration_supported": True,
                "calibration_status": "calibrated",
                "calibration_reason": "calibrated stress coverage confirmed",
            },
            {
                "hypothesis": "H5",
                "study_id": "E5_llm_vs_algorithmic",
                "required_scenarios": "dynamic-load,peak-load",
                "observed_scenarios": "dynamic-load,peak-load",
                "missing_scenarios": "",
                "run_count": 9,
                "seed_count": 3,
                "method_count": 3,
                "generated_tasks_mean": 24.0,
                "node_failure_events_mean": 0.0,
                "failure_requeued_tasks_mean": 0.0,
                "llm_guarded_decisions_mean": 2.0,
                "calibration_supported": True,
                "calibration_status": "calibrated",
                "calibration_reason": "calibrated stress coverage confirmed",
            },
        ]
    )


def test_validate_scenario_calibration_table_ok() -> None:
    """Scenario calibration validator should pass on complete calibrated rows."""
    result = validate_scenario_calibration_table(_valid_scenario_calibration_df())
    assert result.ok is True
    assert result.errors == []
    assert result.row_count == 4


def test_validate_scenario_calibration_table_reports_errors() -> None:
    """Scenario calibration validator should fail on schema/type/value issues."""
    bad_schema = _valid_scenario_calibration_df().drop(columns=["missing_scenarios"])
    schema_result = validate_scenario_calibration_table(bad_schema)
    assert schema_result.ok is False
    assert any("Missing required column 'missing_scenarios'" in err for err in schema_result.errors)

    bad_values = _valid_scenario_calibration_df().copy()
    bad_values.loc[0, "hypothesis"] = "HX"
    bad_values["calibration_supported"] = bad_values["calibration_supported"].astype(object)
    bad_values.loc[1, "calibration_supported"] = "yes"
    bad_values.loc[2, "calibration_status"] = "unknown"
    bad_values.loc[3, "calibration_reason"] = ""
    bad_values.loc[3, "generated_tasks_mean"] = -1.0
    value_result = validate_scenario_calibration_table(bad_values)
    assert value_result.ok is False
    assert any("Missing calibration hypotheses rows" in err for err in value_result.errors)
    assert any("Unexpected calibration hypotheses rows" in err for err in value_result.errors)
    assert any("'calibration_supported' must be boolean" in err for err in value_result.errors)
    assert any("calibration_status must be calibrated/under-calibrated" in err for err in value_result.errors)
    assert any("calibration_reason must be non-empty" in err for err in value_result.errors)


def test_validate_carbon_summary_table_ok() -> None:
    """Carbon summary validator should pass on valid rows."""
    table = pd.DataFrame(
        [
            {
                "rank_co2": 1,
                "method": "carbon-aware",
                "method_label": "Carbon-Aware",
                "baseline_method": "min-load",
                "co2_per_completed_task_lb_mean": 1.1,
                "co2_total_lb_mean": 120.0,
                "delta_latency_vs_min_load": 0.05,
                "delta_throughput_vs_min_load": -0.03,
                "delta_co2_total_vs_min_load_lb": -40.0,
                "delta_co2_per_task_vs_min_load_lb": -0.5,
                "co2_total_reduction_vs_min_load_pct": 25.0,
                "co2_per_task_reduction_vs_min_load_pct": 31.25,
            },
            {
                "rank_co2": 2,
                "method": "min-load",
                "method_label": "Min-Load",
                "baseline_method": "min-load",
                "co2_per_completed_task_lb_mean": 1.6,
                "co2_total_lb_mean": 160.0,
                "delta_latency_vs_min_load": 0.0,
                "delta_throughput_vs_min_load": 0.0,
                "delta_co2_total_vs_min_load_lb": 0.0,
                "delta_co2_per_task_vs_min_load_lb": 0.0,
                "co2_total_reduction_vs_min_load_pct": 0.0,
                "co2_per_task_reduction_vs_min_load_pct": 0.0,
            },
        ]
    )
    result = validate_carbon_summary_table(table)
    assert result.ok is True
    assert result.errors == []
    assert result.row_count == 2


def test_validate_carbon_summary_table_reports_errors() -> None:
    """Carbon summary validator should fail on missing columns and bad values."""
    table = pd.DataFrame(
        [
            {
                "rank_co2": 0,
                "method": "",
                "method_label": "Bad",
                "baseline_method": "",
                "co2_per_completed_task_lb_mean": -1.0,
                "co2_total_lb_mean": -2.0,
                "delta_latency_vs_min_load": float("nan"),
                "delta_throughput_vs_min_load": 0.0,
                "delta_co2_total_vs_min_load_lb": 0.0,
                "delta_co2_per_task_vs_min_load_lb": 0.0,
                "co2_total_reduction_vs_min_load_pct": -5.0,
            }
        ]
    )
    result = validate_carbon_summary_table(table)
    assert result.ok is False
    assert any("Missing required column 'co2_per_task_reduction_vs_min_load_pct'" in err for err in result.errors)
