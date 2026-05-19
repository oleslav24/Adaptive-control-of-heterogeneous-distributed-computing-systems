"""Mutable runtime context shared by MAS agents during simulation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from project.core.models import Node, Task
from project.simulation.network import NetworkModel
from project.simulation.task_queue import TaskQueue


@dataclass
class SimulationContext:
    """Operational state and utility methods for one simulation run."""

    nodes: dict[str, Node]
    queue: TaskQueue
    running_tasks: dict[str, list[Task]]
    completed_tasks: list[Task]
    future_tasks: deque[Task]
    network: NetworkModel
    current_time: int = 0
    active_algorithm: str = "min-load"
    predicted_queue: float = 0.0
    predicted_avg_load: float = 0.0
    prediction_node_bias: dict[str, float] = field(default_factory=dict)
    llm_algorithm_hint: str | None = None
    llm_node_bias: dict[str, float] = field(default_factory=dict)
    llm_confidence: float = 0.0
    llm_reason: str = ""
    llm_source: str = "none"
    llm_raw_response: str = ""
    llm_actions_applied: int = 0
    node_co2_lb_per_mwh: dict[str, float] = field(default_factory=dict)
    node_co2e_lb_per_mwh: dict[str, float] = field(default_factory=dict)
    node_renewable_share: dict[str, float] = field(default_factory=dict)
    assignment_log: list[dict[str, object]] = field(default_factory=list)

    def pop_queued_tasks(self) -> list[Task]:
        """Pop all currently queued tasks."""
        return self.queue.pop_all()

    def requeue_tasks(self, tasks: list[Task]) -> None:
        """Return tasks back to queue preserving order."""
        self.queue.extend(tasks)

    def queued_tasks(self) -> list[Task]:
        """Peek queued tasks without removing them."""
        return self.queue.peek_all()

    def running_task_list(self) -> list[Task]:
        """Flatten running tasks across all nodes."""
        items: list[Task] = []
        for tasks in self.running_tasks.values():
            items.extend(tasks)
        return items

    def assign_task(self, task: Task, node_id: str) -> bool:
        """Assign task to node if capacity allows and record assignment log."""
        node = self.nodes.get(node_id)
        if node is None or not node.can_run(task):
            return False
        node.assign(task)
        task.status = "running"
        task.assigned_node = node_id
        if task.start_time is None:
            task.start_time = self.current_time
        self.running_tasks[node_id].append(task)
        self.assignment_log.append(
            {
                "time": self.current_time,
                "task_id": task.id,
                "node_id": node_id,
                "algorithm": self.active_algorithm,
            }
        )
        return True
