from __future__ import annotations

from project.algorithms import normalize_algorithm
from project.core.agent import Agent, AgentMessage


class OptimizationAgent(Agent):
    def __init__(self, algorithm: str = "min-load", name: str = "optimization") -> None:
        super().__init__(name=name)
        self.algorithm = normalize_algorithm(algorithm)

    def decide(self) -> None:
        if self.context is None:
            return
        self.context.active_algorithm = self.algorithm
        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="optimization_policy",
                payload={"algorithm": self.algorithm},
            )
        )

    def act(self) -> None:
        return

