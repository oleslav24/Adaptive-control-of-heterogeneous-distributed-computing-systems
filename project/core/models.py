from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Node:
    id: str
    cpu: float
    memory: float
    gpu: float
    load: float = 0.0


@dataclass(slots=True)
class Task:
    id: str
    cpu_required: float
    memory_required: float
    data_size: float
    deadline: float


@dataclass(slots=True)
class NetworkEdge:
    source: str
    target: str
    bandwidth: float
    latency: float


@dataclass(slots=True)
class SystemState:
    node_loads: dict[str, float] = field(default_factory=dict)
    queue_lengths: dict[str, int] = field(default_factory=dict)
    network_state: dict[tuple[str, str], dict[str, float]] = field(default_factory=dict)

