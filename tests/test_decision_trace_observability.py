"""Tests for MAS/ML/ZNN/LLM decision trace observability."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from project.agents.llm import LLMAgent
from project.core.config import (
    ExperimentConfig,
    IntelligenceConfig,
    LLMConfig,
    ObservabilityConfig,
    SimulationConfig,
)
from project.core.models import NetworkEdge, Node, SystemState, Task
from project.metrics import persist_observability
from project.simulation.context import SimulationContext
from project.simulation.loop import SimulationLoop
from project.simulation.network import NetworkModel
from project.simulation.task_queue import TaskQueue


def test_simulation_persists_decision_trace_artifacts() -> None:
    """Run observability should persist compact CSV/JSON decision trace artifacts."""
    output_dir = _workspace_dir("decision-trace-run")
    state = SimulationLoop(config=_minimal_config(output_dir)).run()

    events = {str(record.get("event")) for record in state.decision_trace}
    assert {
        "prediction_signal",
        "llm_policy_guard",
        "algorithm_policy",
        "compute_plan",
        "applied_policy",
    }.issubset(events)

    artifacts = persist_observability(
        state=state,
        output_dir=output_dir / "artifacts",
        save_csv=True,
        save_json=True,
        save_plots=False,
    )

    assert "decision_trace_csv" in artifacts
    assert "decision_trace_json" in artifacts
    trace_json = Path(artifacts["decision_trace_json"])
    trace_csv = Path(artifacts["decision_trace_csv"])
    assert trace_json.exists()
    assert trace_csv.exists()

    trace_records = json.loads(trace_json.read_text(encoding="utf-8"))
    assert any(record["event"] == "llm_policy_guard" for record in trace_records)
    assert any(record["event"] == "prediction_signal" for record in trace_records)
    assert "znn_node_bias" in trace_csv.read_text(encoding="utf-8")


def test_llm_agent_trace_records_policy_guard_clamping() -> None:
    """Trace should expose raw LLM output and clamped policy-guard decision."""
    context = _context()
    state = SystemState(
        current_time=0,
        node_loads={"node-a": 0.1},
        queue_lengths={"global": 1},
        selected_algorithm="min-load",
    )
    agent = LLMAgent(
        provider="mock",
        allowed_algorithms=["min-load"],
        allow_algorithm_override=True,
        allow_node_bias_override=True,
    )
    agent.client.complete = lambda *_args, **_kwargs: (  # type: ignore[method-assign]
        json.dumps(
            {
                "algorithm_hint": "not-allowed",
                "node_bias": {"node-a": 2.5, "ghost-node": -2.5},
                "confidence": 1.7,
                "reason": "x" * 300,
            }
        ),
        "mock",
    )

    agent.bind(context)
    agent.observe(state)
    agent.decide()

    trace = context.decision_trace[0]
    assert trace["event"] == "llm_policy_guard"
    assert trace["raw_algorithm_hint"] == "not-allowed"
    assert trace["applied_algorithm_hint"] is None
    assert trace["raw_node_bias"] == {"node-a": 2.5, "ghost-node": -2.5}
    assert trace["applied_node_bias"] == {"node-a": 0.5}
    assert trace["raw_confidence"] == 1.7
    assert trace["applied_confidence"] == 1.0
    assert len(str(trace["reason"])) == 240

    topics = [message.topic for message in agent.flush_outbox()]
    assert topics == ["llm_policy", "llm_decision"]


def _minimal_config(output_dir: Path) -> ExperimentConfig:
    """Build a small run with intelligence and mock LLM enabled."""
    nodes = [
        Node(id="node-a", cpu=8.0, memory=16.0, gpu=0.0),
        Node(id="node-b", cpu=8.0, memory=16.0, gpu=0.0),
    ]
    edges = [
        NetworkEdge(source="node-a", target="node-b", bandwidth=1000.0, latency=3.0),
        NetworkEdge(source="node-b", target="node-a", bandwidth=1000.0, latency=3.0),
    ]
    tasks = [
        Task(
            id="task-1",
            cpu_required=2.0,
            memory_required=2.0,
            data_size=64.0,
            deadline=4.0,
            arrival_time=0,
            duration=1,
        )
    ]
    config = ExperimentConfig(
        name="decision-trace-test",
        scenario="static",
        simulation=SimulationConfig(time_horizon=3, seed=7, step_seconds=1.0),
        nodes=nodes,
        network_edges=edges,
        initial_tasks=tasks,
        observability=ObservabilityConfig(
            output_dir=str(output_dir),
            save_csv=True,
            save_json=True,
            save_plots=False,
        ),
    )
    return replace(
        config,
        intelligence=IntelligenceConfig(enabled=True, adaptive_algorithm=True),
        llm=LLMConfig(
            enabled=True,
            provider="mock",
            allowed_algorithms=["round-robin", "min-load", "greedy", "carbon-aware"],
        ),
    )


def _context() -> SimulationContext:
    """Build minimal context for direct LLM-agent guard tests."""
    return SimulationContext(
        nodes={"node-a": Node(id="node-a", cpu=8.0, memory=16.0, gpu=0.0)},
        queue=TaskQueue(),
        running_tasks={"node-a": []},
        completed_tasks=[],
        future_tasks=[],
        network=NetworkModel(),
        active_algorithm="min-load",
    )


def _workspace_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target
