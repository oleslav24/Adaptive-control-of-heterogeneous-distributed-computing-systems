"""Scenario/task generation helpers for publication experiments."""

from __future__ import annotations

import numpy as np

from project.core.config import (
    DynamicLoadConfig,
    HeterogeneousTasksConfig,
    NodeFailureEventConfig,
    NodeFailuresConfig,
    PeakLoadConfig,
    ScenarioConfig,
)
from project.core.models import Task


def suggest_horizon(node_count: int, task_count: int) -> int:
    """Estimate simulation horizon based on system scale."""
    estimate = int((task_count / max(1, node_count)) * 4) + 30
    return min(360, max(40, estimate))


def generate_tasks(
    *,
    task_count: int,
    task_type: str,
    seed: int,
    horizon: int,
) -> list[Task]:
    """Generate synthetic workload with light/heavy/mixed task profiles."""
    rng = np.random.default_rng(int(seed))
    task_type = str(task_type).strip().lower()
    tasks: list[Task] = []

    for idx in range(task_count):
        if task_type == "light":
            cpu = float(rng.uniform(0.5, 2.5))
            mem = float(rng.uniform(1.0, 4.0))
            duration = int(rng.integers(1, 3))
            data_size = float(rng.uniform(32.0, 192.0))
            slack = int(rng.integers(2, 6))
        elif task_type == "heavy":
            cpu = float(rng.uniform(5.0, 12.0))
            mem = float(rng.uniform(8.0, 24.0))
            duration = int(rng.integers(3, 8))
            data_size = float(rng.uniform(256.0, 1536.0))
            slack = int(rng.integers(4, 10))
        else:
            heavy = bool(rng.random() < 0.35)
            if heavy:
                cpu = float(rng.uniform(4.0, 10.0))
                mem = float(rng.uniform(7.0, 20.0))
                duration = int(rng.integers(3, 7))
                data_size = float(rng.uniform(192.0, 1024.0))
                slack = int(rng.integers(3, 9))
            else:
                cpu = float(rng.uniform(0.8, 3.0))
                mem = float(rng.uniform(1.5, 6.0))
                duration = int(rng.integers(1, 4))
                data_size = float(rng.uniform(48.0, 320.0))
                slack = int(rng.integers(2, 7))

        arrival = int(rng.integers(0, max(1, horizon // 3)))
        deadline = float(arrival + duration + slack)
        tasks.append(
            Task(
                id=f"task-{idx + 1}",
                cpu_required=cpu,
                memory_required=mem,
                data_size=data_size,
                deadline=deadline,
                arrival_time=arrival,
                duration=duration,
            )
        )
    return tasks


def build_scenario_config(
    *,
    scenario: str,
    node_count: int,
    task_count: int,
    horizon: int,
    failure_node_id: str,
) -> ScenarioConfig:
    """Build scenario config object for the requested study scenario."""
    load_rate = max(0.5, task_count / max(1.0, float(horizon)))
    dynamic = DynamicLoadConfig(
        enabled=scenario in {"dynamic-load", "peak-load", "node-failures", "heterogeneous-tasks"},
        base_rate=load_rate,
        amplitude=0.45,
        period=max(6, horizon // 8),
        max_new_tasks=max(4, int(node_count * 0.25)),
    )
    peak = PeakLoadConfig(
        enabled=scenario == "peak-load",
        start=max(2, horizon // 3),
        end=max(3, (2 * horizon) // 3),
        multiplier=2.8,
    )
    failures = NodeFailuresConfig(
        enabled=scenario == "node-failures",
        events=(
            [
                NodeFailureEventConfig(
                    node_id=failure_node_id,
                    time=max(2, horizon // 2),
                    duration=max(2, horizon // 10),
                )
            ]
            if scenario == "node-failures"
            else []
        ),
    )
    heterogeneous = HeterogeneousTasksConfig(enabled=scenario == "heterogeneous-tasks")
    return ScenarioConfig(
        dynamic_load=dynamic,
        peak_load=peak,
        node_failures=failures,
        heterogeneous_tasks=heterogeneous,
    )

