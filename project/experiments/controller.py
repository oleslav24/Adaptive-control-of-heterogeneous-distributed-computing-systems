from __future__ import annotations

from dataclasses import dataclass

from project.core.config import ExperimentConfig
from project.core.models import SystemState
from project.simulation.loop import SimulationLoop


@dataclass
class Experiment:
    config: ExperimentConfig

    def run(self) -> SystemState:
        loop = SimulationLoop(config=self.config)
        return loop.run()
