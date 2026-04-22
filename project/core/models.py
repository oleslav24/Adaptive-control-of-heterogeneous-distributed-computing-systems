from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class Node:
    id: str
    cpu: float
    memory: float
    gpu: float
    used_cpu: float = 0.0
    used_memory: float = 0.0

    @property
    def load(self) -> float:
        if self.cpu <= 0:
            return 0.0
        return min(1.0, self.used_cpu / self.cpu)

    def can_run(self, task: Task) -> bool:
        return (
            self.used_cpu + task.cpu_required <= self.cpu
            and self.used_memory + task.memory_required <= self.memory
        )

    def assign(self, task: Task) -> None:
        self.used_cpu += task.cpu_required
        self.used_memory += task.memory_required

    def release(self, task: Task) -> None:
        self.used_cpu = max(0.0, self.used_cpu - task.cpu_required)
        self.used_memory = max(0.0, self.used_memory - task.memory_required)


@dataclass(slots=True)
class Task:
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
        if self.duration < 1:
            self.duration = 1
        self.remaining_time = self.duration


@dataclass(slots=True)
class NetworkEdge:
    source: str
    target: str
    bandwidth: float
    latency: float


@dataclass(slots=True)
class SystemState:
    current_time: int = 0
    node_loads: dict[str, float] = field(default_factory=dict)
    queue_lengths: dict[str, int] = field(default_factory=dict)
    network_state: dict[tuple[str, str], dict[str, float]] = field(default_factory=dict)
    running_tasks: dict[str, list[str]] = field(default_factory=dict)
    pending_tasks: int = 0
    completed_tasks: int = 0
    deadline_violations: int = 0
    history: list[dict[str, object]] = field(default_factory=list)
