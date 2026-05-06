"""Integration tests for scenario engine events."""

from __future__ import annotations

from dataclasses import replace

from project.core.config import (
    ExperimentConfig,
    NodeFailureEventConfig,
    NodeFailuresConfig,
    ScenarioConfig,
)
from project.core.models import NetworkEdge, Node, Task
from project.simulation.context import SimulationContext
from project.simulation.network import NetworkModel
from project.simulation.scenarios import ScenarioEngine
from project.simulation.task_queue import TaskQueue


def test_node_failure_event_requeues_running_tasks_and_schedules_recovery() -> None:
    """Failure event should deactivate node, requeue tasks, and restore node later."""
    config = ExperimentConfig(
        name="test-scenario-failure",
        scenario="node-failures",
        nodes=[
            Node(id="node-a", cpu=8.0, memory=16.0, gpu=0.0),
            Node(id="node-b", cpu=8.0, memory=16.0, gpu=0.0),
        ],
        network_edges=[
            NetworkEdge(source="node-a", target="node-b", bandwidth=1000.0, latency=5.0),
            NetworkEdge(source="node-b", target="node-a", bandwidth=1000.0, latency=5.0),
        ],
    )
    config = replace(
        config,
        scenarios=ScenarioConfig(
            node_failures=NodeFailuresConfig(
                enabled=True,
                events=[NodeFailureEventConfig(node_id="node-b", time=2, duration=2)],
            )
        ),
    )

    running_task = Task(
        id="task-running",
        cpu_required=2.0,
        memory_required=2.0,
        data_size=64.0,
        deadline=20.0,
        arrival_time=0,
        duration=3,
    )
    running_task.status = "running"
    running_task.assigned_node = "node-b"

    queue = TaskQueue()
    context = SimulationContext(
        nodes={
            "node-a": Node(id="node-a", cpu=8.0, memory=16.0, gpu=0.0),
            "node-b": Node(
                id="node-b",
                cpu=8.0,
                memory=16.0,
                gpu=0.0,
                used_cpu=2.0,
                used_memory=2.0,
            ),
        },
        queue=queue,
        running_tasks={"node-a": [], "node-b": [running_task]},
        completed_tasks=[],
        future_tasks=[],
        network=NetworkModel.from_edges(config.network_edges),
    )
    scenario_engine = ScenarioEngine(config)

    failure_events = scenario_engine.apply_events(2, context)
    assert len(failure_events) == 1
    assert failure_events[0].kind == "node_failed"
    assert context.nodes["node-b"].is_active is False
    assert context.running_tasks["node-b"] == []
    queued = context.queued_tasks()
    assert len(queued) == 1
    assert queued[0].id == "task-running"
    assert queued[0].status == "queued"
    assert queued[0].assigned_node is None

    recovery_events = scenario_engine.apply_events(4, context)
    assert len(recovery_events) == 1
    assert recovery_events[0].kind == "node_recovered"
    assert context.nodes["node-b"].is_active is True
