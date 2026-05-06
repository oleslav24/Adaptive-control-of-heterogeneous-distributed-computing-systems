"""Integration tests for end-to-end simulation loop behavior."""

from __future__ import annotations

from dataclasses import replace

from project.core.config import ExperimentConfig, IntelligenceConfig, LLMConfig, SimulationConfig
from project.core.models import NetworkEdge, Node, Task
from project.simulation.loop import SimulationLoop


def _minimal_config() -> ExperimentConfig:
    """Build deterministic, lightweight config for integration tests."""
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
        name="test-sim-loop",
        scenario="static",
        simulation=SimulationConfig(time_horizon=3, seed=7, step_seconds=1.0),
        nodes=nodes,
        network_edges=edges,
        initial_tasks=tasks,
    )
    return replace(
        config,
        intelligence=IntelligenceConfig(enabled=False, adaptive_algorithm=False),
        llm=LLMConfig(enabled=False),
    )


def test_simulation_loop_completes_task_and_updates_metrics() -> None:
    """Simulation should finish queued task and update state aggregates consistently."""
    state = SimulationLoop(config=_minimal_config()).run()

    assert state.current_time == 3
    assert state.completed_tasks == 1
    assert state.pending_tasks == 0
    assert state.deadline_violations == 0
    assert state.selected_algorithm == "min-load"
    assert state.mas_assignments >= 1
    assert state.mas_messages >= 1
    assert len(state.completed_task_records) == state.completed_tasks
    assert len(state.history) == 4  # init snapshot + one snapshot per tick
