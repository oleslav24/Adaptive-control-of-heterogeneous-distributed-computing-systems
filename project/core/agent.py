from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from abc import ABC, abstractmethod

from .models import SystemState

if TYPE_CHECKING:
    from project.simulation.context import SimulationContext


@dataclass(slots=True)
class AgentMessage:
    sender: str
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    recipient: str | None = None


class Agent(ABC):
    """Base interface for all agents in the testbed."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.state: SystemState | None = None
        self.context: SimulationContext | None = None
        self._inbox: list[AgentMessage] = []
        self._outbox: list[AgentMessage] = []

    def bind(self, context: SimulationContext) -> None:
        self.context = context

    def observe(self, state: SystemState) -> None:
        """Read current system state."""
        self.state = state

    def receive(self, message: AgentMessage) -> None:
        self._inbox.append(message)

    def read_messages(self) -> list[AgentMessage]:
        messages = list(self._inbox)
        self._inbox.clear()
        return messages

    def send(self, message: AgentMessage) -> None:
        """Minimal communication primitive: agent.send(message)."""
        self._outbox.append(message)

    def flush_outbox(self) -> list[AgentMessage]:
        messages = list(self._outbox)
        self._outbox.clear()
        return messages

    @abstractmethod
    def decide(self) -> None:
        """Compute internal decision based on observed state."""

    @abstractmethod
    def act(self) -> None:
        """Apply action to controlled subsystem."""
