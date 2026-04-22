from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from project.algorithms import SUPPORTED_ALGORITHMS, normalize_algorithm
import yaml

from .models import NetworkEdge, Node, Task


@dataclass(slots=True)
class SimulationConfig:
    time_horizon: int = 10
    seed: int = 42
    step_seconds: float = 1.0


@dataclass(slots=True)
class OptimizationConfig:
    algorithm: str = "min-load"
    compare_algorithms: list[str] = field(
        default_factory=lambda: ["round-robin", "min-load", "greedy"]
    )


@dataclass(slots=True)
class ObservabilityConfig:
    output_dir: str = "outputs"
    log_level: str = "INFO"
    save_csv: bool = True
    save_plots: bool = True


@dataclass(slots=True)
class ExperimentConfig:
    name: str = "sprint0-smoke"
    scenario: str = "static"
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
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
    optimization_raw = raw.get("optimization", {})
    raw_compare = optimization_raw.get("compare_algorithms", list(SUPPORTED_ALGORITHMS))
    compare_algorithms = _normalize_algorithm_list(raw_compare)
    optimization = OptimizationConfig(
        algorithm=normalize_algorithm(str(optimization_raw.get("algorithm", "min-load"))),
        compare_algorithms=compare_algorithms or list(SUPPORTED_ALGORITHMS),
    )
    observability_raw = raw.get("observability", {})
    observability = ObservabilityConfig(
        output_dir=str(observability_raw.get("output_dir", "outputs")),
        log_level=str(observability_raw.get("log_level", "INFO")),
        save_csv=_as_bool(observability_raw.get("save_csv", True)),
        save_plots=_as_bool(observability_raw.get("save_plots", True)),
    )

    nodes = [
        _build_node(item)
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
            arrival_time=int(item.get("arrival_time", 0)),
            duration=int(item.get("duration", 1)),
        )
        for item in raw.get("initial_tasks", [])
    ]

    return ExperimentConfig(
        name=str(raw.get("name", "sprint0-smoke")),
        scenario=str(raw.get("scenario", "static")),
        simulation=simulation,
        optimization=optimization,
        observability=observability,
        nodes=nodes,
        network_edges=edges,
        initial_tasks=tasks,
    )


def _build_node(item: dict[str, object]) -> Node:
    cpu = float(item["cpu"])
    load = float(item.get("load", 0.0))
    used_cpu = max(0.0, min(cpu, cpu * load))
    return Node(
        id=str(item["id"]),
        cpu=cpu,
        memory=float(item["memory"]),
        gpu=float(item.get("gpu", 0.0)),
        used_cpu=used_cpu,
        used_memory=0.0,
    )


def _normalize_algorithm_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for item in raw:
        name = normalize_algorithm(str(item))
        if name not in normalized:
            normalized.append(name)
    return normalized


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False
