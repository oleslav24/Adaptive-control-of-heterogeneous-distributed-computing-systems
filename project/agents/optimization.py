"""Optimization agent that selects the active scheduling algorithm."""

from __future__ import annotations

from project.algorithms import normalize_algorithm
from project.core.agent import Agent, AgentMessage


class OptimizationAgent(Agent):
    """Translate adaptive hints into a concrete scheduler policy."""

    def __init__(
        self,
        algorithm: str = "min-load",
        adaptive_algorithm: bool = True,
        name: str = "optimization",
    ) -> None:
        super().__init__(name=name)
        self.base_algorithm = normalize_algorithm(algorithm)
        self.adaptive_algorithm = adaptive_algorithm

    def decide(self) -> None:
        """Resolve final algorithm and send policy update to compute agent."""
        if self.context is None:
            return
        previous = self.context.active_algorithm
        selected = self.base_algorithm
        messages = self.read_messages()
        prediction_hint: str | None = None
        llm_hint: str | None = None
        if self.adaptive_algorithm:
            for message in messages:
                if message.topic != "prediction_algorithm_hint":
                    continue
                hint = message.payload.get("algorithm", selected)
                prediction_hint = normalize_algorithm(str(hint))
                selected = prediction_hint
        for message in messages:
            if message.topic != "llm_algorithm_hint":
                continue
            hint = message.payload.get("algorithm", selected)
            llm_hint = normalize_algorithm(str(hint))
            selected = llm_hint
        self.context.active_algorithm = selected
        self.context.record_decision(
            self.name,
            "algorithm_policy",
            base_algorithm=self.base_algorithm,
            previous_algorithm=previous,
            selected_algorithm=selected,
            prediction_hint=prediction_hint,
            llm_hint=llm_hint,
            switched=selected != previous,
        )
        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="optimization_policy",
                payload={"algorithm": selected},
            )
        )

    def act(self) -> None:
        """No direct actuation beyond policy dispatch in decide phase."""
        return
