"""QoS agent that tracks deadline pressure for queued tasks."""

from __future__ import annotations

from project.core.agent import Agent, AgentMessage
from project.core.models import Task


class QoSAgent(Agent):
    """Identify urgent tasks and signal them to the compute agent."""

    def __init__(self, name: str = "qos", slack_threshold: int = 1) -> None:
        super().__init__(name=name)
        self.slack_threshold = slack_threshold

    def decide(self) -> None:
        """Build urgency list based on deadline slack."""
        if self.context is None or self.state is None:
            return

        urgent_task_ids = []
        for task in self.context.queued_tasks():
            if self._is_urgent(task, self.state.current_time):
                urgent_task_ids.append(task.id)

        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="deadline_alerts",
                payload={"urgent_task_ids": urgent_task_ids},
            )
        )

    def act(self) -> None:
        """No direct actuation for this agent."""
        return

    def _is_urgent(self, task: Task, current_time: int) -> bool:
        """Treat task as urgent when slack is below configured threshold."""
        remaining_budget = task.deadline - current_time
        return remaining_budget - task.duration <= self.slack_threshold
