"""Multi-agent scheduler that runs agent lifecycle and routes messages."""

from __future__ import annotations

from dataclasses import dataclass, field

from project.core.agent import Agent, AgentMessage
from project.core.models import SystemState
from project.simulation.context import SimulationContext


@dataclass
class MultiAgentSystem:
    """Run observe/decide/act phases for all agents with message dispatch."""

    agents: list[Agent]
    context: SimulationContext
    message_log: list[AgentMessage] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Bind shared context to each agent and index agents by name."""
        self._agents_by_name = {agent.name: agent for agent in self.agents}
        for agent in self.agents:
            agent.bind(self.context)

    def step(self, state: SystemState) -> None:
        """Execute one MAS cycle for the provided state snapshot."""
        for agent in self.agents:
            agent.observe(state)

        for agent in self.agents:
            agent.decide()
            self._dispatch_messages()

        for agent in self.agents:
            agent.act()
            self._dispatch_messages()

    def _dispatch_messages(self) -> None:
        """Deliver all pending outbox messages to recipients."""
        for agent in self.agents:
            for message in agent.flush_outbox():
                self.message_log.append(message)
                self._deliver(message)

    def _deliver(self, message: AgentMessage) -> None:
        """Route message to all agents or a specific recipient."""
        if message.recipient is None:
            for agent in self.agents:
                if agent.name != message.sender:
                    agent.receive(message)
            return
        recipient = self._agents_by_name.get(message.recipient)
        if recipient is not None:
            recipient.receive(message)
