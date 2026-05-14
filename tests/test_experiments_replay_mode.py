"""Integration tests for replay-manifest verification mode."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

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
from project.experiments.mode_advanced import run_replay_manifest_mode
from project.experiments.mode_single_compare import run_single_mode


def _minimal_config(output_dir: Path) -> ExperimentConfig:
    """Create deterministic lightweight config for replay tests."""
    return ExperimentConfig(
        name="test-replay-mode",
        scenario="static",
        simulation=SimulationConfig(time_horizon=2, seed=17, step_seconds=1.0),
        intelligence=IntelligenceConfig(enabled=False, adaptive_algorithm=False),
        llm=LLMConfig(enabled=False, provider="mock"),
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


def test_run_replay_manifest_mode_generates_verification_artifacts() -> None:
    """Replay mode should produce CSV + JSON report + replay manifest."""
    config = _minimal_config(_workspace_test_output_dir("replay-mode"))
    _state, artifacts = run_single_mode(config, ["--unit-test-source"])
    source_manifest_path = Path(artifacts["run_manifest_json"])

    run_replay_manifest_mode(
        manifest_path=str(source_manifest_path),
        runs=3,
        cli_args=["--replay-manifest", str(source_manifest_path), "--replay-runs", "3"],
    )

    replay_dir = source_manifest_path.parent / "replay_verification"
    replay_csv = replay_dir / "replay_runs.csv"
    replay_report = replay_dir / "replay_verification_report.json"
    replay_manifest = replay_dir / "replay_manifest.json"
    assert replay_csv.exists()
    assert replay_report.exists()
    assert replay_manifest.exists()

    with replay_report.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["runs"] == 3
    assert payload["reproducible"] is True
    assert payload["matches_source"] is True


def test_run_replay_manifest_mode_rejects_missing_manifest() -> None:
    """Replay mode should fail fast when source manifest path does not exist."""
    missing_path = Path("outputs") / "test-suite" / f"missing-{uuid4().hex}.json"
    with pytest.raises(ValueError, match="Manifest file not found"):
        run_replay_manifest_mode(
            manifest_path=str(missing_path),
            runs=2,
            cli_args=["--replay-manifest", str(missing_path)],
        )
