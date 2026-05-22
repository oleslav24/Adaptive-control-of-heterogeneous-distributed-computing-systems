"""Tests for publication hypothesis evaluation enrichment fields."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from project.experiments import publication as pub


def _row(
    *,
    study_id: str,
    scenario: str,
    method: str,
    seed: int,
    avg_latency: float,
    load_imbalance: float = 0.5,
    throughput: float = 1.0,
    stability_latency_var: float = 0.2,
    node_count: int = 50,
    task_count: int = 300,
    adaptivity: float = 1.0,
) -> dict[str, object]:
    """Build raw publication run row for hypothesis evaluator tests."""
    return {
        "study_id": study_id,
        "scenario": scenario,
        "method": method,
        "seed": seed,
        "node_count": node_count,
        "task_count": task_count,
        "avg_latency": avg_latency,
        "load_imbalance": load_imbalance,
        "throughput": throughput,
        "stability_latency_var": stability_latency_var,
        "adaptivity": adaptivity,
    }


def _raw_runs_fixture() -> pd.DataFrame:
    """Construct minimal raw-runs frame covering all H1-H5 slices."""
    rows: list[dict[str, object]] = []
    rows.extend(
        [
            _row(study_id="E1_scalability", scenario="static", method="round-robin", seed=1, avg_latency=10.0, load_imbalance=0.90),
            _row(study_id="E1_scalability", scenario="static", method="min-load", seed=1, avg_latency=9.2, load_imbalance=0.76),
            _row(study_id="E1_scalability", scenario="static", method="greedy", seed=1, avg_latency=8.9, load_imbalance=0.74),
            _row(study_id="E1_scalability", scenario="static", method="max-min", seed=1, avg_latency=8.7, load_imbalance=0.72),
            _row(study_id="E1_scalability", scenario="static", method="mas-hybrid", seed=1, avg_latency=6.1, load_imbalance=0.33),
            _row(study_id="E1_scalability", scenario="static", method="mas-ml", seed=1, avg_latency=5.8, load_imbalance=0.30),
            _row(study_id="E1_scalability", scenario="static", method="mas-znn", seed=1, avg_latency=5.7, load_imbalance=0.29),
            _row(study_id="E1_scalability", scenario="static", method="mas-llm", seed=1, avg_latency=6.2, load_imbalance=0.34, adaptivity=1.25),
        ]
    )
    rows.extend(
        [
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="round-robin",
                seed=2,
                avg_latency=11.0,
                throughput=0.90,
                stability_latency_var=0.62,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="min-load",
                seed=2,
                avg_latency=10.5,
                throughput=0.95,
                stability_latency_var=0.54,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="mas-basic",
                seed=2,
                avg_latency=7.8,
                throughput=1.18,
                stability_latency_var=0.32,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="mas-hybrid",
                seed=2,
                avg_latency=7.5,
                throughput=1.21,
                stability_latency_var=0.29,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="mas-ml",
                seed=2,
                avg_latency=7.4,
                throughput=1.23,
                stability_latency_var=0.30,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="mas-znn",
                seed=2,
                avg_latency=7.3,
                throughput=1.24,
                stability_latency_var=0.28,
            ),
            _row(
                study_id="E3_robustness",
                scenario="node-failures",
                method="mas-llm",
                seed=2,
                avg_latency=7.6,
                throughput=1.19,
                stability_latency_var=0.31,
                adaptivity=1.33,
            ),
        ]
    )
    rows.extend(
        [
            _row(study_id="E2_adaptivity", scenario="dynamic-load", method="mas-basic", seed=3, avg_latency=9.2),
            _row(study_id="E2_adaptivity", scenario="peak-load", method="mas-basic", seed=3, avg_latency=8.9),
            _row(study_id="E2_adaptivity", scenario="dynamic-load", method="mas-ml", seed=3, avg_latency=6.0),
            _row(study_id="E2_adaptivity", scenario="peak-load", method="mas-ml", seed=3, avg_latency=6.2),
            _row(study_id="E2_adaptivity", scenario="dynamic-load", method="mas-znn", seed=3, avg_latency=5.9),
            _row(study_id="E2_adaptivity", scenario="peak-load", method="mas-znn", seed=3, avg_latency=6.1),
        ]
    )
    rows.extend(
        [
            _row(study_id="E4_hybrid_vs_classical", scenario="static", method="round-robin", seed=4, avg_latency=9.8, node_count=100, task_count=800),
            _row(study_id="E4_hybrid_vs_classical", scenario="static", method="min-load", seed=4, avg_latency=9.4, node_count=100, task_count=800),
            _row(study_id="E4_hybrid_vs_classical", scenario="static", method="greedy", seed=4, avg_latency=9.2, node_count=100, task_count=800),
            _row(study_id="E4_hybrid_vs_classical", scenario="static", method="max-min", seed=4, avg_latency=9.0, node_count=100, task_count=800),
            _row(study_id="E4_hybrid_vs_classical", scenario="static", method="mas-hybrid", seed=4, avg_latency=7.1, node_count=100, task_count=800),
        ]
    )
    rows.extend(
        [
            _row(study_id="E5_llm_vs_algorithmic", scenario="dynamic-load", method="mas-hybrid", seed=5, avg_latency=7.6, adaptivity=1.08),
            _row(study_id="E5_llm_vs_algorithmic", scenario="dynamic-load", method="mas-llm", seed=5, avg_latency=7.0, adaptivity=1.24),
            _row(study_id="E5_llm_vs_algorithmic", scenario="peak-load", method="mas-hybrid", seed=5, avg_latency=7.8, adaptivity=1.06),
            _row(study_id="E5_llm_vs_algorithmic", scenario="peak-load", method="mas-llm", seed=5, avg_latency=7.2, adaptivity=1.22),
        ]
    )
    return pd.DataFrame(rows)


def test_evaluate_hypotheses_includes_significance_fields() -> None:
    """Hypotheses frame should expose deterministic significance metadata."""
    hypotheses = pub._evaluate_hypotheses(_raw_runs_fixture())  # noqa: SLF001
    assert set(hypotheses["hypothesis"].tolist()) == {"H1", "H2", "H3", "H4", "H5"}
    assert "significance_supported" in hypotheses.columns
    p_value_columns = [name for name in hypotheses.columns if name.startswith("p_value_")]
    effect_columns = [name for name in hypotheses.columns if name.startswith("effect_size_")]
    assert p_value_columns
    assert effect_columns

    for _, row in hypotheses.iterrows():
        assert isinstance(row["confirmed"], (bool, np.bool_))
        assert isinstance(row["significance_supported"], (bool, np.bool_))
        for column in p_value_columns:
            value = row.get(column)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            numeric = float(value)
            assert 0.0 <= numeric <= 1.0
