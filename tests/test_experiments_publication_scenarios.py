"""Deterministic fixture tests for publication scenario/task helpers."""

from __future__ import annotations

from project.experiments.publication_scenarios import (
    build_scenario_config,
    generate_tasks,
    suggest_horizon,
)


def test_generate_tasks_is_deterministic_for_seed_fixture() -> None:
    """Task generator should reproduce stable fixture values for fixed seed."""
    tasks = generate_tasks(task_count=3, task_type="mixed", seed=42, horizon=60)
    snapshot = [
        {
            "id": task.id,
            "cpu": round(task.cpu_required, 6),
            "memory": round(task.memory_required, 6),
            "data_size": round(task.data_size, 6),
            "deadline": round(task.deadline, 6),
            "arrival_time": task.arrival_time,
            "duration": task.duration,
        }
        for task in tasks
    ]
    assert snapshot == [
        {
            "id": "task-1",
            "cpu": 1.765533,
            "memory": 5.363691,
            "data_size": 73.616239,
            "deadline": 16.0,
            "arrival_time": 10,
            "duration": 1,
        },
        {
            "id": "task-2",
            "cpu": 2.529341,
            "memory": 2.076511,
            "data_size": 170.504975,
            "deadline": 14.0,
            "arrival_time": 7,
            "duration": 3,
        },
        {
            "id": "task-3",
            "cpu": 2.216503,
            "memory": 5.202427,
            "data_size": 109.808932,
            "deadline": 7.0,
            "arrival_time": 1,
            "duration": 2,
        },
    ]


def test_build_scenario_config_sets_expected_flags() -> None:
    """Scenario config builder should enable only scenario-specific toggles."""
    horizon = suggest_horizon(node_count=50, task_count=300)

    peak = build_scenario_config(
        scenario="peak-load",
        node_count=50,
        task_count=300,
        horizon=horizon,
        failure_node_id="node-25",
    )
    assert peak.dynamic_load.enabled is True
    assert peak.peak_load.enabled is True
    assert peak.node_failures.enabled is False
    assert peak.heterogeneous_tasks.enabled is False

    failures = build_scenario_config(
        scenario="node-failures",
        node_count=50,
        task_count=300,
        horizon=horizon,
        failure_node_id="node-25",
    )
    assert failures.node_failures.enabled is True
    assert len(failures.node_failures.events) == 1
    assert failures.node_failures.events[0].node_id == "node-25"
