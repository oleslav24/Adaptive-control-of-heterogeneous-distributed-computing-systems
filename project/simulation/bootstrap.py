"""Helpers for building an initialized simulation system from parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from project.core.models import NetworkEdge, Node, SystemState
from project.simulation.network import NetworkModel

TopologySpec = str | list[tuple[object, object]] | list[dict[str, object]]


@dataclass(slots=True)
class InitializedSystem:
    """Container for initialized nodes, edges, network model, and initial state."""

    nodes: dict[str, Node]
    edges: list[NetworkEdge]
    network: NetworkModel
    state: SystemState


def init_system(
    N: int,
    topology: TopologySpec,
    *,
    cpu: float = 16.0,
    memory: float = 64.0,
    gpu: float = 0.0,
    bandwidth: float = 1000.0,
    latency: float = 4.0,
) -> InitializedSystem:
    """Create nodes/topology and return an initialized simulation bundle."""
    node_count = int(N)
    if node_count < 1:
        raise ValueError("N must be >= 1")

    node_ids = [f"node-{idx + 1}" for idx in range(node_count)]
    nodes = {
        node_id: Node(
            id=node_id,
            cpu=float(cpu),
            memory=float(memory),
            gpu=float(gpu),
        )
        for node_id in node_ids
    }

    edges = _build_edges(
        node_ids=node_ids,
        topology=topology,
        default_bandwidth=float(bandwidth),
        default_latency=float(latency),
    )
    network = NetworkModel.from_edges(edges)
    state = SystemState(
        node_loads={node_id: node.load for node_id, node in nodes.items()},
        queue_lengths={"global": 0},
        network_state=network.snapshot(),
    )
    return InitializedSystem(
        nodes=nodes,
        edges=edges,
        network=network,
        state=state,
    )


def _build_edges(
    *,
    node_ids: list[str],
    topology: TopologySpec,
    default_bandwidth: float,
    default_latency: float,
) -> list[NetworkEdge]:
    """Build edges from named topology or explicit edge list."""
    if isinstance(topology, str):
        return _named_topology_edges(
            node_ids=node_ids,
            name=topology,
            default_bandwidth=default_bandwidth,
            default_latency=default_latency,
        )

    if not isinstance(topology, list):
        raise TypeError("topology must be a topology name or a list of edges")

    edges: list[NetworkEdge] = []
    for item in topology:
        if isinstance(item, tuple) and len(item) == 2:
            source = _resolve_node_ref(node_ids, item[0])
            target = _resolve_node_ref(node_ids, item[1])
            edges.append(
                NetworkEdge(
                    source=source,
                    target=target,
                    bandwidth=default_bandwidth,
                    latency=default_latency,
                )
            )
            continue

        if isinstance(item, dict):
            source = _resolve_node_ref(node_ids, item.get("source"))
            target = _resolve_node_ref(node_ids, item.get("target"))
            edges.append(
                NetworkEdge(
                    source=source,
                    target=target,
                    bandwidth=_coerce_float(item.get("bandwidth"), default_bandwidth),
                    latency=_coerce_float(item.get("latency"), default_latency),
                )
            )
            continue

        raise TypeError(
            "Unsupported edge format in topology list; expected tuple(source, target) or dict."
        )
    return edges


def _named_topology_edges(
    *,
    node_ids: list[str],
    name: str,
    default_bandwidth: float,
    default_latency: float,
) -> list[NetworkEdge]:
    """Generate predefined topology edges."""
    normalized = str(name).strip().lower().replace("_", "-")
    if normalized in {"full", "mesh", "fully-connected"}:
        return _pairs_to_edges(
            ((src, dst) for src in node_ids for dst in node_ids if src != dst),
            default_bandwidth=default_bandwidth,
            default_latency=default_latency,
        )

    if normalized in {"ring", "cycle"}:
        if len(node_ids) == 1:
            return []
        pairs: list[tuple[str, str]] = []
        count = len(node_ids)
        for idx, src in enumerate(node_ids):
            dst = node_ids[(idx + 1) % count]
            pairs.append((src, dst))
            pairs.append((dst, src))
        return _pairs_to_edges(
            pairs,
            default_bandwidth=default_bandwidth,
            default_latency=default_latency,
        )

    if normalized in {"line", "chain"}:
        line_pairs: list[tuple[str, str]] = []
        for idx in range(len(node_ids) - 1):
            src = node_ids[idx]
            dst = node_ids[idx + 1]
            line_pairs.append((src, dst))
            line_pairs.append((dst, src))
        return _pairs_to_edges(
            line_pairs,
            default_bandwidth=default_bandwidth,
            default_latency=default_latency,
        )

    if normalized == "star":
        if len(node_ids) == 1:
            return []
        hub = node_ids[0]
        star_pairs: list[tuple[str, str]] = []
        for dst in node_ids[1:]:
            star_pairs.append((hub, dst))
            star_pairs.append((dst, hub))
        return _pairs_to_edges(
            star_pairs,
            default_bandwidth=default_bandwidth,
            default_latency=default_latency,
        )

    raise ValueError(
        "Unsupported topology name. Use one of: full, mesh, fully-connected, ring, line, star."
    )


def _pairs_to_edges(
    pairs: Iterable[tuple[str, str]],
    *,
    default_bandwidth: float,
    default_latency: float,
) -> list[NetworkEdge]:
    """Convert source/target pairs to typed edge objects."""
    return [
        NetworkEdge(
            source=source,
            target=target,
            bandwidth=default_bandwidth,
            latency=default_latency,
        )
        for source, target in pairs
    ]


def _resolve_node_ref(node_ids: list[str], ref: object) -> str:
    """Resolve string or index reference into canonical node id."""
    if isinstance(ref, str):
        value = ref.strip()
        if value in node_ids:
            return value
        raise ValueError(f"Unknown node id '{value}'.")

    if isinstance(ref, int):
        if ref in range(len(node_ids)):
            return node_ids[ref]
        one_based = ref - 1
        if one_based in range(len(node_ids)):
            return node_ids[one_based]
        raise ValueError(f"Node index '{ref}' is out of range.")

    raise TypeError("Node reference must be a node id string or integer index.")


def _coerce_float(value: object, default: float) -> float:
    """Convert optional edge attribute to float with deterministic fallback."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
