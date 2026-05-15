"""Integration tests for scalability profiling sweep harness."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

from project.core.config import (
    ExperimentConfig,
    IntelligenceConfig,
    LLMConfig,
    ObservabilityConfig,
    SimulationConfig,
)
from project.experiments.integrity import verify_artifact_integrity_file
from project.experiments.scalability import (
    ScalabilitySweepSpec,
    run_scalability_sweep,
)


def _minimal_config(output_dir: Path) -> ExperimentConfig:
    """Build lightweight config for fast sweep tests."""
    base = ExperimentConfig(
        name="test-scalability-profile",
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
    )
    return replace(
        base,
        optimization=replace(base.optimization, compare_algorithms=["round-robin", "min-load"]),
    )


def test_scalability_sweep_persists_outputs_and_expected_runs() -> None:
    """Sweep should execute full matrix and persist reproducible artifacts."""
    config = _minimal_config(_workspace_test_output_dir("scalability-sweep"))
    spec = ScalabilitySweepSpec(
        node_counts=[2, 3],
        task_counts=[6],
        algorithms=["round-robin", "min-load"],
        repeats=2,
        topology="ring",
        scenario="static",
        strict_algorithm_comparison=True,
    )
    result = run_scalability_sweep(config=config, spec=spec, cli_args=["--scalability-profile"])

    expected_runs = len(spec.node_counts) * len(spec.task_counts) * len(spec.algorithms) * spec.repeats
    assert len(result.runs_df) == expected_runs
    assert len(result.summary_df) == len(spec.node_counts) * len(spec.task_counts) * len(spec.algorithms)
    assert set(result.runs_df["node_count"].tolist()) == {2, 3}
    assert set(result.runs_df["task_count"].tolist()) == {6}
    assert set(result.runs_df["algorithm"].tolist()) == {"round-robin", "min-load"}
    assert "scalability_manifest_json" in result.output_paths
    assert "artifact_integrity_json" in result.output_paths

    manifest_path = Path(result.output_paths["scalability_manifest_json"])
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["mode"] == "scalability-profile"
    assert manifest["extra"]["total_runs"] == expected_runs
    ok, errors = verify_artifact_integrity_file(result.output_paths["artifact_integrity_json"])
    assert ok is True
    assert errors == []


def test_scalability_sweep_strict_mode_disables_intelligence_and_llm() -> None:
    """Strict mode should switch off adaptive layers for fair algorithm timing."""
    config = _minimal_config(_workspace_test_output_dir("scalability-strict"))
    result = run_scalability_sweep(
        config=config,
        spec=ScalabilitySweepSpec(
            node_counts=[2],
            task_counts=[4],
            algorithms=["greedy"],
            repeats=1,
            topology="star",
            strict_algorithm_comparison=True,
        ),
        cli_args=["--scalability-profile"],
    )
    assert len(result.runs_df) == 1
    assert bool(result.runs_df["intelligence_enabled"].iloc[0]) is False
    assert bool(result.runs_df["llm_enabled"].iloc[0]) is False


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target
