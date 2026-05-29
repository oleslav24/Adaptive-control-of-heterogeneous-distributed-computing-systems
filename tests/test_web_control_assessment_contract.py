"""Unit tests for control-assessment schema v2 contract helpers."""

from __future__ import annotations

from project.web.control_assessment_contract import (
    CONTROL_ASSESSMENT_SCHEMA,
    CONTROL_ASSESSMENT_SCHEMA_VERSION,
    build_control_assessment_consistency_report,
    build_control_assessment_payload,
    normalize_control_assessment_payload,
    validate_control_assessment_payload,
)


def test_build_and_validate_control_assessment_payload_v2() -> None:
    """Builder should emit schema-v2 payload that passes validation."""
    payload = build_control_assessment_payload(
        job_id="job-1",
        job_status="success",
        mode="real-job",
        source="runtime-assessment",
        signals=[
            {
                "component_id": "policy",
                "state": "pass",
                "reason": "ok",
                "evidence": ["decision_trace_json"],
            }
        ],
    )
    assert payload["control_assessment_schema"] == CONTROL_ASSESSMENT_SCHEMA
    assert payload["control_assessment_schema_version"] == CONTROL_ASSESSMENT_SCHEMA_VERSION
    errors = validate_control_assessment_payload(payload)
    assert errors == []


def test_normalize_control_assessment_payload_upgrades_legacy_shape() -> None:
    """Legacy payload without schema/summary should normalize to schema-v2."""
    normalized = normalize_control_assessment_payload(
        {
            "job_id": "legacy",
            "job_status": "running",
            "mode": "real-job",
            "signals": [
                {"component_id": "policy", "state": "PASS", "reason": "legacy"},
                {"component_id": "qgate", "state": "fail", "reason": "legacy-fail"},
            ],
        }
    )
    assert normalized["control_assessment_schema"] == CONTROL_ASSESSMENT_SCHEMA
    assert normalized["control_assessment_schema_version"] == CONTROL_ASSESSMENT_SCHEMA_VERSION
    assert normalized["summary"]["counts"] == {"pass": 1, "fail": 1, "present": 0, "unknown": 0}
    assert normalized["summary"]["overall_state"] == "fail"
    assert normalized["summary"]["failing_components"] == ["qgate"]
    assert validate_control_assessment_payload(normalized) == []


def test_validate_control_assessment_payload_reports_summary_inconsistency() -> None:
    """Validator should reject mismatched summary fields against signal list."""
    payload = build_control_assessment_payload(
        job_id="job-bad",
        job_status="failed",
        mode="real-job",
        signals=[
            {
                "component_id": "policy",
                "state": "fail",
                "reason": "bad",
                "evidence": [],
            }
        ],
    )
    payload["summary"]["overall_state"] = "pass"
    payload["summary"]["counts"] = {"pass": 1, "fail": 0, "present": 0, "unknown": 0}
    errors = validate_control_assessment_payload(payload)
    assert any("summary.overall_state" in item for item in errors)
    assert any("summary.counts" in item for item in errors)


def test_build_control_assessment_consistency_report_detects_mismatch() -> None:
    """Consistency report should mark payloads with divergent business fields as not ok."""
    runtime = build_control_assessment_payload(
        job_id="job-1",
        job_status="success",
        mode="real-job",
        source="runtime",
        signals=[{"component_id": "policy", "state": "pass", "reason": "runtime", "evidence": []}],
    )
    artifact = build_control_assessment_payload(
        job_id="job-1",
        job_status="success",
        mode="real-job",
        source="job-artifact",
        signals=[{"component_id": "policy", "state": "fail", "reason": "artifact", "evidence": []}],
    )
    report = build_control_assessment_consistency_report(
        {
            "runtime": runtime,
            "job-artifact": artifact,
        }
    )
    assert report["ok"] is False
    assert report["source_count"] == 2
    assert report["sources"] == ["job-artifact", "runtime"]
    assert report["mismatches"]
    assert isinstance(report["fingerprint_sha256"], str)
    assert len(report["fingerprint_sha256"]) == 64
