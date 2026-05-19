"""Unit tests for compute agent scheduling decisions."""

from __future__ import annotations

from project.agents.compute import ComputeAgent
from project.core.agent import AgentMessage
from project.core.models import Node, Task
from project.simulation.context import SimulationContext
from project.simulation.network import NetworkModel
from project.simulation.task_queue import TaskQueue


def _task(task_id: str = "task-1") -> Task:
    return Task(
        id=task_id,
        cpu_required=2.0,
        memory_required=2.0,
        data_size=64.0,
        deadline=6.0,
        arrival_time=0,
        duration=1,
    )


def _context() -> SimulationContext:
    nodes = {
        "dirty": Node(id="dirty", cpu=8.0, memory=16.0, gpu=0.0),
        "green": Node(id="green", cpu=8.0, memory=16.0, gpu=0.0),
    }
    queue = TaskQueue()
    return SimulationContext(
        nodes=nodes,
        queue=queue,
        running_tasks={"dirty": [], "green": []},
        completed_tasks=[],
        future_tasks=[],
        network=NetworkModel(),
        node_co2_lb_per_mwh={"dirty": 1400.0, "green": 420.0},
    )


def test_compute_agent_carbon_aware_prefers_lower_co2_node() -> None:
    """Carbon-aware policy should place task on lower-CO2 node when feasible."""
    context = _context()
    task = _task()
    context.queue.enqueue(task)

    agent = ComputeAgent()
    agent.bind(context)
    agent.receive(
        AgentMessage(
            sender="optimization",
            recipient="compute",
            topic="optimization_policy",
            payload={"algorithm": "carbon-aware"},
        )
    )

    agent.decide()
    agent.act()

    assert context.active_algorithm == "carbon-aware"
    assert task.assigned_node == "green"
    assert len(context.running_tasks["green"]) == 1
    assert context.running_tasks["green"][0].id == task.id


def test_compute_agent_carbon_aware_fallback_without_carbon_map() -> None:
    """Carbon-aware policy should still assign task when carbon map is missing."""
    context = _context()
    context.node_co2_lb_per_mwh = {}
    task = _task("task-2")
    context.queue.enqueue(task)

    agent = ComputeAgent()
    agent.bind(context)
    agent.receive(
        AgentMessage(
            sender="optimization",
            recipient="compute",
            topic="optimization_policy",
            payload={"algorithm": "carbon-aware"},
        )
    )

    agent.decide()
    agent.act()

    assert task.assigned_node in {"dirty", "green"}
    assert sum(len(tasks) for tasks in context.running_tasks.values()) == 1
