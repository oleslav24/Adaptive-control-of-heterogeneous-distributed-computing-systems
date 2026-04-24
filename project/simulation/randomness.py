"""Deterministic seeding utilities for reproducible simulation runs."""

from __future__ import annotations

import random

import numpy as np


def set_global_seed(seed: int) -> int:
    """Set random seeds for Python and NumPy and return normalized value."""
    normalized = int(seed) % (2**32 - 1)
    random.seed(normalized)
    np.random.seed(normalized)
    return normalized
