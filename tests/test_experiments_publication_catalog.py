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
    assert len(specs) == 6
    assert specs[0].study_id == "E1_scalability"
    assert specs[0].node_count in {10, 50}
    assert specs[-1].study_id == "E5_llm_vs_algorithmic"
    assert specs[-1].methods == ["min-load", "mas-hybrid", "mas-llm"]
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


def test_get_method_variant_and_method_to_row_contract() -> None:
    """Catalog lookup and serialization should preserve stable method keys."""
    variant = get_method_variant("mas-llm")
    row = method_to_row(variant)
    assert row["key"] == "mas-llm"
    assert row["ready"] is True
    assert row["llm_enabled"] is True
    with pytest.raises(KeyError, match="Unknown method variant"):
        get_method_variant("missing-method")

