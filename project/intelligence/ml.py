from __future__ import annotations

import numpy as np


class LinearLoadRegressor:
    """Small linear regression model for one-step-ahead forecasting."""

    def __init__(self, window: int = 6) -> None:
        self.window = max(2, int(window))

    def predict_next(self, series: list[float]) -> float:
        if not series:
            return 0.0
        values = np.asarray(series[-self.window :], dtype=float)
        if values.size == 1:
            return float(values[0])
        x = np.arange(values.size, dtype=float)
        design = np.column_stack((x, np.ones_like(x)))
        coeffs, _, _, _ = np.linalg.lstsq(design, values, rcond=None)
        slope, intercept = coeffs
        prediction = slope * float(values.size) + intercept
        return float(max(0.0, prediction))

