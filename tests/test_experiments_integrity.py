"""Unit tests for artifact integrity helpers."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from project.experiments.integrity import (
    INTEGRITY_SCHEMA,
    INTEGRITY_SCHEMA_VERSION,
    compute_file_sha256,
    validate_artifact_integrity_payload,
    verify_artifact_integrity_file,
    write_artifact_integrity_file,
)


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_write_and_verify_artifact_integrity_file() -> None:
    """Integrity report should verify untouched artifacts successfully."""
    output_dir = _workspace_test_output_dir("integrity-ok")
    alpha = output_dir / "alpha.txt"
    beta = output_dir / "beta.txt"
    alpha.write_text("alpha\n", encoding="utf-8")
    beta.write_text("beta\n", encoding="utf-8")

    report_path = output_dir / "artifact_integrity.json"
    write_artifact_integrity_file(
        report_path,
        {
            "alpha": str(alpha),
            "beta": str(beta),
        },
    )

    ok, errors = verify_artifact_integrity_file(report_path)
    assert ok is True
    assert errors == []

    with report_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["integrity_schema"] == INTEGRITY_SCHEMA
    assert payload["integrity_schema_version"] == INTEGRITY_SCHEMA_VERSION
    assert payload["artifacts"]["alpha"]["sha256"] == compute_file_sha256(alpha)


def test_verify_artifact_integrity_file_detects_tampering() -> None:
    """Verifier should report hash mismatch when artifact is modified."""
    output_dir = _workspace_test_output_dir("integrity-tamper")
    artifact = output_dir / "artifact.txt"
    artifact.write_text("stable\n", encoding="utf-8")
    report_path = output_dir / "artifact_integrity.json"
    write_artifact_integrity_file(report_path, {"artifact": str(artifact)})

    artifact.write_text("tampered\n", encoding="utf-8")
    ok, errors = verify_artifact_integrity_file(report_path)
    assert ok is False
    assert any("sha256 mismatch" in item for item in errors)


def test_validate_artifact_integrity_payload_reports_schema_errors() -> None:
    """Validator should reject malformed integrity payload shape."""
    errors = validate_artifact_integrity_payload(
        {
            "integrity_schema": "wrong",
            "integrity_schema_version": "999",
            "created_at_utc": "bad-date",
            "algorithm": "md5",
            "artifacts": {
                "x": {
                    "path": "",
                    "size_bytes": -1,
                    "sha256": "oops",
                }
            },
        }
    )
    assert any("integrity_schema" in item for item in errors)
    assert any("integrity_schema_version" in item for item in errors)
    assert any("created_at_utc" in item for item in errors)
    assert any("algorithm" in item for item in errors)
    assert any("Artifact 'x' has invalid 'sha256'." in item for item in errors)
