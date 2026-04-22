from __future__ import annotations

from dataclasses import dataclass, field

from project.core.agent import Agent
from project.core.config import ExperimentConfig
from project.core.models import SystemState
from project.simulation.loop import SimulationLoop


@dataclass
class Experiment:
    config: ExperimentConfig
    agents: list[Agent] = field(default_factory=list)

    def run(self) -> SystemState:
        loop = SimulationLoop(config=self.config, agents=self.agents)
        return loop.run()

