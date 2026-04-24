"""Compute agent that performs task-to-node assignments."""

from __future__ import annotations

from project.algorithms import choose_node, normalize_algorithm
from project.core.agent import Agent, AgentMessage
from project.core.models import Node, Task


class ComputeAgent(Agent):
    """Assign queued tasks to nodes using active scheduling policies."""

    def __init__(self, name: str = "compute") -> None:
        super().__init__(name=name)
        self._plan: list[tuple[Task, str]] = []
        self._node_bandwidth: dict[str, float] = {}
        self._blocked_nodes: set[str] = set()
        self._urgent_task_ids: set[str] = set()
        self._algorithm = "min-load"
        self._rr_cursor = 0
        self._predicted_queue: float = 0.0
        self._predicted_avg_load: float = 0.0
        self._node_bias: dict[str, float] = {}
        self._llm_bias: dict[str, float] = {}
        self._llm_confidence: float = 0.0

    def decide(self) -> None:
        """Build an assignment plan for tasks currently in the queue."""
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
                    "algorithm": self._algorithm,
                    "predicted_queue": self._predicted_queue,
                    "predicted_avg_load": self._predicted_avg_load,
                    "llm_confidence": self._llm_confidence,
                    "planned_assignments": len(self._plan),
                    "unassigned_tasks": [task.id for task in unassigned],
                },
            )
        )

    def act(self) -> None:
        """Apply planned assignments and requeue tasks that could not be placed."""
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
        """Ingest policy messages from other agents and refresh local controls."""
        if self.context is None:
            return
        self._node_bandwidth = {node_id: float("inf") for node_id in self.context.nodes}
        self._blocked_nodes = set()
        self._urgent_task_ids = set()
        self._predicted_queue = 0.0
        self._predicted_avg_load = 0.0
        self._node_bias = {}
        self._llm_bias = {}
        self._llm_confidence = 0.0
        for message in self.read_messages():
            if message.topic == "optimization_policy":
                algorithm = message.payload.get("algorithm", "min-load")
                self._algorithm = normalize_algorithm(str(algorithm))
                self.context.active_algorithm = self._algorithm
            if message.topic == "prediction_signal":
                self._predicted_queue = max(
                    0.0, float(message.payload.get("predicted_queue", 0.0))
                )
                self._predicted_avg_load = min(
                    1.0, max(0.0, float(message.payload.get("predicted_avg_load", 0.0)))
                )
                bias = message.payload.get("node_bias", {})
                if isinstance(bias, dict):
                    self._node_bias = {
                        str(node_id): float(value)
                        for node_id, value in bias.items()
                    }
            if message.topic == "llm_policy":
                self._llm_confidence = max(
                    0.0, min(1.0, float(message.payload.get("confidence", 0.0)))
                )
                llm_bias = message.payload.get("node_bias", {})
                if isinstance(llm_bias, dict):
                    self._llm_bias = {
                        str(node_id): float(value)
                        for node_id, value in llm_bias.items()
                    }
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
        """Choose a node for a single task according to the active strategy."""
        if self.context is None:
            return None
        candidates = [
            node
            for node in self.context.nodes.values()
            if node.id not in self._blocked_nodes and node.can_run(task)
        ]
        if not candidates:
            return None
        if self._algorithm == "round-robin":
            selected, next_cursor = choose_node(
                algorithm=self._algorithm,
                task=task,
                candidates=candidates,
                all_node_ids=list(self.context.nodes.keys()),
                node_bandwidth=self._node_bandwidth,
                rr_cursor=self._rr_cursor,
            )
            self._rr_cursor = next_cursor
            return selected
        if self._algorithm == "greedy":
            return min(candidates, key=lambda node: self._greedy_score(task, node))
        return min(candidates, key=self._min_load_score)

    def _min_load_score(self, node: Node) -> float:
        """Score function for min-load style placement with policy modifiers."""
        predicted_target = self._predicted_avg_load
        projected_over_target = max(0.0, node.load - predicted_target)
        bias = self._node_bias.get(node.id, 0.0) + (
            self._llm_bias.get(node.id, 0.0) * self._llm_confidence
        )
        bandwidth = self._node_bandwidth.get(node.id, 1.0)
        bandwidth_penalty = 1.0 / (1.0 + max(0.0, bandwidth))
        pressure = self._predicted_queue / max(1.0, float(len(self._node_bandwidth)))
        return (
            node.load
            + 0.30 * projected_over_target
            + 0.08 * pressure
            - 0.35 * bias
            + bandwidth_penalty
            - 0.0001 * node.cpu
        )

    def _greedy_score(self, task: Task, node: Node) -> float:
        """Score function for greedy placement that favors residual capacity."""
        residual = (
            (node.cpu - (node.used_cpu + task.cpu_required))
            + 0.1 * (node.memory - (node.used_memory + task.memory_required))
        )
        bias = self._node_bias.get(node.id, 0.0) + (
            self._llm_bias.get(node.id, 0.0) * self._llm_confidence
        )
        projected_over_target = max(0.0, node.load - self._predicted_avg_load)
        return (
            -residual
            + 0.25 * projected_over_target
            - 0.25 * bias
            + 0.06 * (self._predicted_queue / max(1.0, len(self._node_bandwidth)))
        )
