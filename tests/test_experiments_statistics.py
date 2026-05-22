"""Unit tests for deterministic publication statistics helpers."""

from __future__ import annotations

import pytest

from project.experiments.statistics import (
    cliffs_delta,
    mean_difference,
    permutation_p_value,
    significance_payload,
)


def test_mean_difference_and_cliffs_delta_direction() -> None:
    """Directional statistics should reflect better/worse sample ordering."""
    left = [4.0, 5.0, 6.0]
    right = [1.0, 2.0, 3.0]
    assert mean_difference(left, right) > 0.0
    assert cliffs_delta(left, right) == pytest.approx(1.0)
    assert cliffs_delta(right, left) == pytest.approx(-1.0)


def test_permutation_p_value_is_bounded_and_deterministic() -> None:
    """Permutation p-value should be deterministic for fixed seed and bounded in [0, 1]."""
    left = [10.0, 11.0, 12.0, 13.0]
    right = [4.0, 5.0, 6.0, 7.0]
    p1 = permutation_p_value(left, right, alternative="greater", iterations=600, seed=77)
    p2 = permutation_p_value(left, right, alternative="greater", iterations=600, seed=77)
    assert p1 == pytest.approx(p2)
    assert 0.0 <= p1 <= 1.0


def test_significance_payload_handles_empty_samples() -> None:
    """Payload should stay stable for empty or invalid sample input."""
    payload = significance_payload([], [], alternative="two-sided", iterations=100, seed=11)
    assert payload["sample_size_left"] == 0.0
    assert payload["sample_size_right"] == 0.0
    assert payload["p_value_permutation"] == 1.0
    assert payload["effect_size_cliffs_delta"] == 0.0
    assert payload["statistically_significant"] is False
