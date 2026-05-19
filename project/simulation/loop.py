"""Main time-stepped simulation loop for the experimental testbed."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import logging

from project.agents import (
    ComputeAgent,
    LLMAgent,
    MonitoringAgent,
    NetworkAgent,
    OptimizationAgent,
    PredictionAgent,
    QoSAgent,
)
from project.core.agent import Agent
from project.core.config import ExperimentConfig
from project.core.models import Node, SystemState, Task
from project.metrics.egrid_loader import EGridLookup, default_factors, load_lookup
from project.simulation.context import SimulationContext
from project.simulation.mas import MultiAgentSystem
from project.simulation.network import NetworkModel
from project.simulation.randomness import set_global_seed
from project.simulation.scenarios import ScenarioEngine
from project.simulation.task_queue import TaskQueue

LOGGER = logging.getLogger(__name__)


@dataclass
class SimulationLoop:
    """Drive system initialization, per-tick actions, and state synchronization."""

    config: ExperimentConfig
    agents: list[Agent] = field(default_factory=list)
    nodes: dict[str, Node] = field(default_factory=dict)
    future_tasks: deque[Task] = field(default_factory=deque)
    queue: TaskQueue = field(default_factory=TaskQueue)
    running_tasks: dict[str, list[Task]] = field(default_factory=dict)
    completed_tasks: list[Task] = field(default_factory=list)
    completed_task_records: list[dict[str, object]] = field(default_factory=list)
    completed_latency_sum: float = 0.0
    completed_latency_count: int = 0
    deadline_violations_count: int = 0
    energy_consumed_mwh_total: float = 0.0
    co2_total_lb_accum: float = 0.0
    co2e_total_lb_accum: float = 0.0
    scenario_events: list[dict[str, object]] = field(default_factory=list)
    network: NetworkModel = field(default_factory=NetworkModel)
    egrid_lookup: EGridLookup | None = None
    scenario_engine: ScenarioEngine | None = None
    context: SimulationContext | None = None
    mas: MultiAgentSystem | None = None
    state: SystemState = field(default_factory=SystemState)

    def init_system(self) -> None:
        """Initialize nodes, queue, scenarios, MAS, and initial system state."""
        seed = set_global_seed(self.config.simulation.seed)
        self.nodes = {
            node.id: Node(
                id=node.id,
                cpu=node.cpu,
                memory=node.memory,
                gpu=node.gpu,
                used_cpu=node.used_cpu,
                used_memory=node.used_memory,
                egrid_subregion=node.egrid_subregion,
                egrid_ba_code=node.egrid_ba_code,
            )
            for node in self.config.nodes
        }
        self.network = NetworkModel.from_edges(self.config.network_edges)
        self.future_tasks = deque(
            sorted(
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
        )
        self.queue = TaskQueue()
        self.running_tasks = {node_id: [] for node_id in self.nodes}
        self.completed_tasks = []
        self.completed_task_records = []
        self.completed_latency_sum = 0.0
        self.completed_latency_count = 0
        self.deadline_violations_count = 0
        self.energy_consumed_mwh_total = 0.0
        self.co2_total_lb_accum = 0.0
        self.co2e_total_lb_accum = 0.0
        self.scenario_events = []
        self.egrid_lookup = (
            load_lookup(self.config.energy.egrid_dataset_path)
            if self.config.energy.enabled
            else None
        )
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
            node_co2_lb_per_mwh={
                node_id: self._resolve_node_factors(node_id).co2_lb_per_mwh
                for node_id in self.nodes
            },
            node_co2e_lb_per_mwh={
                node_id: self._resolve_node_factors(node_id).co2e_lb_per_mwh
                for node_id in self.nodes
            },
            node_renewable_share={
                node_id: self._resolve_node_factors(node_id).renewable_share
                for node_id in self.nodes
            },
        )
        if not self.agents:
            agents: list[Agent] = [MonitoringAgent()]
            if self.config.intelligence.enabled:
                agents.append(
                    PredictionAgent(
                        prediction_window=self.config.intelligence.prediction_window,
                        znn_gain=self.config.intelligence.znn_gain,
                        high_queue_threshold=self.config.intelligence.high_queue_threshold,
                        high_load_threshold=self.config.intelligence.high_load_threshold,
                        adaptive_algorithm=self.config.intelligence.adaptive_algorithm,
                        congestion_algorithm=self.config.intelligence.congestion_algorithm,
                        normal_algorithm=self.config.intelligence.normal_algorithm,
                    )
                )
            if self.config.llm.enabled:
                agents.append(
                    LLMAgent(
                        provider=self.config.llm.provider,
                        model=self.config.llm.model,
                        temperature=self.config.llm.temperature,
                        max_tokens=self.config.llm.max_tokens,
                        timeout_seconds=self.config.llm.timeout_seconds,
                        api_base_url=self.config.llm.api_base_url,
                        api_key_env=self.config.llm.api_key_env,
                        allowed_algorithms=self.config.llm.allowed_algorithms,
                        allow_algorithm_override=self.config.llm.allow_algorithm_override,
                        allow_node_bias_override=self.config.llm.allow_node_bias_override,
                    )
                )
            agents.extend(
                [
                    NetworkAgent(),
                    QoSAgent(),
                    OptimizationAgent(
                        algorithm=self.config.optimization.algorithm,
                        adaptive_algorithm=self.config.intelligence.adaptive_algorithm,
                    ),
                    ComputeAgent(
                        carbon_weight=self.config.energy.carbon_weight,
                        load_weight=self.config.energy.load_weight,
                        bandwidth_weight=self.config.energy.bandwidth_weight,
                    ),
                ]
            )
            self.agents = agents
        self.mas = MultiAgentSystem(agents=self.agents, context=self.context)
        self._sync_state(0)
        LOGGER.info(
            "Simulation initialized: scenario=%s algorithm=%s intelligence=%s llm=%s seed=%d nodes=%d tasks=%d horizon=%d",
            self.config.scenario,
            self.config.optimization.algorithm,
            self.config.intelligence.enabled,
            self.config.llm.enabled,
            seed,
            len(self.nodes),
            len(self.future_tasks),
            self.config.simulation.time_horizon,
        )

    def generate_tasks(self, t: int) -> None:
        """Release preloaded tasks and generate scenario tasks for tick t."""
        released: list[Task] = []
        while self.future_tasks and self.future_tasks[0].arrival_time <= t:
            task = self.future_tasks.popleft()
            task.status = "queued"
            released.append(task)
        generated: list[Task] = []
        if self.scenario_engine is not None:
            generated = self.scenario_engine.generate_tasks(t)
            for task in generated:
                task.status = "queued"
        self.queue.extend(released + generated)

    def update_state(self, t: int) -> None:
        """Advance running tasks by one tick and refresh aggregate state."""
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
                self._register_completed_task(task)
                node.release(task)
            self.running_tasks[node_id] = still_running
        self._sync_state(t + 1)

    def run(self) -> SystemState:
        """Execute the configured simulation horizon and return final state."""
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
                    self.scenario_events.append(
                        {
                            "time": event.time,
                            "kind": event.kind,
                            **event.details,
                        }
                    )
            self.generate_tasks(t)
            self.mas.step(self.state)
            self.update_state(t)
        LOGGER.info(
            "Simulation finished: completed=%d pending=%d latency=%.3f throughput=%.3f avg_load=%.3f energy_mwh=%.6f co2_lb=%.3f predicted_queue=%.3f predicted_load=%.3f llm_source=%s llm_hint=%s",
            self.state.completed_tasks,
            self.state.pending_tasks,
            self.state.avg_latency,
            self.state.throughput,
            self.state.avg_load,
            self.state.energy_consumed_mwh,
            self.state.co2_total_lb,
            self.state.predicted_queue,
            self.state.predicted_avg_load,
            self.state.llm_source,
            self.state.llm_algorithm_hint,
        )
        return self.state

    def _sync_state(self, current_time: int) -> None:
        """Recompute SystemState snapshot and append history point."""
        if self.context is not None:
            self.context.current_time = current_time
        self.state.current_time = current_time
        self.state.scenario = self.config.scenario
        self.state.intelligence_enabled = self.config.intelligence.enabled
        self.state.llm_enabled = self.config.llm.enabled
        if self.context is not None:
            self.state.selected_algorithm = self.context.active_algorithm
            self.state.predicted_queue = self.context.predicted_queue
            self.state.predicted_avg_load = self.context.predicted_avg_load
            self.state.llm_source = self.context.llm_source
            self.state.llm_confidence = self.context.llm_confidence
            self.state.llm_algorithm_hint = self.context.llm_algorithm_hint
            self.state.llm_actions_applied = self.context.llm_actions_applied
            self.state.llm_last_reason = self.context.llm_reason
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
        self.state.deadline_violations = self.deadline_violations_count
        self.state.generated_tasks = (
            self.scenario_engine.generated_tasks_total
            if self.scenario_engine is not None
            else 0
        )
        self.state.avg_latency = (
            self.completed_latency_sum / float(self.completed_latency_count)
            if self.completed_latency_count > 0
            else 0.0
        )
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
        self.state.energy_consumed_mwh = self.energy_consumed_mwh_total
        self.state.co2_total_lb = self.co2_total_lb_accum
        self.state.co2e_total_lb = self.co2e_total_lb_accum
        if self.state.completed_tasks > 0:
            self.state.co2_per_completed_task_lb = (
                self.state.co2_total_lb / float(self.state.completed_tasks)
            )
            self.state.co2e_per_completed_task_lb = (
                self.state.co2e_total_lb / float(self.state.completed_tasks)
            )
        else:
            self.state.co2_per_completed_task_lb = 0.0
            self.state.co2e_per_completed_task_lb = 0.0
        self.state.mas_messages = len(self.mas.message_log) if self.mas is not None else 0
        if self.context is not None:
            self.state.mas_assignments = len(self.context.assignment_log)
        else:
            self.state.mas_assignments = 0
        self.state.completed_task_records = list(self.completed_task_records)
        self.state.scenario_events = list(self.scenario_events)
        self.state.history.append(
            {
                "time": self.state.current_time,
                "scenario": self.state.scenario,
                "algorithm": self.state.selected_algorithm,
                "intelligence_enabled": self.state.intelligence_enabled,
                "llm_enabled": self.state.llm_enabled,
                "llm_source": self.state.llm_source,
                "llm_confidence": self.state.llm_confidence,
                "llm_algorithm_hint": self.state.llm_algorithm_hint,
                "llm_actions_applied": self.state.llm_actions_applied,
                "predicted_queue": self.state.predicted_queue,
                "predicted_avg_load": self.state.predicted_avg_load,
                "node_loads": dict(self.state.node_loads),
                "queue_size": self.state.queue_lengths["global"],
                "pending_tasks": self.state.pending_tasks,
                "completed_tasks": self.state.completed_tasks,
                "inactive_nodes": len(self.state.inactive_nodes),
                "generated_tasks": self.state.generated_tasks,
                "avg_latency": self.state.avg_latency,
                "throughput": self.state.throughput,
                "avg_load": self.state.avg_load,
                "energy_consumed_mwh": self.state.energy_consumed_mwh,
                "co2_total_lb": self.state.co2_total_lb,
                "co2e_total_lb": self.state.co2e_total_lb,
                "co2_per_completed_task_lb": self.state.co2_per_completed_task_lb,
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

    def _register_completed_task(self, task: Task) -> None:
        """Update incremental counters and completion record for finished task."""
        if task.finish_time is not None:
            latency = float(task.finish_time - task.arrival_time)
            self.completed_latency_sum += latency
            self.completed_latency_count += 1
            if task.finish_time > task.deadline:
                self.deadline_violations_count += 1
        else:
            latency = None
        energy_mwh = self._estimate_task_energy_mwh(task)
        factors = self._resolve_node_factors(task.assigned_node)
        co2_lb = energy_mwh * factors.co2_lb_per_mwh
        co2e_lb = energy_mwh * factors.co2e_lb_per_mwh
        self.energy_consumed_mwh_total += energy_mwh
        self.co2_total_lb_accum += co2_lb
        self.co2e_total_lb_accum += co2e_lb
        self.completed_task_records.append(
            {
                "task_id": task.id,
                "arrival_time": task.arrival_time,
                "start_time": task.start_time,
                "finish_time": task.finish_time,
                "deadline": task.deadline,
                "latency": latency,
                "duration": task.duration,
                "assigned_node": task.assigned_node,
                "energy_mwh": energy_mwh,
                "co2_lb": co2_lb,
                "co2e_lb": co2e_lb,
                "egrid_source": factors.source,
                "algorithm": self.context.active_algorithm if self.context is not None else "",
                "scenario": self.config.scenario,
            }
        )

    def _estimate_task_energy_mwh(self, task: Task) -> float:
        """Estimate consumed electrical energy for one completed task."""
        node = self.nodes.get(task.assigned_node or "")
        if node is None:
            return 0.0
        step_seconds = float(self.config.simulation.step_seconds)
        hours = max(0.0, float(task.duration) * step_seconds / 3600.0)
        if hours <= 0.0:
            return 0.0
        cpu_ratio = (
            max(0.0, min(1.0, float(task.cpu_required) / float(node.cpu)))
            if node.cpu > 0.0
            else 0.0
        )
        idle_kw = float(self.config.energy.node_power_idle_kw)
        max_kw = max(idle_kw, float(self.config.energy.node_power_max_kw))
        power_kw = idle_kw + (max_kw - idle_kw) * cpu_ratio
        return (power_kw * hours) / 1000.0

    def _resolve_node_factors(self, node_id: str | None):
        """Resolve node factors from eGRID lookup with deterministic fallback."""
        fallback = default_factors(self.config.energy)
        if node_id is None:
            return fallback
        node = self.nodes.get(node_id)
        if node is None:
            return fallback
        if self.egrid_lookup is None:
            return fallback
        return self.egrid_lookup.resolve(
            node=node,
            level=self.config.energy.egrid_level,
            fallback=fallback,
        )
