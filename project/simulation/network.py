from __future__ import annotations

import networkx as nx

from project.core.models import NetworkEdge


class NetworkModel:
    """Network topology wrapper over networkx directed graph."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    @classmethod
    def from_edges(cls, edges: list[NetworkEdge]) -> NetworkModel:
        model = cls()
        for edge in edges:
            model.graph.add_edge(
                edge.source,
                edge.target,
                bandwidth=edge.bandwidth,
                latency=edge.latency,
            )
        return model

    def snapshot(self) -> dict[tuple[str, str], dict[str, float]]:
        data: dict[tuple[str, str], dict[str, float]] = {}
        for source, target, attr in self.graph.edges(data=True):
            data[(str(source), str(target))] = {
                "bandwidth": float(attr.get("bandwidth", 0.0)),
                "latency": float(attr.get("latency", 0.0)),
            }
        return data

