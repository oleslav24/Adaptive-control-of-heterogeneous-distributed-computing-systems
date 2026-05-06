"""Tests for smoke baseline golden-comparison logic."""

from __future__ import annotations

from project.experiments.smoke import compare_baseline_with_golden


def test_compare_baseline_with_golden_passes_on_equal_fingerprints() -> None:
    """Comparison should pass when case fingerprints are equal."""
    current = {"fingerprints": {"single": "a1", "batch": "b1"}}
    golden = {"fingerprints": {"single": "a1", "batch": "b1"}}
    result = compare_baseline_with_golden(current=current, golden=golden)
    assert result["ok"] is True
    assert result["mismatches"] == []


def test_compare_baseline_with_golden_reports_mismatch() -> None:
    """Comparison should fail when any case fingerprint differs."""
    current = {"fingerprints": {"single": "a1", "batch": "b2"}}
    golden = {"fingerprints": {"single": "a1", "batch": "b1"}}
    result = compare_baseline_with_golden(current=current, golden=golden)
    assert result["ok"] is False
    assert any("Fingerprint mismatch for case 'batch'" in item for item in result["mismatches"])
