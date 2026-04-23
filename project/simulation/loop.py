from __future__ import annotations

from dataclasses import dataclass, field
import logging

from project.agents import ComputeAgent, MonitoringAgent, NetworkAgent, OptimizationAgent, QoSAgent
from project.core.agent import Agent
from project.core.config import ExperimentConfig
from project.core.models import Node, SystemState, Task
from project.simulation.context import SimulationContext
from project.simulation.mas import MultiAgentSystem
from project.simulation.network import NetworkModel
from project.simulation.scenarios import ScenarioEngine
from project.simulation.task_queue import TaskQueue

LOGGER = logging.getLogger(__name__)


@dataclass
class SimulationLoop:
    config: ExperimentConfig
    agents: list[Agent] = field(default_factory=list)
    nodes: dict[str, Node] = field(default_factory=dict)
    future_tasks: list[Task] = field(default_factory=list)
    queue: TaskQueue = field(default_factory=TaskQueue)
    running_tasks: dict[str, list[Task]] = field(default_factory=dict)
    completed_tasks: list[Task] = field(default_factory=list)
    network: NetworkModel = field(default_factory=NetworkModel)
    scenario_engine: ScenarioEngine | None = None
    context: SimulationContext | None = None
    mas: MultiAgentSystem | None = None
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
        self.scenario_engine = ScenarioEngine(config=self.config)
        self.context = SimulationContext(
            nodes=self.nodes,
            queue=self.queue,
            running_tasks=self.running_tasks,
            completed_tasks=self.completed_tasks,
            future_tasks=self.future_tasks,
            network=self.network,
            current_time=0,
            active_algorithm=self.config.optimization.algorithm,
        )
        if not self.agents:
            self.agents = [
                MonitoringAgent(),
                NetworkAgent(),
                QoSAgent(),
                OptimizationAgent(algorithm=self.config.optimization.algorithm),
                ComputeAgent(),
            ]
        self.mas = MultiAgentSystem(agents=self.agents, context=self.context)
        self._sync_state(0)
        LOGGER.info(
            "Simulation initialized: algorithm=%s nodes=%d tasks=%d horizon=%d",
            self.config.optimization.algorithm,
            len(self.nodes),
            len(self.future_tasks),
            self.config.simulation.time_horizon,
        )

    def generate_tasks(self, t: int) -> None:
        released: list[Task] = []
        while self.future_tasks and self.future_tasks[0].arrival_time <= t:
            task = self.future_tasks.pop(0)
            task.status = "queued"
            released.append(task)
        generated: list[Task] = []
        if self.scenario_engine is not None:
            generated = self.scenario_engine.generate_tasks(t)
            for task in generated:
                task.status = "queued"
        self.queue.extend(released + generated)

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
            if self.context is None or self.mas is None:
                raise RuntimeError("Simulation context is not initialized.")
            self.context.current_time = t
            if self.scenario_engine is not None:
                for event in self.scenario_engine.apply_events(t, self.context):
                    LOGGER.warning(
                        "Scenario event: time=%d kind=%s details=%s",
                        event.time,
                        event.kind,
                        event.details,
                    )
            self.generate_tasks(t)
            self.mas.step(self.state)
            self.update_state(t)
        LOGGER.info(
            "Simulation finished: completed=%d pending=%d latency=%.3f throughput=%.3f avg_load=%.3f",
            self.state.completed_tasks,
            self.state.pending_tasks,
            self.state.avg_latency,
            self.state.throughput,
            self.state.avg_load,
        )
        return self.state

    def _sync_state(self, current_time: int) -> None:
        if self.context is not None:
            self.context.current_time = current_time
        self.state.current_time = current_time
        self.state.scenario = self.config.scenario
        if self.context is not None:
            self.state.selected_algorithm = self.context.active_algorithm
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
        self.state.inactive_nodes = sorted(
            [node_id for node_id, node in self.nodes.items() if not node.is_active]
        )
        self.state.deadline_violations = sum(
            1
            for task in self.completed_tasks
            if task.finish_time is not None and task.finish_time > task.deadline
        )
        self.state.generated_tasks = (
            self.scenario_engine.generated_tasks_total
            if self.scenario_engine is not None
            else 0
        )
        latencies = [
            float(task.finish_time - task.arrival_time)
            for task in self.completed_tasks
            if task.finish_time is not None
        ]
        self.state.avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        self.state.throughput = (
            float(self.state.completed_tasks) / float(current_time)
            if current_time > 0
            else 0.0
        )
        self.state.avg_load = (
            sum(self.state.node_loads.values()) / len(self.state.node_loads)
            if self.state.node_loads
            else 0.0
        )
        self.state.mas_messages = len(self.mas.message_log) if self.mas is not None else 0
        if self.context is not None:
            self.state.mas_assignments = len(self.context.assignment_log)
        else:
            self.state.mas_assignments = 0
        self.state.completed_task_records = [
            {
                "task_id": task.id,
                "arrival_time": task.arrival_time,
                "start_time": task.start_time,
                "finish_time": task.finish_time,
                "deadline": task.deadline,
                "latency": (
                    float(task.finish_time - task.arrival_time)
                    if task.finish_time is not None
                    else None
                ),
                "duration": task.duration,
                "assigned_node": task.assigned_node,
                "algorithm": self.state.selected_algorithm,
                "scenario": self.state.scenario,
            }
            for task in self.completed_tasks
        ]
        self.state.scenario_events = (
            self.scenario_engine.events_as_dicts()
            if self.scenario_engine is not None
            else []
        )
        self.state.history.append(
            {
                "time": self.state.current_time,
                "scenario": self.state.scenario,
                "algorithm": self.state.selected_algorithm,
                "node_loads": dict(self.state.node_loads),
                "queue_size": self.state.queue_lengths["global"],
                "pending_tasks": self.state.pending_tasks,
                "completed_tasks": self.state.completed_tasks,
                "inactive_nodes": len(self.state.inactive_nodes),
                "generated_tasks": self.state.generated_tasks,
                "avg_latency": self.state.avg_latency,
                "throughput": self.state.throughput,
                "avg_load": self.state.avg_load,
                "mas_messages": self.state.mas_messages,
                "mas_assignments": self.state.mas_assignments,
            }
        )
        LOGGER.info(
            "t=%d queue=%d completed=%d latency=%.3f throughput=%.3f avg_load=%.3f",
            self.state.current_time,
            self.state.queue_lengths["global"],
            self.state.completed_tasks,
            self.state.avg_latency,
            self.state.throughput,
            self.state.avg_load,
        )
