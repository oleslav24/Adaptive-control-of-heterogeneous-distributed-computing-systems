from __future__ import annotations


class ZNNBalancer:
    """
    Simplified ZNN-style balancing dynamics.
    Produces per-node bias where positive values mean "prefer this node".
    """

    def __init__(self, gain: float = 0.35) -> None:
        self.gain = max(0.01, float(gain))

    def node_bias(
        self,
        node_loads: dict[str, float],
        predicted_avg_load: float,
    ) -> dict[str, float]:
        if not node_loads:
            return {}
        target = max(0.0, min(1.0, float(predicted_avg_load)))
        bias: dict[str, float] = {}
        for node_id, load in node_loads.items():
            error = float(load) - target
            bias_value = -self.gain * error
            bias[node_id] = max(-1.0, min(1.0, bias_value))
        return bias

