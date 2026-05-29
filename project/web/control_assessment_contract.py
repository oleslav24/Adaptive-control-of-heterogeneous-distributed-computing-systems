"""Schema v2 contract helpers for web control-assessment payloads."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


CONTROL_ASSESSMENT_SCHEMA = "adaptive-testbed.web.control-assessment"
CONTROL_ASSESSMENT_SCHEMA_VERSION = "2"
_SIGNAL_STATES = {"pass", "fail", "present", "unknown"}


def build_control_assessment_payload(
    *,
    job_id: str,
    job_status: str,
    mode: str,
    signals: list[dict[str, object]],
    summary: dict[str, object] | None = None,
    source: str = "runtime-assessment",
    generated_at_utc: str | None = None,
) -> dict[str, object]:
    """Build schema-v2 control-assessment payload."""
    normalized_signals = _normalize_signals(signals)
    normalized_summary = _normalize_summary(summary, normalized_signals)
    timestamp = generated_at_utc or datetime.now(timezone.utc).isoformat()
    return {
        "control_assessment_schema": CONTROL_ASSESSMENT_SCHEMA,
        "control_assessment_schema_version": CONTROL_ASSESSMENT_SCHEMA_VERSION,
        "generated_at_utc": timestamp,
        "source": _normalize_text(source, default="unknown"),
        "job_id": _normalize_text(job_id, default=""),
        "job_status": _normalize_text(job_status, default="unknown"),
        "mode": _normalize_text(mode, default="real-job"),
        "summary": normalized_summary,
        "signals": normalized_signals,
    }


def normalize_control_assessment_payload(
    payload: Mapping[str, object],
    *,
    fallback_job_id: str = "",
    fallback_job_status: str = "unknown",
    fallback_mode: str = "real-job",
    source_override: str | None = None,
) -> dict[str, object]:
    """Normalize legacy/partial control-assessment payload to schema v2 shape."""
    signals = _normalize_signals(payload.get("signals", []))
    summary = _normalize_summary(payload.get("summary"), signals)
    source = source_override if source_override is not None else _normalize_text(
        payload.get("source"),
        default="unknown",
    )
    generated_at_utc = payload.get("generated_at_utc")
    if not _is_valid_iso_datetime(generated_at_utc):
        generated_at_utc = datetime.now(timezone.utc).isoformat()
    return build_control_assessment_payload(
        job_id=_normalize_text(payload.get("job_id"), default=fallback_job_id),
        job_status=_normalize_text(payload.get("job_status"), default=fallback_job_status),
        mode=_normalize_text(payload.get("mode"), default=fallback_mode),
        signals=signals,
        summary=summary,
        source=source,
        generated_at_utc=str(generated_at_utc),
    )


def validate_control_assessment_payload(payload: Mapping[str, object]) -> list[str]:
    """Validate schema-v2 payload and report field/consistency issues."""
    errors: list[str] = []
    required = (
        "control_assessment_schema",
        "control_assessment_schema_version",
        "generated_at_utc",
        "source",
        "job_id",
        "job_status",
        "mode",
        "summary",
        "signals",
    )
    for key in required:
        if key not in payload:
            errors.append(f"Missing required key: '{key}'.")

    if payload.get("control_assessment_schema") != CONTROL_ASSESSMENT_SCHEMA:
        errors.append(
            "Field 'control_assessment_schema' must be "
            f"'{CONTROL_ASSESSMENT_SCHEMA}'."
        )
    if payload.get("control_assessment_schema_version") != CONTROL_ASSESSMENT_SCHEMA_VERSION:
        errors.append(
            "Field 'control_assessment_schema_version' must be "
            f"'{CONTROL_ASSESSMENT_SCHEMA_VERSION}'."
        )
    if not _is_valid_iso_datetime(payload.get("generated_at_utc")):
        errors.append("Field 'generated_at_utc' must be a valid ISO-8601 datetime.")
    for key in ("source", "job_id", "job_status", "mode"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Field '{key}' must be a non-empty string.")

    signals = payload.get("signals")
    if not isinstance(signals, list):
        errors.append("Field 'signals' must be an array.")
        signals = []
    normalized_signals = _normalize_signals(signals)

    for index, signal in enumerate(signals):
        if not isinstance(signal, dict):
            errors.append(f"Signal at index {index} must be an object.")
            continue
        state = _normalize_state(signal.get("state"))
        if state not in _SIGNAL_STATES:
            errors.append(f"Signal at index {index} has invalid state '{signal.get('state')}'.")
        evidence = signal.get("evidence")
        if evidence is not None and not isinstance(evidence, list):
            errors.append(f"Signal at index {index} has non-array 'evidence'.")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("Field 'summary' must be an object.")
        summary = {}
    counts = summary.get("counts")
    if not isinstance(counts, dict):
        errors.append("Field 'summary.counts' must be an object.")
        counts = {}
    for key in ("pass", "fail", "present", "unknown"):
        value = counts.get(key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"Field 'summary.counts.{key}' must be a non-negative integer.")
    overall_state = summary.get("overall_state")
    if _normalize_state(overall_state) not in _SIGNAL_STATES:
        errors.append("Field 'summary.overall_state' must be one of pass/fail/present/unknown.")
    failing_components = summary.get("failing_components")
    if not isinstance(failing_components, list) or any(
        not isinstance(item, str) or not item.strip() for item in failing_components
    ):
        errors.append("Field 'summary.failing_components' must be an array of non-empty strings.")

    expected_summary = _computed_summary_from_signals(normalized_signals)
    if isinstance(summary, dict):
        if summary.get("overall_state") != expected_summary["overall_state"]:
            errors.append("Field 'summary.overall_state' is inconsistent with 'signals'.")
        if summary.get("counts") != expected_summary["counts"]:
            errors.append("Field 'summary.counts' is inconsistent with 'signals'.")
        if summary.get("failing_components") != expected_summary["failing_components"]:
            errors.append("Field 'summary.failing_components' is inconsistent with 'signals'.")
    return errors


def compare_control_assessment_payloads(
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> list[str]:
    """Compare two payloads by canonical business fields and return mismatches."""
    left = normalized_assessment_fingerprint(baseline)
    right = normalized_assessment_fingerprint(candidate)
    mismatches: list[str] = []
    for key in ("job_id", "job_status", "mode", "summary", "signals"):
        if left.get(key) != right.get(key):
            mismatches.append(key)
    return mismatches


def build_control_assessment_consistency_report(
    payloads_by_source: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Build consistency report for multiple control-assessment payload sources."""
    normalized: dict[str, dict[str, object]] = {}
    for source, payload in payloads_by_source.items():
        normalized[source] = normalize_control_assessment_payload(
            payload,
            source_override=str(source),
        )

    source_names = sorted(normalized.keys())
    if not source_names:
        return {
            "ok": True,
            "source_count": 0,
            "sources": [],
            "mismatches": [],
            "fingerprint_sha256": "",
        }

    baseline_name = source_names[0]
    baseline = normalized[baseline_name]
    mismatches: list[dict[str, object]] = []
    for source in source_names[1:]:
        candidate = normalized[source]
        fields = compare_control_assessment_payloads(baseline, candidate)
        if fields:
            mismatches.append(
                {
                    "baseline": baseline_name,
                    "candidate": source,
                    "fields": fields,
                }
            )

    fingerprint = json.dumps(
        normalized_assessment_fingerprint(baseline),
        sort_keys=True,
        ensure_ascii=False,
    )
    return {
        "ok": len(mismatches) == 0,
        "source_count": len(source_names),
        "sources": source_names,
        "mismatches": mismatches,
        "fingerprint_sha256": hashlib.sha256(fingerprint.encode("utf-8")).hexdigest(),
    }


def normalized_assessment_fingerprint(payload: Mapping[str, object]) -> dict[str, object]:
    """Return canonical fingerprint map excluding schema metadata."""
    normalized = normalize_control_assessment_payload(payload)
    signals = normalized.get("signals", [])
    sorted_signals = sorted(
        (
            {
                "component_id": str(item.get("component_id", "")),
                "state": str(item.get("state", "unknown")),
                "reason": str(item.get("reason", "")),
                "evidence": sorted(str(entry) for entry in item.get("evidence", [])),
            }
            for item in signals
            if isinstance(item, dict)
        ),
        key=lambda item: item["component_id"],
    )
    summary = normalized.get("summary", {})
    return {
        "job_id": normalized.get("job_id", ""),
        "job_status": normalized.get("job_status", ""),
        "mode": normalized.get("mode", ""),
        "summary": summary,
        "signals": sorted_signals,
    }


def _normalize_signals(raw: object) -> list[dict[str, object]]:
    """Normalize control signal list to contract shape."""
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        component = _normalize_text(item.get("component_id"), default="unknown")
        state = _normalize_state(item.get("state"))
        reason = _normalize_text(item.get("reason"), default="")
        evidence = _normalize_evidence(item.get("evidence"))
        normalized.append(
            {
                "component_id": component,
                "state": state,
                "reason": reason,
                "evidence": evidence,
            }
        )
    return normalized


def _normalize_summary(
    raw: object,
    signals: list[dict[str, object]],
) -> dict[str, object]:
    """Normalize summary payload, filling from signals where needed."""
    computed = _computed_summary_from_signals(signals)
    computed_counts = dict(computed["counts"])
    failing_components = list(computed["failing_components"])
    computed_overall = str(computed["overall_state"])

    if not isinstance(raw, Mapping):
        return {
            "overall_state": computed_overall,
            "counts": computed_counts,
            "failing_components": failing_components,
        }

    counts_raw = raw.get("counts")
    counts = computed_counts.copy()
    if isinstance(counts_raw, Mapping):
        for key in counts.keys():
            value = counts_raw.get(key)
            if isinstance(value, int) and value >= 0:
                counts[key] = value

    failing_raw = raw.get("failing_components")
    failing = failing_components
    if isinstance(failing_raw, list):
        cleaned = [
            str(item).strip()
            for item in failing_raw
            if isinstance(item, str) and str(item).strip()
        ]
        failing = cleaned

    overall = _normalize_state(raw.get("overall_state"))
    return {
        "overall_state": overall if overall in _SIGNAL_STATES else computed_overall,
        "counts": counts,
        "failing_components": failing,
    }


def _computed_summary_from_signals(signals: list[dict[str, object]]) -> dict[str, object]:
    """Compute strict summary directly from normalized signal list."""
    counts = {"pass": 0, "fail": 0, "present": 0, "unknown": 0}
    failing_components: list[str] = []
    for signal in signals:
        state = _normalize_state(signal.get("state"))
        counts[state] = int(counts[state]) + 1
        if state == "fail":
            failing_components.append(str(signal.get("component_id", "unknown")))
    if counts["fail"] > 0:
        overall = "fail"
    elif counts["unknown"] > 0:
        overall = "unknown"
    elif counts["present"] > 0:
        overall = "present"
    else:
        overall = "pass"
    return {
        "overall_state": overall,
        "counts": counts,
        "failing_components": failing_components,
    }


def _normalize_evidence(raw: object) -> list[str]:
    """Normalize signal evidence as non-empty string list."""
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        text = _normalize_text(item, default="")
        if not text:
            continue
        values.append(text)
    return values


def _normalize_state(raw: object) -> str:
    """Normalize signal state to supported value set."""
    text = _normalize_text(raw, default="unknown").lower()
    if text in _SIGNAL_STATES:
        return text
    return "unknown"


def _normalize_text(raw: object, *, default: str) -> str:
    """Normalize arbitrary value to trimmed string with fallback."""
    text = str(raw).strip() if raw is not None else ""
    return text or default


def _is_valid_iso_datetime(raw: object) -> bool:
    """Return True when value is valid ISO datetime string."""
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
