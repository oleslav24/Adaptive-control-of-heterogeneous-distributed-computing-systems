"""Unit tests for scheduling heuristics."""

from __future__ import annotations

from project.algorithms.schedulers import choose_node, normalize_algorithm
from project.core.models import Node, Task


def _task() -> Task:
    return Task(
        id="task-1",
        cpu_required=2.0,
        memory_required=2.0,
        data_size=64.0,
        deadline=10.0,
    )


def test_normalize_algorithm_unknown_falls_back_to_min_load() -> None:
    """Unsupported external names should map to min-load."""
    assert normalize_algorithm("UNKNOWN") == "min-load"
    assert normalize_algorithm("round_robin") == "round-robin"
    assert normalize_algorithm("carbon_aware") == "carbon-aware"


def test_round_robin_uses_global_node_order_and_updates_cursor() -> None:
    """Round-robin should follow sorted all-node ids and move cursor forward."""
    candidates = [
        Node(id="node-b", cpu=8.0, memory=8.0, gpu=0.0),
        Node(id="node-c", cpu=8.0, memory=8.0, gpu=0.0),
    ]
    selected, cursor = choose_node(
        algorithm="round-robin",
        task=_task(),
        candidates=candidates,
        all_node_ids=["node-c", "node-a", "node-b"],
        node_bandwidth={},
        rr_cursor=1,
    )
    assert selected is not None
    assert selected.id == "node-b"
    assert cursor == 2


def test_min_load_prefers_higher_bandwidth_when_load_is_equal() -> None:
    """For equal load, min-load should prefer node with higher average bandwidth."""
    n1 = Node(id="node-1", cpu=8.0, memory=8.0, gpu=0.0, used_cpu=2.0)
    n2 = Node(id="node-2", cpu=8.0, memory=8.0, gpu=0.0, used_cpu=2.0)
    selected, cursor = choose_node(
        algorithm="min-load",
        task=_task(),
        candidates=[n1, n2],
        all_node_ids=[n1.id, n2.id],
        node_bandwidth={n1.id: 300.0, n2.id: 1200.0},
        rr_cursor=0,
    )
    assert selected is not None
    assert selected.id == n2.id
    assert cursor == 0


def test_greedy_selection_is_deterministic_with_residual_resource_score() -> None:
    """Greedy strategy should deterministically pick node with smaller greedy key."""
    strong = Node(id="strong", cpu=16.0, memory=32.0, gpu=0.0, used_cpu=1.0, used_memory=1.0)
    weak = Node(id="weak", cpu=8.0, memory=12.0, gpu=0.0, used_cpu=1.0, used_memory=1.0)
    selected, cursor = choose_node(
        algorithm="greedy",
        task=_task(),
        candidates=[strong, weak],
        all_node_ids=[strong.id, weak.id],
        node_bandwidth={strong.id: 1000.0, weak.id: 1000.0},
        rr_cursor=5,
    )
    assert selected is not None
    assert selected.id == "weak"
    assert cursor == 5


def test_carbon_aware_prefers_lower_co2_factor() -> None:
    """Carbon-aware strategy should prefer node with lower mapped CO2 factor."""
    dirty = Node(id="dirty", cpu=16.0, memory=32.0, gpu=0.0, used_cpu=1.0, used_memory=1.0)
    green = Node(id="green", cpu=16.0, memory=32.0, gpu=0.0, used_cpu=2.0, used_memory=1.0)
    selected, cursor = choose_node(
        algorithm="carbon-aware",
        task=_task(),
        candidates=[dirty, green],
        all_node_ids=[dirty.id, green.id],
        node_bandwidth={dirty.id: 1000.0, green.id: 800.0},
        rr_cursor=2,
        node_carbon={dirty.id: 1200.0, green.id: 450.0},
    )
    assert selected is not None
    assert selected.id == "green"
    assert cursor == 2
