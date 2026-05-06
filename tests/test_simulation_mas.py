"""Integration tests for MAS lifecycle and message routing."""

from __future__ import annotations

from project.core.agent import Agent, AgentMessage
from project.core.models import Node, SystemState
from project.simulation.context import SimulationContext
from project.simulation.mas import MultiAgentSystem
from project.simulation.network import NetworkModel
from project.simulation.task_queue import TaskQueue


class SenderAgent(Agent):
    """Agent that emits one directed and one broadcast message per decide phase."""

    def __init__(self) -> None:
        super().__init__(name="sender")

    def decide(self) -> None:
        self.send(
            AgentMessage(
                sender=self.name,
                recipient="receiver",
                topic="direct",
                payload={"k": "v"},
            )
        )
        self.send(
            AgentMessage(
                sender=self.name,
                recipient=None,
                topic="broadcast",
                payload={"x": 1},
            )
        )

    def act(self) -> None:
        return


class ReceiverAgent(Agent):
    """Agent that consumes all messages in decide and stores seen topics."""

    def __init__(self) -> None:
        super().__init__(name="receiver")
        self.seen_topics: list[str] = []

    def decide(self) -> None:
        for message in self.read_messages():
            self.seen_topics.append(message.topic)

    def act(self) -> None:
        return


def test_mas_routes_direct_and_broadcast_messages() -> None:
    """Receiver should get both directed and broadcast messages after one MAS step."""
    context = SimulationContext(
        nodes={"node-1": Node(id="node-1", cpu=8.0, memory=16.0, gpu=0.0)},
        queue=TaskQueue(),
        running_tasks={"node-1": []},
        completed_tasks=[],
        future_tasks=[],
        network=NetworkModel(),
    )
    sender = SenderAgent()
    receiver = ReceiverAgent()
    mas = MultiAgentSystem(agents=[sender, receiver], context=context)
    mas.step(SystemState())

    assert mas.message_log
    assert [msg.topic for msg in mas.message_log] == ["direct", "broadcast"]
    assert receiver.seen_topics == ["direct", "broadcast"]
