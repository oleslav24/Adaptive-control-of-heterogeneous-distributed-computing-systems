from __future__ import annotations

from project.core.agent import Agent, AgentMessage


class NetworkAgent(Agent):
    def __init__(self, name: str = "network", min_bandwidth: float = 50.0) -> None:
        super().__init__(name=name)
        self.min_bandwidth = min_bandwidth

    def decide(self) -> None:
        if self.context is None:
            return
        node_bandwidth = self.context.network.node_bandwidth_map(list(self.context.nodes.keys()))
        blocked_nodes = [
            node_id
            for node_id, bandwidth in node_bandwidth.items()
            if bandwidth < self.min_bandwidth
        ]
        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="bandwidth_policy",
                payload={
                    "node_bandwidth": node_bandwidth,
                    "blocked_nodes": blocked_nodes,
                },
            )
        )

    def act(self) -> None:
        return

