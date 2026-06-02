"""Unit tests for publication catalog and study spec builders."""

from __future__ import annotations

import pytest

from project.experiments.publication_catalog import (
    METHOD_CATALOG,
    build_study_specs,
    get_method_variant,
    method_to_row,
)


def test_build_study_specs_quick_profile_shape() -> None:
    """Quick profile should create compact E1-E5 specification set."""
    seeds = [42, 43]
    ready = [variant.key for variant in METHOD_CATALOG if variant.ready]
    specs = build_study_specs(seeds=seeds, ready_methods=ready, quick=True)
    assert len(specs) == 9
    assert specs[0].study_id == "E1_scalability"
    assert specs[0].node_count in {10, 50}
    assert "max-min" in specs[0].methods
    assert "carbon-aware" in specs[0].methods
    e2_scenarios = sorted(
        {
            spec.scenario
            for spec in specs
            if spec.study_id == "E2_adaptivity"
        }
    )
    e5_scenarios = sorted(
        {
            spec.scenario
            for spec in specs
            if spec.study_id == "E5_llm_vs_algorithmic"
        }
    )
    assert e2_scenarios == ["dynamic-load", "peak-load"]
    assert e5_scenarios == ["dynamic-load", "peak-load"]
    assert specs[-1].study_id == "E6_carbon_vs_performance"
    assert specs[-1].methods == ["min-load", "greedy", "carbon-aware", "mas-hybrid", "mas-llm"]
    assert specs[-1].seeds == seeds


def test_build_study_specs_filters_unavailable_methods() -> None:
    """Unavailable methods should be removed from generated specs."""
    specs = build_study_specs(
        seeds=[7],
        ready_methods=["min-load", "mas-hybrid"],
        quick=False,
    )
    assert specs
    for spec in specs:
        assert spec.methods
        assert all(method in {"min-load", "mas-hybrid"} for method in spec.methods)


def test_build_study_specs_filters_quick_profile_methods() -> None:
    """Quick smoke specs should respect the same ready-method filter as full specs."""
    specs = build_study_specs(
        seeds=[7],
        ready_methods=["round-robin", "greedy"],
        quick=True,
    )
    assert specs
    for spec in specs:
        assert spec.methods
        assert all(method in {"round-robin", "greedy"} for method in spec.methods)


def test_build_study_specs_applies_study_specific_method_overrides() -> None:
    """Study overrides should trim only the selected study."""
    specs = build_study_specs(
        seeds=[7],
        ready_methods=["round-robin", "min-load", "greedy", "mas-hybrid"],
        quick=True,
        method_overrides_by_study={"E1_scalability": ["round-robin", "min-load"]},
    )
    e1_specs = [spec for spec in specs if spec.study_id == "E1_scalability"]
    e4_specs = [spec for spec in specs if spec.study_id == "E4_hybrid_vs_classical"]
    assert e1_specs
    assert e4_specs
    assert all(spec.methods == ["round-robin", "min-load"] for spec in e1_specs)
    assert "greedy" in e4_specs[0].methods


def test_get_method_variant_and_method_to_row_contract() -> None:
    """Catalog lookup and serialization should preserve stable method keys."""
    variant = get_method_variant("mas-llm")
    row = method_to_row(variant)
    assert row["key"] == "mas-llm"
    assert row["ready"] is True
    assert row["llm_enabled"] is True
    carbon = method_to_row(get_method_variant("carbon-aware"))
    assert carbon["algorithm"] == "carbon-aware"
    assert carbon["ready"] is True
    max_min = method_to_row(get_method_variant("max-min"))
    assert max_min["algorithm"] == "max-min"
    assert max_min["ready"] is True
    with pytest.raises(KeyError, match="Unknown method variant"):
        get_method_variant("missing-method")

