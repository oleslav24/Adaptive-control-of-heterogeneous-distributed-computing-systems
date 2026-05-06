"""Tests for run-manifest validation contract."""

from __future__ import annotations

from project.core.config import load_config
from project.experiments.manifest import build_run_manifest, validate_run_manifest


def test_validate_run_manifest_accepts_complete_manifest() -> None:
    """Validator should pass for a complete manifest payload."""
    config = load_config("config.yaml")
    manifest = build_run_manifest(
        config=config,
        mode="unit-test",
        cli_args=["--config", "config.yaml"],
        extra={"scope": "test"},
    )
    errors = validate_run_manifest(manifest)
    assert errors == []


def test_validate_run_manifest_reports_missing_required_key() -> None:
    """Validator should report missing root keys."""
    config = load_config("config.yaml")
    manifest = build_run_manifest(
        config=config,
        mode="unit-test",
        cli_args=[],
        extra=None,
    )
    del manifest["config"]
    errors = validate_run_manifest(manifest)
    assert any("Missing required key: 'config'." in item for item in errors)
