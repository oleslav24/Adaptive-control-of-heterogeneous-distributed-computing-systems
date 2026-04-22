from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SystemState


class Agent(ABC):
    """Base interface for all agents in the testbed."""

    @abstractmethod
    def observe(self, state: SystemState) -> None:
        """Read current system state."""

    @abstractmethod
    def decide(self) -> None:
        """Compute internal decision based on observed state."""

    @abstractmethod
    def act(self) -> None:
        """Apply action to controlled subsystem."""

