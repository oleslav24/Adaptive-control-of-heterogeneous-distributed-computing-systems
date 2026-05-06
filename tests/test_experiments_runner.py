"""Integration tests for batch runner invariants."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

from project.core.config import (
    ExperimentConfig,
    IntelligenceConfig,
    LLMConfig,
    NetworkEdge,
    Node,
    ObservabilityConfig,
    SimulationConfig,
)
from project.core.models import Task
from project.experiments.runner import BatchRunSpec, ExperimentRunner


def _minimal_batch_config(output_dir: Path) -> ExperimentConfig:
    """Create lightweight deterministic configuration for runner tests."""
    return ExperimentConfig(
        name="test-batch-runner",
        scenario="static",
        simulation=SimulationConfig(time_horizon=2, seed=11, step_seconds=1.0),
        intelligence=IntelligenceConfig(enabled=True, adaptive_algorithm=True),
        llm=LLMConfig(enabled=True, provider="mock"),
        observability=ObservabilityConfig(
            output_dir=str(output_dir),
            save_csv=True,
            save_json=True,
            save_plots=False,
            plot_formats=["png"],
        ),
        nodes=[
            Node(id="node-a", cpu=8.0, memory=16.0, gpu=0.0),
            Node(id="node-b", cpu=8.0, memory=16.0, gpu=0.0),
        ],
        network_edges=[
            NetworkEdge(source="node-a", target="node-b", bandwidth=1000.0, latency=3.0),
            NetworkEdge(source="node-b", target="node-a", bandwidth=1000.0, latency=3.0),
        ],
        initial_tasks=[
            Task(
                id="task-1",
                cpu_required=1.0,
                memory_required=1.0,
                data_size=32.0,
                deadline=4.0,
                arrival_time=0,
                duration=1,
            )
        ],
    )


def test_batch_runner_total_runs_and_manifest_consistency() -> None:
    """Runner should execute full scenario/algorithm/repeat matrix and persist totals."""
    config = _minimal_batch_config(_workspace_test_output_dir("batch-consistency"))
    runner = ExperimentRunner(config)
    spec = BatchRunSpec(
        scenarios=["static", "dynamic-load"],
        algorithms=["round-robin", "min-load"],
        repeats=2,
        persist_individual_runs=False,
        strict_algorithm_comparison=True,
    )
    result = runner.run_batch(spec, cli_args=["--unit-test-batch"])

    expected_runs = len(spec.scenarios) * len(spec.algorithms) * spec.repeats
    assert len(result.runs_df) == expected_runs
    assert len(result.summary_df) == len(spec.scenarios) * len(spec.algorithms)
    assert set(result.runs_df["seed"].tolist()) == {11, 12}
    assert set(result.runs_df["scenario"].tolist()) == {"static", "dynamic-load"}
    assert set(result.runs_df["algorithm"].tolist()) == {"round-robin", "min-load"}

    manifest_path = Path(result.output_paths["batch_manifest_json"])
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["extra"]["total_runs"] == expected_runs
    assert manifest["extra"]["strict_algorithm_comparison"] is True


def test_batch_runner_strict_mode_disables_intelligence_and_llm() -> None:
    """Strict comparison should force non-adaptive runs in output rows."""
    config = _minimal_batch_config(_workspace_test_output_dir("batch-strict"))
    config = replace(
        config,
        intelligence=IntelligenceConfig(enabled=True, adaptive_algorithm=True),
        llm=LLMConfig(enabled=True, provider="mock"),
    )
    runner = ExperimentRunner(config)
    result = runner.run_batch(
        BatchRunSpec(
            scenarios=["static"],
            algorithms=["min-load"],
            repeats=1,
            strict_algorithm_comparison=True,
        ),
        cli_args=["--strict-check"],
    )
    assert not result.runs_df.empty
    assert bool(result.runs_df["intelligence_enabled"].iloc[0]) is False
    assert bool(result.runs_df["llm_enabled"].iloc[0]) is False


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target
