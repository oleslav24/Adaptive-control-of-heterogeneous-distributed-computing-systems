"""Scheduling heuristics used by the compute agent."""

from __future__ import annotations

from project.core.models import Node, Task

SUPPORTED_ALGORITHMS = ("round-robin", "min-load", "greedy")


def normalize_algorithm(name: str) -> str:
    """Normalize external algorithm name to a supported identifier."""
    normalized = str(name).strip().lower().replace("_", "-")
    if normalized in SUPPORTED_ALGORITHMS:
        return normalized
    return "min-load"


def choose_node(
    algorithm: str,
    task: Task,
    candidates: list[Node],
    all_node_ids: list[str],
    node_bandwidth: dict[str, float],
    rr_cursor: int,
) -> tuple[Node | None, int]:
    """Select a node with the requested strategy and return next RR cursor."""
    algorithm = normalize_algorithm(algorithm)
    if not candidates:
        return None, rr_cursor
    if algorithm == "round-robin":
        return _round_robin(candidates, all_node_ids, rr_cursor)
    if algorithm == "greedy":
        return _greedy(task, candidates, node_bandwidth), rr_cursor
    return _min_load(candidates, node_bandwidth), rr_cursor


def _round_robin(
    candidates: list[Node],
    all_node_ids: list[str],
    rr_cursor: int,
) -> tuple[Node | None, int]:
    """Pick next available candidate in global node-id order."""
    if not all_node_ids:
        return None, rr_cursor
    ordered_ids = sorted(all_node_ids)
    candidate_map = {node.id: node for node in candidates}
    count = len(ordered_ids)
    for offset in range(count):
        idx = (rr_cursor + offset) % count
        node_id = ordered_ids[idx]
        node = candidate_map.get(node_id)
        if node is not None:
            return node, (idx + 1) % count
    return None, rr_cursor


def _min_load(candidates: list[Node], node_bandwidth: dict[str, float]) -> Node:
    """Prefer less-loaded nodes and higher available bandwidth."""
    return min(
        candidates,
        key=lambda node: (
            node.load,
            -node_bandwidth.get(node.id, float("inf")),
            -node.cpu,
        ),
    )


def _greedy(task: Task, candidates: list[Node], node_bandwidth: dict[str, float]) -> Node:
    """Prefer nodes with the largest residual resources after assignment."""
    return min(
        candidates,
        key=lambda node: (
            (node.cpu - (node.used_cpu + task.cpu_required))
            + 0.1 * (node.memory - (node.used_memory + task.memory_required)),
            node.load,
            -node_bandwidth.get(node.id, float("inf")),
        ),
    )
