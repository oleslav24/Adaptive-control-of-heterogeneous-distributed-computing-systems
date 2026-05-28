"""Operational control-health appendix helpers for chapter10/paper artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal, Mapping

from project.experiments.integrity import verify_artifact_integrity_file

ControlSignalState = Literal["pass", "fail", "present", "unknown"]
ControlOverallStatus = Literal["STABLE", "WARNING", "CRITICAL"]

CONTROL_COMPONENT_ORDER = (
    "policy",
    "context",
    "logging",
    "iteration",
    "qgate",
    "autonomy",
    "integrity",
)
CRITICAL_COMPONENTS = {"context", "qgate", "integrity"}


@dataclass(frozen=True, slots=True)
class ControlHealthSignal:
    """One operational control signal resolved from produced artifacts."""

    component_id: str
    state: ControlSignalState
    reason: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ControlHealthAssessment:
    """Operational assessment payload for chapter10/paper appendices."""

    mode: str
    overall_status: ControlOverallStatus
    signal_counts: dict[str, int]
    signals: tuple[ControlHealthSignal, ...]
    notes: tuple[str, ...]


def build_control_health_assessment(
    output_paths: Mapping[str, str],
    *,
    mode: str,
) -> ControlHealthAssessment:
    """Build operational control-health assessment from generated artifacts."""
    existing = _existing_file_map(output_paths)
    raw_runs = _read_json_list(existing.get("publication_raw_runs_json", ""))
    llm_run_count = sum(1 for row in raw_runs if str(row.get("method", "")).strip() == "mas-llm")

    autonomy_signal = _assess_autonomy(raw_runs)
    signals = (
        _assess_policy(existing, llm_run_count),
        _assess_context(output_paths, existing),
        _assess_logging(existing),
        _assess_iteration(existing),
        _assess_qgate(existing),
        autonomy_signal,
        _assess_integrity(output_paths, existing),
    )
    counts = _signal_counts(signals)
    overall = _overall_status(signals)
    notes = (
        "Operational quality-gate appendix: not an algorithmic effectiveness metric.",
        "Demo controllability percentages are excluded from this artifact.",
    )
    return ControlHealthAssessment(
        mode=str(mode).strip() or "chapter10-study",
        overall_status=overall,
        signal_counts=counts,
        signals=signals,
        notes=notes,
    )


def control_health_payload(assessment: ControlHealthAssessment) -> dict[str, Any]:
    """Convert control-health dataclasses into JSON-friendly payload."""
    return {
        "schema": "adaptive-testbed.control-health.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "operational_quality_gate",
        "mode": assessment.mode,
        "overall_status": assessment.overall_status,
        "signal_counts": dict(assessment.signal_counts),
        "signals": [
            {
                "component_id": signal.component_id,
                "state": signal.state,
                "reason": signal.reason,
                "evidence": list(signal.evidence),
            }
            for signal in assessment.signals
        ],
        "notes": list(assessment.notes),
    }


def write_control_health_artifacts(
    output_dir: Path,
    assessment: ControlHealthAssessment,
) -> dict[str, str]:
    """Persist JSON and markdown control-health appendix artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "chapter10_control_health.json"
    markdown_path = output_dir / "chapter10_control_health.md"
    payload = control_health_payload(assessment)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(assessment), encoding="utf-8")
    return {
        "chapter10_control_health_json": str(json_path),
        "chapter10_control_health_md": str(markdown_path),
    }


def _existing_file_map(output_paths: Mapping[str, str]) -> dict[str, str]:
    """Return key/path pairs for files that exist on disk."""
    existing: dict[str, str] = {}
    for key, raw_path in output_paths.items():
        value = str(raw_path).strip()
        if not value:
            continue
        path = Path(value)
        if path.exists() and path.is_file():
            existing[key] = str(path)
    return existing


def _signal_counts(signals: tuple[ControlHealthSignal, ...]) -> dict[str, int]:
    """Count signal states in deterministic order."""
    counts = {"pass": 0, "fail": 0, "present": 0, "unknown": 0}
    for signal in signals:
        counts[signal.state] = counts.get(signal.state, 0) + 1
    return counts


def _overall_status(signals: tuple[ControlHealthSignal, ...]) -> ControlOverallStatus:
    """Aggregate per-component states into a single operational status."""
    for signal in signals:
        if signal.component_id in CRITICAL_COMPONENTS and signal.state == "fail":
            return "CRITICAL"
    if any(signal.state == "fail" for signal in signals):
        return "WARNING"
    if any(signal.state in {"present", "unknown"} for signal in signals):
        return "WARNING"
    return "STABLE"


def _assess_context(
    output_paths: Mapping[str, str],
    existing: Mapping[str, str],
) -> ControlHealthSignal:
    """Assess context continuity via manifest presence."""
    keys = ("chapter10_manifest_json", "publication_publication_manifest_json")
    present = [key for key in keys if key in existing]
    missing_reported = [key for key in keys if key in output_paths and key not in existing]
    if len(present) == len(keys):
        return ControlHealthSignal(
            component_id="context",
            state="pass",
            reason="Chapter10 and publication manifests are present.",
            evidence=tuple(present),
        )
    if present:
        return ControlHealthSignal(
            component_id="context",
            state="present",
            reason="Only part of context manifests is present.",
            evidence=tuple(sorted(set(present + missing_reported))),
        )
    return ControlHealthSignal(
        component_id="context",
        state="fail",
        reason="Manifest continuity artifacts are missing.",
        evidence=tuple(sorted(set(missing_reported))),
    )


def _assess_integrity(
    output_paths: Mapping[str, str],
    existing: Mapping[str, str],
) -> ControlHealthSignal:
    """Assess integrity via artifact integrity verification files."""
    keys = ("chapter10_artifact_integrity_json", "publication_artifact_integrity_json")
    valid: list[str] = []
    failed: list[str] = []
    for key in keys:
        path = existing.get(key, "")
        if not path:
            continue
        ok, errors = verify_artifact_integrity_file(path)
        if ok:
            valid.append(key)
        else:
            message = errors[0] if errors else "integrity verification failed"
            failed.append(f"{key}:{message}")
    if failed:
        return ControlHealthSignal(
            component_id="integrity",
            state="fail",
            reason="Integrity verification failed for one or more reports.",
            evidence=tuple(failed),
        )
    if len(valid) == len(keys):
        return ControlHealthSignal(
            component_id="integrity",
            state="pass",
            reason="Publication and Chapter10 integrity reports are valid.",
            evidence=tuple(valid),
        )
    missing_reported = [key for key in keys if key in output_paths and key not in existing]
    if valid:
        return ControlHealthSignal(
            component_id="integrity",
            state="present",
            reason="Only part of integrity reports is available.",
            evidence=tuple(sorted(set(valid + missing_reported))),
        )
    return ControlHealthSignal(
        component_id="integrity",
        state="fail",
        reason="Integrity reports are missing.",
        evidence=tuple(sorted(set(missing_reported))),
    )


def _assess_logging(existing: Mapping[str, str]) -> ControlHealthSignal:
    """Assess observability via publication telemetry artifacts."""
    keys = (
        "publication_raw_runs_csv",
        "publication_summary_csv",
        "publication_decision_trace_json",
    )
    present = [key for key in keys if key in existing]
    if len(present) == len(keys):
        return ControlHealthSignal(
            component_id="logging",
            state="pass",
            reason="Raw runs, summary, and decision trace artifacts are present.",
            evidence=tuple(present),
        )
    if present:
        return ControlHealthSignal(
            component_id="logging",
            state="present",
            reason="Only part of telemetry artifacts is available.",
            evidence=tuple(present),
        )
    return ControlHealthSignal(
        component_id="logging",
        state="fail",
        reason="Telemetry artifacts are missing.",
    )


def _assess_iteration(existing: Mapping[str, str]) -> ControlHealthSignal:
    """Assess iteration discipline via validation gates presence/OK state."""
    keys = (
        "publication_summary_validation_json",
        "publication_hypotheses_validation_json",
        "chapter10_package_validation_json",
    )
    verdicts = {key: _read_json_ok(existing.get(key, "")) for key in keys}
    if all(value is True for value in verdicts.values()):
        return ControlHealthSignal(
            component_id="iteration",
            state="pass",
            reason="Validation gates are present and passing.",
            evidence=tuple(keys),
        )
    failed = [key for key, value in verdicts.items() if value is False]
    if failed:
        return ControlHealthSignal(
            component_id="iteration",
            state="fail",
            reason="At least one validation gate failed.",
            evidence=tuple(failed),
        )
    present = [key for key, value in verdicts.items() if value is True]
    if present:
        return ControlHealthSignal(
            component_id="iteration",
            state="present",
            reason="Only part of validation gates are available.",
            evidence=tuple(present),
        )
    return ControlHealthSignal(
        component_id="iteration",
        state="unknown",
        reason="Validation gates are not available yet.",
    )


def _assess_qgate(existing: Mapping[str, str]) -> ControlHealthSignal:
    """Assess quality-gate state from validation/claims/evidence artifacts."""
    package_ok = _read_json_ok(existing.get("chapter10_package_validation_json", ""))
    hypothesis_ok = _read_json_ok(existing.get("publication_hypotheses_validation_json", ""))
    summary_ok = _read_json_ok(existing.get("publication_summary_validation_json", ""))
    claims_ok = _read_claims_gate_ok(existing.get("chapter10_claims_report_json", ""))
    literature = _read_json_dict(existing.get("chapter10_literature_evidence_gate_json", ""))
    literature_ok = _as_bool(literature.get("ok"))
    literature_skipped = _as_bool(literature.get("skipped"))

    if package_ok is False or hypothesis_ok is False or summary_ok is False or claims_ok is False:
        return ControlHealthSignal(
            component_id="qgate",
            state="fail",
            reason="One of quality-gate artifacts reports a failure.",
        )
    if literature_ok is False and not literature_skipped:
        return ControlHealthSignal(
            component_id="qgate",
            state="fail",
            reason="Literature evidence gate reported failure.",
            evidence=("chapter10_literature_evidence_gate_json",),
        )

    evidence: list[str] = []
    if package_ok is True:
        evidence.append("chapter10_package_validation_json")
    if summary_ok is True:
        evidence.append("publication_summary_validation_json")
    if hypothesis_ok is True:
        evidence.append("publication_hypotheses_validation_json")
    if claims_ok is True:
        evidence.append("chapter10_claims_report_json")
    if literature_ok is True or literature_skipped:
        evidence.append("chapter10_literature_evidence_gate_json")

    if package_ok is True and summary_ok is True and hypothesis_ok is True and claims_ok is True:
        return ControlHealthSignal(
            component_id="qgate",
            state="pass",
            reason="Quality-gate validations and claims gate are passing.",
            evidence=tuple(evidence),
        )
    if evidence:
        return ControlHealthSignal(
            component_id="qgate",
            state="present",
            reason="Quality-gate artifacts are partially available.",
            evidence=tuple(evidence),
        )
    return ControlHealthSignal(
        component_id="qgate",
        state="unknown",
        reason="Quality-gate artifacts are not available yet.",
    )


def _assess_autonomy(raw_runs: list[dict[str, Any]]) -> ControlHealthSignal:
    """Assess autonomy bounds from LLM run rows and guard counters."""
    llm_rows = [
        row for row in raw_runs if str(row.get("method", "")).strip() == "mas-llm"
    ]
    if not llm_rows:
        return ControlHealthSignal(
            component_id="autonomy",
            state="unknown",
            reason="No LLM method rows in publication raw runs.",
        )
    guarded = sum(
        1 for row in llm_rows if float(row.get("llm_guarded_decisions", 0.0)) > 0.0
    )
    if guarded == len(llm_rows):
        return ControlHealthSignal(
            component_id="autonomy",
            state="pass",
            reason="All LLM runs include guarded decisions.",
            evidence=("publication_raw_runs_json",),
        )
    if guarded > 0:
        return ControlHealthSignal(
            component_id="autonomy",
            state="present",
            reason="Only part of LLM runs include guarded decisions.",
            evidence=("publication_raw_runs_json",),
        )
    return ControlHealthSignal(
        component_id="autonomy",
        state="fail",
        reason="LLM runs were executed without guard evidence counters.",
        evidence=("publication_raw_runs_json",),
    )


def _assess_policy(
    existing: Mapping[str, str],
    llm_run_count: int,
) -> ControlHealthSignal:
    """Assess policy guard from decision trace guard events."""
    records = _read_json_list(existing.get("publication_decision_trace_json", ""))
    guard_events = sum(
        1 for item in records if str(item.get("event", "")).strip() == "llm_policy_guard"
    )
    if guard_events > 0:
        return ControlHealthSignal(
            component_id="policy",
            state="pass",
            reason="Decision trace contains LLM policy-guard events.",
            evidence=("publication_decision_trace_json",),
        )
    if llm_run_count > 0:
        return ControlHealthSignal(
            component_id="policy",
            state="fail",
            reason="LLM runs exist but no policy-guard events were captured.",
            evidence=("publication_decision_trace_json",),
        )
    if records:
        return ControlHealthSignal(
            component_id="policy",
            state="present",
            reason="Decision trace exists but no LLM events were executed.",
            evidence=("publication_decision_trace_json",),
        )
    return ControlHealthSignal(
        component_id="policy",
        state="unknown",
        reason="Decision trace evidence is unavailable.",
    )


def _read_claims_gate_ok(path: str) -> bool | None:
    """Read `gate.ok` value from claims report payload."""
    payload = _read_json_dict(path)
    gate = payload.get("gate")
    if not isinstance(gate, dict):
        return None
    return _as_bool(gate.get("ok"))


def _read_json_ok(path: str) -> bool | None:
    """Read optional top-level `ok` field from JSON artifact."""
    payload = _read_json_dict(path)
    return _as_bool(payload.get("ok"))


def _read_json_dict(path: str) -> dict[str, Any]:
    """Read JSON object from path or return empty dict on failure."""
    if not path:
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _read_json_list(path: str) -> list[dict[str, Any]]:
    """Read JSON list of object rows from path."""
    if not path:
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _as_bool(value: object) -> bool | None:
    """Return bool value or None for non-bool objects."""
    if isinstance(value, bool):
        return value
    return None


def _render_markdown(assessment: ControlHealthAssessment) -> str:
    """Render compact markdown appendix for chapter10 report package."""
    lines: list[str] = []
    lines.append("# Chapter10 Control-Health Appendix")
    lines.append("")
    lines.append("- Scope: operational quality-gate health (not algorithmic performance).")
    lines.append(f"- Mode: `{assessment.mode}`")
    lines.append(f"- Overall status: `{assessment.overall_status}`")
    lines.append(
        "- Signal counts: "
        f"pass={assessment.signal_counts['pass']}, "
        f"fail={assessment.signal_counts['fail']}, "
        f"present={assessment.signal_counts['present']}, "
        f"unknown={assessment.signal_counts['unknown']}."
    )
    lines.append("")
    lines.append("| Component | State | Reason | Evidence |")
    lines.append("|---|---|---|---|")
    lookup = {signal.component_id: signal for signal in assessment.signals}
    for component_id in CONTROL_COMPONENT_ORDER:
        signal = lookup.get(component_id)
        if signal is None:
            continue
        evidence = ", ".join(signal.evidence) if signal.evidence else "-"
        lines.append(
            f"| `{signal.component_id}` | `{signal.state}` | {signal.reason} | {evidence} |"
        )
    lines.append("")
    lines.append("## Notes")
    for note in assessment.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
