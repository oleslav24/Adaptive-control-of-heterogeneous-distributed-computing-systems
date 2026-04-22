from __future__ import annotations

from project.core.agent import Agent, AgentMessage
from project.core.models import Node, Task


class ComputeAgent(Agent):
    def __init__(self, name: str = "compute") -> None:
        super().__init__(name=name)
        self._plan: list[tuple[Task, str]] = []
        self._node_bandwidth: dict[str, float] = {}
        self._blocked_nodes: set[str] = set()
        self._urgent_task_ids: set[str] = set()

    def decide(self) -> None:
        if self.context is None:
            return
        self._refresh_policies()

        queued = self.context.pop_queued_tasks()
        if not queued:
            self._plan = []
            return

        self._plan = []
        unassigned: list[Task] = []
        ordered = sorted(
            queued,
            key=lambda task: (
                0 if task.id in self._urgent_task_ids else 1,
                task.deadline,
                task.arrival_time,
            ),
        )
        for task in ordered:
            node = self._select_node(task)
            if node is None:
                unassigned.append(task)
                continue
            self._plan.append((task, node.id))

        self.context.requeue_tasks(unassigned)
        self.send(
            AgentMessage(
                sender=self.name,
                recipient="monitoring",
                topic="compute_plan",
                payload={
                    "planned_assignments": len(self._plan),
                    "unassigned_tasks": [task.id for task in unassigned],
                },
            )
        )

    def act(self) -> None:
        if self.context is None:
            return
        deferred: list[Task] = []
        assigned_count = 0
        for task, node_id in self._plan:
            if self.context.assign_task(task, node_id):
                assigned_count += 1
                continue
            task.status = "queued"
            task.assigned_node = None
            deferred.append(task)

        self.context.requeue_tasks(deferred)
        self._plan = []
        self.send(
            AgentMessage(
                sender=self.name,
                recipient=None,
                topic="assignments_done",
                payload={"assigned_count": assigned_count},
            )
        )

    def _refresh_policies(self) -> None:
        if self.context is None:
            return
        self._node_bandwidth = {node_id: float("inf") for node_id in self.context.nodes}
        self._blocked_nodes = set()
        self._urgent_task_ids = set()
        for message in self.read_messages():
            if message.topic == "bandwidth_policy":
                node_bandwidth = message.payload.get("node_bandwidth", {})
                blocked_nodes = message.payload.get("blocked_nodes", [])
                if isinstance(node_bandwidth, dict):
                    for node_id, bandwidth in node_bandwidth.items():
                        try:
                            self._node_bandwidth[str(node_id)] = float(bandwidth)
                        except (TypeError, ValueError):
                            continue
                if isinstance(blocked_nodes, list):
                    self._blocked_nodes = {str(node_id) for node_id in blocked_nodes}
            if message.topic == "deadline_alerts":
                urgent = message.payload.get("urgent_task_ids", [])
                if isinstance(urgent, list):
                    self._urgent_task_ids = {str(task_id) for task_id in urgent}

    def _select_node(self, task: Task) -> Node | None:
        if self.context is None:
            return None
        candidates = [
            node
            for node in self.context.nodes.values()
            if node.id not in self._blocked_nodes and node.can_run(task)
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda node: (
                node.load,
                -self._node_bandwidth.get(node.id, float("inf")),
                -node.cpu,
            ),
        )

