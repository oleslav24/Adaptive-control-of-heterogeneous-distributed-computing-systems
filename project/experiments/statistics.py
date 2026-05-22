"""Deterministic statistical helpers for publication hypothesis evaluation."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

Alternative = Literal["two-sided", "greater", "less"]


def sanitize_samples(values) -> np.ndarray:
    """Convert raw values to finite float numpy array."""
    try:
        arr = np.asarray(list(values), dtype=float)
    except Exception:  # noqa: BLE001
        return np.asarray([], dtype=float)
    if arr.size == 0:
        return arr
    return arr[np.isfinite(arr)]


def mean_difference(left, right) -> float:
    """Return mean(left) - mean(right) for finite samples, else 0."""
    left_arr = sanitize_samples(left)
    right_arr = sanitize_samples(right)
    if left_arr.size == 0 or right_arr.size == 0:
        return 0.0
    return float(np.mean(left_arr) - np.mean(right_arr))


def cliffs_delta(left, right) -> float:
    """Compute Cliff's delta in [-1, 1], robust for small samples."""
    left_arr = sanitize_samples(left)
    right_arr = sanitize_samples(right)
    if left_arr.size == 0 or right_arr.size == 0:
        return 0.0
    greater = 0
    less = 0
    for value_left in left_arr.tolist():
        greater += int(np.sum(value_left > right_arr))
        less += int(np.sum(value_left < right_arr))
    pairs = left_arr.size * right_arr.size
    if pairs <= 0:
        return 0.0
    return float((greater - less) / pairs)


def permutation_p_value(
    left,
    right,
    *,
    alternative: Alternative = "two-sided",
    iterations: int = 2000,
    seed: int = 42,
) -> float:
    """Compute deterministic permutation-test p-value for mean differences."""
    left_arr = sanitize_samples(left)
    right_arr = sanitize_samples(right)
    if left_arr.size == 0 or right_arr.size == 0:
        return 1.0
    if iterations <= 0:
        return 1.0

    observed = float(np.mean(left_arr) - np.mean(right_arr))
    pooled = np.concatenate([left_arr, right_arr])
    left_count = int(left_arr.size)
    rng = np.random.default_rng(int(seed))
    hits = 0
    eps = 1e-12
    for _ in range(int(iterations)):
        permuted = rng.permutation(pooled)
        stat = float(np.mean(permuted[:left_count]) - np.mean(permuted[left_count:]))
        if alternative == "greater":
            hits += int(stat >= observed - eps)
        elif alternative == "less":
            hits += int(stat <= observed + eps)
        else:
            hits += int(abs(stat) >= abs(observed) - eps)
    p_value = (hits + 1) / (int(iterations) + 1)
    return float(min(1.0, max(0.0, p_value)))


def significance_payload(
    left,
    right,
    *,
    alternative: Alternative = "two-sided",
    iterations: int = 2000,
    seed: int = 42,
) -> dict[str, float | bool]:
    """Build standardized significance fields for hypothesis rows."""
    left_arr = sanitize_samples(left)
    right_arr = sanitize_samples(right)
    p_value = permutation_p_value(
        left_arr,
        right_arr,
        alternative=alternative,
        iterations=iterations,
        seed=seed,
    )
    return {
        "sample_size_left": float(left_arr.size),
        "sample_size_right": float(right_arr.size),
        "effect_size_cliffs_delta": cliffs_delta(left_arr, right_arr),
        "p_value_permutation": p_value,
        "statistically_significant": bool(p_value < 0.05),
    }


def is_finite(value: float) -> bool:
    """Return True when value is finite float."""
    return math.isfinite(float(value))
