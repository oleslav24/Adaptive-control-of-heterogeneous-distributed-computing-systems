"""Tests for scalability performance budget gate."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.core.config import (
    ExperimentConfig,
    IntelligenceConfig,
    LLMConfig,
    ObservabilityConfig,
    SimulationConfig,
)
from project.experiments.performance_budget import (
    PerformanceBudgetResult,
    PerformanceBudgetSpec,
    evaluate_performance_budget,
    main,
    run_performance_budget,
)


def _minimal_config(output_dir: Path) -> ExperimentConfig:
    """Build tiny deterministic config for budget gate tests."""
    return ExperimentConfig(
        name="test-performance-budget",
        scenario="static",
        simulation=SimulationConfig(time_horizon=2, seed=19, step_seconds=1.0),
        intelligence=IntelligenceConfig(enabled=True, adaptive_algorithm=True),
        llm=LLMConfig(enabled=True, provider="mock"),
        observability=ObservabilityConfig(
            output_dir=str(output_dir),
            save_csv=True,
            save_json=True,
            save_plots=False,
            plot_formats=["png"],
        ),
    )


def test_evaluate_performance_budget_detects_runtime_and_throughput_violations() -> None:
    """Threshold evaluator should report both runtime and throughput violations."""
    summary_df = pd.DataFrame(
        [
            {
                "node_count": 10,
                "task_count": 100,
                "algorithm": "min-load",
                "runtime_seconds_mean": 1.8,
                "throughput_mean": 0.02,
                "pending_tasks_mean": 9.0,
            }
        ]
    )
    spec = PerformanceBudgetSpec(
        node_counts=[10],
        task_counts=[100],
        algorithms=["min-load"],
        repeats=1,
        topology="ring",
        scenario="static",
        strict_algorithm_comparison=True,
        max_runtime_seconds=1.0,
        min_throughput=0.05,
        max_pending_tasks=8,
    )
    violations = evaluate_performance_budget(summary_df, spec)
    assert len(violations) == 3
    assert any("runtime_seconds_mean" in item for item in violations)
    assert any("throughput_mean" in item for item in violations)
    assert any("pending_tasks_mean" in item for item in violations)


def test_run_performance_budget_persists_report_and_passes() -> None:
    """Budget runner should persist report and pass for relaxed thresholds."""
    config = _minimal_config(_workspace_test_output_dir("performance-budget"))
    config = replace(
        config,
        optimization=replace(config.optimization, compare_algorithms=["min-load"]),
    )
    spec = PerformanceBudgetSpec(
        node_counts=[2],
        task_counts=[4],
        algorithms=["min-load"],
        repeats=1,
        topology="ring",
        scenario="static",
        strict_algorithm_comparison=True,
        max_runtime_seconds=2.0,
        min_throughput=0.0,
        max_pending_tasks=1000,
    )
    result = run_performance_budget(
        config=config,
        spec=spec,
        cli_args=["--performance-budget-test"],
    )
    assert result.passed is True
    assert result.violations == []
    report_path = Path(result.report_path)
    assert report_path.exists()
    with report_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["passed"] is True
    assert payload["spec"]["node_counts"] == [2]


def test_main_returns_nonzero_when_gate_fails(monkeypatch) -> None:
    """CLI should return non-zero exit code when performance budget fails."""
    config = _minimal_config(_workspace_test_output_dir("performance-budget-main"))

    monkeypatch.setattr(
        "project.experiments.performance_budget.load_config",
        lambda _path: config,
    )
    monkeypatch.setattr(
        "project.experiments.performance_budget.run_performance_budget",
        lambda config, spec, cli_args: PerformanceBudgetResult(
            passed=False,
            violations=["runtime exceeded"],
            report_path="outputs/report.json",
            output_paths={},
        ),
    )

    code = main(
        [
            "--config",
            "config.yaml",
            "--nodes",
            "2",
            "--tasks",
            "4",
            "--algorithms",
            "min-load",
        ]
    )
    assert code == 2


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target
