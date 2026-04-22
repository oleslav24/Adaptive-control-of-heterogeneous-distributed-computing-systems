from __future__ import annotations

from dataclasses import dataclass, field

from project.core.config import ExperimentConfig
from project.core.models import Node, SystemState, Task
from project.simulation.network import NetworkModel
from project.simulation.task_queue import TaskQueue


@dataclass
class SimulationLoop:
    config: ExperimentConfig
    nodes: dict[str, Node] = field(default_factory=dict)
    future_tasks: list[Task] = field(default_factory=list)
    queue: TaskQueue = field(default_factory=TaskQueue)
    running_tasks: dict[str, list[Task]] = field(default_factory=dict)
    completed_tasks: list[Task] = field(default_factory=list)
    network: NetworkModel = field(default_factory=NetworkModel)
    state: SystemState = field(default_factory=SystemState)

    def init_system(self) -> None:
        self.nodes = {
            node.id: Node(
                id=node.id,
                cpu=node.cpu,
                memory=node.memory,
                gpu=node.gpu,
                used_cpu=node.used_cpu,
                used_memory=node.used_memory,
            )
            for node in self.config.nodes
        }
        self.network = NetworkModel.from_edges(self.config.network_edges)
        self.future_tasks = sorted(
            [
                Task(
                    id=task.id,
                    cpu_required=task.cpu_required,
                    memory_required=task.memory_required,
                    data_size=task.data_size,
                    deadline=task.deadline,
                    arrival_time=task.arrival_time,
                    duration=task.duration,
                )
                for task in self.config.initial_tasks
            ],
            key=lambda task: task.arrival_time,
        )
        self.queue = TaskQueue()
        self.running_tasks = {node_id: [] for node_id in self.nodes}
        self.completed_tasks = []
        self._sync_state(0)

    def generate_tasks(self, t: int) -> None:
        released: list[Task] = []
        while self.future_tasks and self.future_tasks[0].arrival_time <= t:
            task = self.future_tasks.pop(0)
            task.status = "queued"
            released.append(task)
        self.queue.extend(released)

    def assign_tasks(self) -> None:
        not_assigned: list[Task] = []
        for task in self.queue.pop_all():
            selected = self._select_node(task)
            if selected is None:
                not_assigned.append(task)
                continue
            selected.assign(task)
            task.status = "running"
            task.assigned_node = selected.id
            if task.start_time is None:
                task.start_time = self.state.current_time
            self.running_tasks[selected.id].append(task)
        self.queue.extend(not_assigned)

    def update_state(self, t: int) -> None:
        for node_id, tasks in self.running_tasks.items():
            node = self.nodes[node_id]
            still_running: list[Task] = []
            for task in tasks:
                task.remaining_time -= 1
                if task.remaining_time > 0:
                    still_running.append(task)
                    continue
                task.status = "completed"
                task.finish_time = t + 1
                self.completed_tasks.append(task)
                node.release(task)
            self.running_tasks[node_id] = still_running
        self._sync_state(t + 1)

    def run(self) -> SystemState:
        self.init_system()
        for t in range(self.config.simulation.time_horizon):
            self.generate_tasks(t)
            self.assign_tasks()
            self.update_state(t)
        return self.state

    def _select_node(self, task: Task) -> Node | None:
        candidates = [node for node in self.nodes.values() if node.can_run(task)]
        if not candidates:
            return None
        return min(candidates, key=lambda node: (node.load, -node.cpu))

    def _sync_state(self, current_time: int) -> None:
        self.state.current_time = current_time
        self.state.node_loads = {node_id: node.load for node_id, node in self.nodes.items()}
        self.state.queue_lengths = {"global": len(self.queue)}
        self.state.network_state = self.network.snapshot()
        self.state.running_tasks = {
            node_id: [task.id for task in tasks]
            for node_id, tasks in self.running_tasks.items()
        }
        self.state.completed_tasks = len(self.completed_tasks)
        self.state.pending_tasks = (
            len(self.future_tasks)
            + len(self.queue)
            + sum(len(tasks) for tasks in self.running_tasks.values())
        )
        self.state.deadline_violations = sum(
            1
            for task in self.completed_tasks
            if task.finish_time is not None and task.finish_time > task.deadline
        )
        self.state.history.append(
            {
                "time": self.state.current_time,
                "node_loads": dict(self.state.node_loads),
                "queue_size": self.state.queue_lengths["global"],
                "pending_tasks": self.state.pending_tasks,
                "completed_tasks": self.state.completed_tasks,
            }
        )
