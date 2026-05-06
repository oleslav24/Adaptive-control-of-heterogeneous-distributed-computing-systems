"""Unit tests for core simulation domain models."""

from __future__ import annotations

from project.core.models import Node, Task


def test_task_duration_is_normalized_to_positive_value() -> None:
    """Task duration below 1 should be clamped to 1 and copied to remaining time."""
    task = Task(
        id="task-1",
        cpu_required=1.0,
        memory_required=1.0,
        data_size=1.0,
        deadline=5.0,
        duration=0,
    )
    assert task.duration == 1
    assert task.remaining_time == 1


def test_node_assign_release_and_can_run_follow_capacity_constraints() -> None:
    """Node should reserve/release resources and reject oversized task assignment."""
    node = Node(id="node-1", cpu=8.0, memory=16.0, gpu=0.0)
    small = Task(
        id="small",
        cpu_required=2.0,
        memory_required=4.0,
        data_size=1.0,
        deadline=10.0,
    )
    big = Task(
        id="big",
        cpu_required=7.0,
        memory_required=13.0,
        data_size=1.0,
        deadline=10.0,
    )

    assert node.can_run(small) is True
    node.assign(small)
    assert node.used_cpu == 2.0
    assert node.used_memory == 4.0
    assert node.load == 0.25
    assert node.can_run(big) is False

    node.release(small)
    assert node.used_cpu == 0.0
    assert node.used_memory == 0.0


def test_node_load_special_cases_for_inactive_and_zero_cpu() -> None:
    """Inactive node should report full load, zero-cpu active node should report 0."""
    inactive = Node(id="node-inactive", cpu=8.0, memory=16.0, gpu=0.0, is_active=False)
    zero_cpu = Node(id="node-zero", cpu=0.0, memory=16.0, gpu=0.0)
    assert inactive.load == 1.0
    assert zero_cpu.load == 0.0
