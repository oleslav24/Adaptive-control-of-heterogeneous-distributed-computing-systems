from __future__ import annotations

from project.core.agent import Agent, AgentMessage


class MonitoringAgent(Agent):
    def __init__(self, name: str = "monitoring") -> None:
        super().__init__(name=name)

    def decide(self) -> None:
        if self.state is None or self.context is None:
            return
        snapshot = {
            "time": self.state.current_time,
            "queue_size": len(self.context.queued_tasks()),
            "running_tasks": len(self.context.running_task_list()),
            "completed_tasks": self.state.completed_tasks,
            "node_loads": dict(self.state.node_loads),
        }
        self.send(
            AgentMessage(
                sender=self.name,
                recipient=None,
                topic="state_snapshot",
                payload=snapshot,
            )
        )

    def act(self) -> None:
        return

