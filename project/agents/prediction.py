"""Prediction agent that provides load forecasts and adaptive hints."""

from __future__ import annotations

from project.algorithms import normalize_algorithm
from project.core.agent import Agent, AgentMessage
from project.intelligence import LinearLoadRegressor, ZNNBalancer


class PredictionAgent(Agent):
    """Predict queue/load dynamics and provide balancing signals."""

    def __init__(
        self,
        prediction_window: int = 6,
        znn_gain: float = 0.35,
        high_queue_threshold: float = 2.0,
        high_load_threshold: float = 0.70,
        adaptive_algorithm: bool = True,
        congestion_algorithm: str = "round-robin",
        normal_algorithm: str = "min-load",
        name: str = "prediction",
    ) -> None:
        super().__init__(name=name)
        self.queue_model = LinearLoadRegressor(window=prediction_window)
        self.load_model = LinearLoadRegressor(window=prediction_window)
        self.znn = ZNNBalancer(gain=znn_gain)
        self.high_queue_threshold = float(high_queue_threshold)
        self.high_load_threshold = float(high_load_threshold)
        self.adaptive_algorithm = adaptive_algorithm
        self.congestion_algorithm = normalize_algorithm(congestion_algorithm)
        self.normal_algorithm = normalize_algorithm(normal_algorithm)
        self.queue_history: list[float] = []
        self.load_history: list[float] = []

    def decide(self) -> None:
        """Produce prediction signals and optional algorithm hint."""
        if self.context is None or self.state is None:
            return

        self._consume_snapshots()
        if not self.queue_history:
            self.queue_history.append(float(self.state.queue_lengths.get("global", 0)))
        if not self.load_history:
            self.load_history.append(float(self.state.avg_load))

        predicted_queue = self.queue_model.predict_next(self.queue_history)
        predicted_avg_load = min(1.0, self.load_model.predict_next(self.load_history))
        node_bias = self.znn.node_bias(self.state.node_loads, predicted_avg_load)

        self.context.predicted_queue = predicted_queue
        self.context.predicted_avg_load = predicted_avg_load
        self.context.prediction_node_bias = node_bias

        self.send(
            AgentMessage(
                sender=self.name,
                recipient="compute",
                topic="prediction_signal",
                payload={
                    "predicted_queue": predicted_queue,
                    "predicted_avg_load": predicted_avg_load,
                    "node_bias": node_bias,
                },
            )
        )

        if self.adaptive_algorithm:
            hint = self.normal_algorithm
            if (
                predicted_queue >= self.high_queue_threshold
                or predicted_avg_load >= self.high_load_threshold
            ):
                hint = self.congestion_algorithm
        else:
            hint = None
        self.context.record_decision(
            self.name,
            "prediction_signal",
            predicted_queue=predicted_queue,
            predicted_avg_load=predicted_avg_load,
            znn_node_bias=dict(node_bias),
            algorithm_hint=hint,
        )
        if hint is not None:
            self.send(
                AgentMessage(
                    sender=self.name,
                    recipient="optimization",
                    topic="prediction_algorithm_hint",
                    payload={"algorithm": hint},
                )
            )

    def act(self) -> None:
        """No direct side effects; output is delivered via MAS messages."""
        return

    def _consume_snapshots(self) -> None:
        """Update local history from monitoring snapshots and current state."""
        queue = float(self.state.queue_lengths.get("global", 0)) if self.state else 0.0
        load = float(self.state.avg_load) if self.state else 0.0
        seen_snapshot = False
        for message in self.read_messages():
            if message.topic != "state_snapshot":
                continue
            seen_snapshot = True
            queue = float(message.payload.get("queue_size", queue))
            payload_loads = message.payload.get("node_loads", {})
            if isinstance(payload_loads, dict) and payload_loads:
                load = sum(float(v) for v in payload_loads.values()) / float(
                    len(payload_loads)
                )
            else:
                load = float(message.payload.get("avg_load", load))
        if seen_snapshot or self.state is not None:
            self.queue_history.append(max(0.0, queue))
            self.load_history.append(max(0.0, load))
