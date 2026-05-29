"""Unified quality-gate contract helpers for experiment artifact bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from project.experiments.integrity import verify_artifact_integrity_file
from project.experiments.manifest import validate_run_manifest_file

QualityGateState = Literal["pass", "fail", "unknown"]

QUALITY_GATE_SCHEMA = "adaptive-testbed.quality-gate"
QUALITY_GATE_SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class QualityGateCheck:
    """One quality-gate check item."""

    gate_id: str
    title: str
    required: bool
    state: QualityGateState
    detail: str
    evidence: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QualityGateAssessment:
    """Final quality-gate assessment for one run bundle."""

    mode: str
    scope: str
    checks: tuple[QualityGateCheck, ...]
    notes: tuple[str, ...]
    ok: bool


def build_quality_gate_assessment(
    *,
    mode: str,
    scope: str,
    checks: list[QualityGateCheck],
    notes: list[str] | tuple[str, ...] = (),
) -> QualityGateAssessment:
    """Build aggregate quality-gate assessment from check list."""
    required_failures = [
        check for check in checks if check.required and check.state != "pass"
    ]
    return QualityGateAssessment(
        mode=str(mode).strip() or "unknown",
        scope=str(scope).strip() or "unknown",
        checks=tuple(checks),
        notes=tuple(str(item) for item in notes),
        ok=len(required_failures) == 0,
    )


def quality_gate_payload(assessment: QualityGateAssessment) -> dict[str, Any]:
    """Convert assessment dataclasses into JSON payload."""
    counts = {"pass": 0, "fail": 0, "unknown": 0}
    required_total = 0
    required_passed = 0
    required_failed = 0
    optional_total = 0
    optional_failed = 0

    checks_payload: list[dict[str, Any]] = []
    for check in assessment.checks:
        counts[check.state] = counts.get(check.state, 0) + 1
        if check.required:
            required_total += 1
            if check.state == "pass":
                required_passed += 1
            else:
                required_failed += 1
        else:
            optional_total += 1
            if check.state == "fail":
                optional_failed += 1
        checks_payload.append(
            {
                "gate_id": check.gate_id,
                "title": check.title,
                "required": check.required,
                "state": check.state,
                "detail": check.detail,
                "evidence": list(check.evidence),
                "errors": list(check.errors),
            }
        )

    return {
        "schema": QUALITY_GATE_SCHEMA,
        "schema_version": QUALITY_GATE_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": assessment.mode,
        "scope": assessment.scope,
        "ok": assessment.ok,
        "counts": counts,
        "required": {
            "total": required_total,
            "passed": required_passed,
            "failed": required_failed,
        },
        "optional": {
            "total": optional_total,
            "failed": optional_failed,
        },
        "checks": checks_payload,
        "notes": list(assessment.notes),
    }


def write_quality_gate_file(path: str | Path, assessment: QualityGateAssessment) -> str:
    """Persist quality-gate payload to JSON file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = quality_gate_payload(assessment)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
    return str(target)


def render_quality_gate_failure(assessment: QualityGateAssessment) -> str:
    """Render concise fail-fast message for required quality-gate failures."""
    failed = [
        check
        for check in assessment.checks
        if check.required and check.state != "pass"
    ]
    if not failed:
        return "quality gate failed without explicit required-check failures"
    parts = [f"{item.gate_id}:{item.state}" for item in failed]
    return "; ".join(parts)


def check_manifest_artifact(
    *,
    gate_id: str,
    title: str,
    path: str,
    required: bool = True,
) -> QualityGateCheck:
    """Build check from run-manifest file validation."""
    cleaned = str(path).strip()
    if not cleaned:
        return _missing_check(
            gate_id=gate_id,
            title=title,
            required=required,
            detail="manifest path is missing",
        )
    ok, errors = validate_run_manifest_file(cleaned)
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="pass" if ok else "fail",
        detail="manifest validation passed" if ok else "manifest validation failed",
        evidence=(cleaned,),
        errors=tuple(str(item) for item in errors),
    )


def check_integrity_artifact(
    *,
    gate_id: str,
    title: str,
    path: str,
    required: bool = True,
) -> QualityGateCheck:
    """Build check from artifact-integrity verification file."""
    cleaned = str(path).strip()
    if not cleaned:
        return _missing_check(
            gate_id=gate_id,
            title=title,
            required=required,
            detail="integrity path is missing",
        )
    ok, errors = verify_artifact_integrity_file(cleaned)
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="pass" if ok else "fail",
        detail="integrity verification passed" if ok else "integrity verification failed",
        evidence=(cleaned,),
        errors=tuple(str(item) for item in errors),
    )


def check_json_ok_artifact(
    *,
    gate_id: str,
    title: str,
    path: str,
    required: bool = True,
    allow_skipped: bool = False,
) -> QualityGateCheck:
    """Build check from JSON file with top-level `ok` status."""
    cleaned = str(path).strip()
    if not cleaned:
        return _missing_check(
            gate_id=gate_id,
            title=title,
            required=required,
            detail="validation artifact path is missing",
        )
    payload = _read_json_object(cleaned)
    if payload is None:
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="fail" if required else "unknown",
            detail="validation artifact is unreadable",
            evidence=(cleaned,),
            errors=("unreadable-json",),
        )
    if allow_skipped and bool(payload.get("skipped", False)):
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="pass",
            detail="validation gate was skipped by design",
            evidence=(cleaned,),
        )
    ok = payload.get("ok")
    if isinstance(ok, bool):
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="pass" if ok else "fail",
            detail="validation gate passed" if ok else "validation gate failed",
            evidence=(cleaned,),
            errors=tuple(_extract_payload_errors(payload)),
        )
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="fail" if required else "unknown",
        detail="validation artifact has no boolean `ok` field",
        evidence=(cleaned,),
    )


def check_claims_gate_artifact(
    *,
    gate_id: str,
    title: str,
    path: str,
    required: bool = False,
) -> QualityGateCheck:
    """Build check from claims report (`gate.ok`)."""
    cleaned = str(path).strip()
    if not cleaned:
        return _missing_check(
            gate_id=gate_id,
            title=title,
            required=required,
            detail="claims report path is missing",
        )
    payload = _read_json_object(cleaned)
    if payload is None:
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="fail" if required else "unknown",
            detail="claims report is unreadable",
            evidence=(cleaned,),
            errors=("unreadable-json",),
        )
    gate = payload.get("gate")
    if not isinstance(gate, dict):
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="fail" if required else "unknown",
            detail="claims report has no `gate` object",
            evidence=(cleaned,),
        )
    ok = gate.get("ok")
    if isinstance(ok, bool):
        return QualityGateCheck(
            gate_id=gate_id,
            title=title,
            required=required,
            state="pass" if ok else "fail",
            detail="claims gate passed" if ok else "claims gate failed",
            evidence=(cleaned,),
            errors=tuple(str(item) for item in gate.get("errors", []) if str(item).strip()),
        )
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="fail" if required else "unknown",
        detail="claims gate has no boolean `ok` field",
        evidence=(cleaned,),
    )


def check_file_exists(
    *,
    gate_id: str,
    title: str,
    path: str,
    required: bool = True,
) -> QualityGateCheck:
    """Build check for plain file existence."""
    cleaned = str(path).strip()
    if not cleaned:
        return _missing_check(
            gate_id=gate_id,
            title=title,
            required=required,
            detail="file path is missing",
        )
    target = Path(cleaned)
    exists = target.exists() and target.is_file()
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="pass" if exists else "fail",
        detail="file exists" if exists else "file is missing",
        evidence=(cleaned,),
    )


def _missing_check(
    *,
    gate_id: str,
    title: str,
    required: bool,
    detail: str,
) -> QualityGateCheck:
    """Build missing-artifact check with required/optional semantics."""
    return QualityGateCheck(
        gate_id=gate_id,
        title=title,
        required=required,
        state="fail" if required else "unknown",
        detail=detail,
    )


def _read_json_object(path: str) -> dict[str, Any] | None:
    """Read JSON object or return None on failure."""
    target = Path(path)
    if not target.exists() or not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _extract_payload_errors(payload: dict[str, Any]) -> list[str]:
    """Extract human-readable errors list from a JSON validation payload."""
    raw = payload.get("errors")
    if not isinstance(raw, list):
        return []
    errors: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            errors.append(text)
    return errors
