"""Core domain models for nodes, tasks, links, and global state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class Node:
    """Compute node with capacity, runtime usage, and failure state."""

    id: str
    cpu: float
    memory: float
    gpu: float
    used_cpu: float = 0.0
    used_memory: float = 0.0
    is_active: bool = True
    failed_since: int | None = None
    egrid_subregion: str = ""
    egrid_ba_code: str = ""

    @property
    def load(self) -> float:
        """Current CPU utilization ratio in [0, 1]."""
        if not self.is_active:
            return 1.0
        if self.cpu <= 0:
            return 0.0
        return min(1.0, self.used_cpu / self.cpu)

    def can_run(self, task: Task) -> bool:
        """Return True when node has enough free CPU and memory for task."""
        if not self.is_active:
            return False
        return (
            self.used_cpu + task.cpu_required <= self.cpu
            and self.used_memory + task.memory_required <= self.memory
        )

    def assign(self, task: Task) -> None:
        """Reserve node resources for a running task."""
        self.used_cpu += task.cpu_required
        self.used_memory += task.memory_required

    def release(self, task: Task) -> None:
        """Release node resources when task finishes or is preempted."""
        self.used_cpu = max(0.0, self.used_cpu - task.cpu_required)
        self.used_memory = max(0.0, self.used_memory - task.memory_required)


@dataclass(slots=True)
class Task:
    """Work unit with resource requirements and timing constraints."""

    id: str
    cpu_required: float
    memory_required: float
    data_size: float
    deadline: float
    arrival_time: int = 0
    duration: int = 1
    remaining_time: int = 1
    status: Literal["pending", "queued", "running", "completed"] = "pending"
    assigned_node: str | None = None
    start_time: int | None = None
    finish_time: int | None = None

    def __post_init__(self) -> None:
        """Normalize duration and initialize remaining execution time."""
        if self.duration < 1:
            self.duration = 1
        self.remaining_time = self.duration


@dataclass(slots=True)
class NetworkEdge:
    """Directed network link between two nodes."""

    source: str
    target: str
    bandwidth: float
    latency: float


@dataclass(slots=True)
class SystemState:
    """Full observable simulation state and aggregated metrics."""

    current_time: int = 0
    scenario: str = "static"
    selected_algorithm: str = "min-load"
    intelligence_enabled: bool = False
    llm_enabled: bool = False
    llm_source: str = "none"
    llm_confidence: float = 0.0
    llm_algorithm_hint: str | None = None
    llm_actions_applied: int = 0
    llm_last_reason: str = ""
    predicted_queue: float = 0.0
    predicted_avg_load: float = 0.0
    node_loads: dict[str, float] = field(default_factory=dict)
    queue_lengths: dict[str, int] = field(default_factory=dict)
    network_state: dict[tuple[str, str], dict[str, float]] = field(default_factory=dict)
    running_tasks: dict[str, list[str]] = field(default_factory=dict)
    inactive_nodes: list[str] = field(default_factory=list)
    pending_tasks: int = 0
    completed_tasks: int = 0
    generated_tasks: int = 0
    deadline_violations: int = 0
    avg_latency: float = 0.0
    throughput: float = 0.0
    avg_load: float = 0.0
    energy_consumed_mwh: float = 0.0
    co2_total_lb: float = 0.0
    co2e_total_lb: float = 0.0
    co2_per_completed_task_lb: float = 0.0
    co2e_per_completed_task_lb: float = 0.0
    mas_messages: int = 0
    mas_assignments: int = 0
    completed_task_records: list[dict[str, object]] = field(default_factory=list)
    scenario_events: list[dict[str, object]] = field(default_factory=list)
    decision_trace: list[dict[str, object]] = field(default_factory=list)
    history: list[dict[str, object]] = field(default_factory=list)
