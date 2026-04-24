"""Single-experiment controller abstraction."""

from __future__ import annotations

from dataclasses import dataclass

from project.core.agent import Agent
from project.core.config import ExperimentConfig
from project.core.models import SystemState
from project.simulation.loop import SimulationLoop


@dataclass
class Experiment:
    """Thin wrapper that executes one configured simulation run."""

    config: ExperimentConfig
    agents: list[Agent] | None = None

    def run(self) -> SystemState:
        """Run simulation loop and return final state."""
        loop = SimulationLoop(config=self.config, agents=list(self.agents or []))
        return loop.run()
