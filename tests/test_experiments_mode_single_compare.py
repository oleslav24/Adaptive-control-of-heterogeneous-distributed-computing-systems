"""Integration tests for single and compare experiment mode handlers."""

from __future__ import annotations

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
from project.experiments.mode_single_compare import run_comparison_mode, run_single_mode


def _minimal_config(output_dir: Path) -> ExperimentConfig:
    """Create deterministic lightweight config for mode tests."""
    return ExperimentConfig(
        name="test-single-compare-mode",
        scenario="static",
        simulation=SimulationConfig(time_horizon=2, seed=7, step_seconds=1.0),
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
                data_size=16.0,
                deadline=3.0,
                arrival_time=0,
                duration=1,
            ),
            Task(
                id="task-2",
                cpu_required=1.0,
                memory_required=1.0,
                data_size=16.0,
                deadline=3.0,
                arrival_time=0,
                duration=1,
            ),
        ],
    )


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_run_single_mode_returns_state_and_artifact_map() -> None:
    """Single mode should run simulation and persist run manifest artifacts."""
    config = _minimal_config(_workspace_test_output_dir("single-mode"))
    state, artifacts = run_single_mode(config, ["--unit-test-single"])
    assert state.current_time == config.simulation.time_horizon
    assert "run_manifest_json" in artifacts
    assert Path(artifacts["run_manifest_json"]).exists()
    assert "summary_json" in artifacts
    assert Path(artifacts["summary_json"]).exists()


def test_run_comparison_mode_writes_csv_and_manifest() -> None:
    """Comparison mode should persist aggregate CSV and manifest artifacts."""
    output_dir = _workspace_test_output_dir("compare-mode")
    config = _minimal_config(output_dir)
    run_comparison_mode(
        config,
        algorithms=["round-robin", "min-load"],
        cli_args=["--unit-test-compare"],
    )
    comparison_dir = output_dir / config.name / config.scenario
    comparison_csv = comparison_dir / "comparison.csv"
    comparison_manifest = comparison_dir / "comparison_manifest.json"
    assert comparison_csv.exists()
    assert comparison_manifest.exists()

