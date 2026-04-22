from __future__ import annotations

from project.core.agent import Agent, AgentMessage
from project.core.models import Task


class QoSAgent(Agent):
    def __init__(self, name: str = "qos", slack_threshold: int = 1) -> None:
        super().__init__(name=name)
        self.slack_threshold = slack_threshold

    def decide(self) -> None:
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
        return

    def _is_urgent(self, task: Task, current_time: int) -> bool:
        remaining_budget = task.deadline - current_time
        return remaining_budget - task.duration <= self.slack_threshold

