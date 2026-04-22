from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import NetworkEdge, Node, Task


@dataclass(slots=True)
class SimulationConfig:
    time_horizon: int = 10
    seed: int = 42
    step_seconds: float = 1.0


@dataclass(slots=True)
class ExperimentConfig:
    name: str = "sprint0-smoke"
    scenario: str = "static"
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    nodes: list[Node] = field(default_factory=list)
    network_edges: list[NetworkEdge] = field(default_factory=list)
    initial_tasks: list[Task] = field(default_factory=list)


def load_config(path: str | Path) -> ExperimentConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    simulation_raw = raw.get("simulation", {})
    simulation = SimulationConfig(
        time_horizon=int(simulation_raw.get("time_horizon", 10)),
        seed=int(simulation_raw.get("seed", 42)),
        step_seconds=float(simulation_raw.get("step_seconds", 1.0)),
    )

    nodes = [
        Node(
            id=item["id"],
            cpu=float(item["cpu"]),
            memory=float(item["memory"]),
            gpu=float(item.get("gpu", 0.0)),
            load=float(item.get("load", 0.0)),
        )
        for item in raw.get("nodes", [])
    ]
    edges = [
        NetworkEdge(
            source=item["source"],
            target=item["target"],
            bandwidth=float(item["bandwidth"]),
            latency=float(item["latency"]),
        )
        for item in raw.get("network_edges", [])
    ]
    tasks = [
        Task(
            id=item["id"],
            cpu_required=float(item["cpu_required"]),
            memory_required=float(item["memory_required"]),
            data_size=float(item["data_size"]),
            deadline=float(item["deadline"]),
        )
        for item in raw.get("initial_tasks", [])
    ]

    return ExperimentConfig(
        name=str(raw.get("name", "sprint0-smoke")),
        scenario=str(raw.get("scenario", "static")),
        simulation=simulation,
        nodes=nodes,
        network_edges=edges,
        initial_tasks=tasks,
    )

