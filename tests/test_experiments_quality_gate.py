"""Unit tests for unified experiment quality-gate helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from project.core.config import load_config
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.quality_gate import (
    build_quality_gate_assessment,
    check_claims_gate_artifact,
    check_file_exists,
    check_integrity_artifact,
    check_json_ok_artifact,
    check_manifest_artifact,
    quality_gate_payload,
    render_quality_gate_failure,
    write_quality_gate_file,
)


def test_quality_gate_required_checks_drive_ok_status() -> None:
    """Assessment should pass when required checks pass, even with optional failures."""
    workspace = _workspace_dir("quality-gate-pass")
    sample = workspace / "sample.txt"
    sample.write_text("ok", encoding="utf-8")
    integrity_path = Path(
        write_artifact_integrity_file(
            workspace / "artifact_integrity.json",
            {"sample_txt": str(sample)},
        )
    )
    validation_path = workspace / "summary_validation.json"
    validation_path.write_text('{"ok": true, "errors": []}', encoding="utf-8")
    claims_path = workspace / "claims_report.json"
    claims_path.write_text('{"gate": {"ok": false, "errors": ["weak evidence"]}}', encoding="utf-8")

    config = load_config("config.yaml")
    manifest_path = workspace / "publication_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="publication-study",
            cli_args=["--publication-study"],
            extra={},
        ),
    )

    checks = [
        check_manifest_artifact(
            gate_id="manifest",
            title="Manifest",
            path=str(manifest_path),
            required=True,
        ),
        check_integrity_artifact(
            gate_id="integrity",
            title="Integrity",
            path=str(integrity_path),
            required=True,
        ),
        check_json_ok_artifact(
            gate_id="summary",
            title="Summary validation",
            path=str(validation_path),
            required=True,
        ),
        check_claims_gate_artifact(
            gate_id="claims",
            title="Claims gate",
            path=str(claims_path),
            required=False,
        ),
    ]
    assessment = build_quality_gate_assessment(
        mode="publication-study",
        scope="publication_bundle",
        checks=checks,
    )
    payload = quality_gate_payload(assessment)

    assert assessment.ok is True
    assert payload["required"]["failed"] == 0
    assert payload["optional"]["failed"] == 1
    assert payload["counts"]["fail"] == 1

    gate_path = Path(write_quality_gate_file(workspace / "quality_gate.json", assessment))
    assert gate_path.exists()


def test_quality_gate_missing_required_file_fails_fast_message() -> None:
    """Missing required check should flip gate to fail and produce stable message."""
    checks = [
        check_file_exists(
            gate_id="required-artifact",
            title="Required artifact",
            path="",
            required=True,
        )
    ]
    assessment = build_quality_gate_assessment(
        mode="chapter10-study",
        scope="chapter10_bundle",
        checks=checks,
    )
    assert assessment.ok is False
    message = render_quality_gate_failure(assessment)
    assert "required-artifact:fail" in message


def test_quality_gate_skipped_validation_is_allowed_when_configured() -> None:
    """Validation payload with skipped=true should pass when allow_skipped is enabled."""
    workspace = _workspace_dir("quality-gate-skipped")
    skipped_path = workspace / "literature_evidence_gate.json"
    skipped_path.write_text('{"skipped": true}', encoding="utf-8")

    skipped_allowed = check_json_ok_artifact(
        gate_id="literature",
        title="Literature gate",
        path=str(skipped_path),
        required=False,
        allow_skipped=True,
    )
    skipped_unknown = check_json_ok_artifact(
        gate_id="literature",
        title="Literature gate",
        path=str(skipped_path),
        required=False,
        allow_skipped=False,
    )

    assert skipped_allowed.state == "pass"
    assert skipped_unknown.state == "unknown"


def _workspace_dir(suffix: str) -> Path:
    """Create unique writable test directory under outputs/test-suite."""
    path = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path
