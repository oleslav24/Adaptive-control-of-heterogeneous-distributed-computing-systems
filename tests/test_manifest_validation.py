"""Tests for run-manifest validation contract."""

from __future__ import annotations

from project.core.config import load_config
from project.experiments.manifest import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    build_run_manifest,
    validate_run_manifest,
)


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


def test_validate_run_manifest_reports_schema_version_mismatch() -> None:
    """Validator should reject incompatible schema versions."""
    config = load_config("config.yaml")
    manifest = build_run_manifest(
        config=config,
        mode="unit-test",
        cli_args=[],
        extra={},
    )
    manifest["manifest_schema_version"] = "999"
    errors = validate_run_manifest(manifest)
    assert any("manifest_schema_version" in item for item in errors)


def test_validate_run_manifest_reports_bad_timestamp() -> None:
    """Validator should reject malformed timestamp field."""
    config = load_config("config.yaml")
    manifest = build_run_manifest(
        config=config,
        mode="unit-test",
        cli_args=[],
        extra={},
    )
    manifest["created_at_utc"] = "not-a-date"
    errors = validate_run_manifest(manifest)
    assert any("valid ISO-8601 datetime" in item for item in errors)


def test_build_run_manifest_sets_declared_schema_fields() -> None:
    """Builder should stamp schema identity and version in payload."""
    config = load_config("config.yaml")
    manifest = build_run_manifest(
        config=config,
        mode="unit-test",
        cli_args=[],
        extra={},
    )
    assert manifest["manifest_schema"] == MANIFEST_SCHEMA
    assert manifest["manifest_schema_version"] == MANIFEST_SCHEMA_VERSION
