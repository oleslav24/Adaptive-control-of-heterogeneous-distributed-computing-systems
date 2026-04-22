from __future__ import annotations

from dataclasses import dataclass, field

from project.core.agent import Agent
from project.core.config import ExperimentConfig
from project.core.models import SystemState, Task


@dataclass
class SimulationLoop:
    config: ExperimentConfig
    agents: list[Agent] = field(default_factory=list)
    pending_tasks: list[Task] = field(default_factory=list)
    state: SystemState = field(default_factory=SystemState)

    def init_system(self) -> None:
        self.pending_tasks = list(self.config.initial_tasks)
        self.state.node_loads = {node.id: node.load for node in self.config.nodes}
        self.state.queue_lengths = {node.id: 0 for node in self.config.nodes}
        self.state.network_state = {
            (edge.source, edge.target): {
                "bandwidth": edge.bandwidth,
                "latency": edge.latency,
            }
            for edge in self.config.network_edges
        }

    def generate_tasks(self, t: int) -> None:
        # Sprint 0 stub: scenarios and dynamic workload generation will come later.
        _ = t

    def agents_act(self) -> None:
        for agent in self.agents:
            agent.observe(self.state)
            agent.decide()
            agent.act()

    def update_state(self) -> None:
        # Sprint 0 stub: no state dynamics yet.
        return

    def collect_metrics(self) -> None:
        # Sprint 0 stub: metrics module will be integrated in Sprint 1.
        return

    def run(self) -> SystemState:
        self.init_system()
        for t in range(self.config.simulation.time_horizon):
            self.generate_tasks(t)
            self.agents_act()
            self.update_state()
            self.collect_metrics()
        return self.state

