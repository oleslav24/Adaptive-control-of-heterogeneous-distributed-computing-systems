"""Agent controllability model and job-level quality-gate assessment helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Literal, Mapping, Protocol, Sequence

from project.experiments.integrity import verify_artifact_integrity_file


ControlStatus = Literal["STABLE", "WARNING", "CRITICAL", "CONTROLLED_STATE"]
ControlSignalState = Literal["pass", "fail", "present", "unknown"]


@dataclass(frozen=True, slots=True)
class ControlComponent:
    """Control component descriptor."""

    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ControlMetric:
    """Control metric descriptor."""

    id: str
    name: str
    baseline: float = 100.0


@dataclass(frozen=True, slots=True)
class ControlImpactProfile:
    """Configurable impact map used for controllability simulation."""

    components: tuple[ControlComponent, ...]
    metrics: tuple[ControlMetric, ...]
    impacts: dict[str, dict[str, float]]
    disable_order: tuple[str, ...]
    scenario_disable_order: tuple[str, ...]
    controlled_band: tuple[float, float] = (55.0, 75.0)
    demonstration_only: bool = True


@dataclass(frozen=True, slots=True)
class ControlAssessment:
    """Computed controllability snapshot for demo mode."""

    status: ControlStatus
    controlled_state: bool
    metrics: dict[str, float]
    enabled_components: dict[str, bool]
    disabled_components: tuple[str, ...]
    enabled_count: int
    total_components: int
    critical_combo_triggered: bool


@dataclass(frozen=True, slots=True)
class ControlSignal:
    """One component signal in real-job assessment mode."""

    component_id: str
    state: ControlSignalState
    reason: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ControlAssessmentSummary:
    """Aggregated signal summary for quick quality-gate interpretation."""

    overall_state: ControlSignalState
    counts: dict[str, int]
    failing_components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JobControlAssessment:
    """Control assessment for a real web job."""

    job_id: str
    job_status: str
    mode: str
    signals: tuple[ControlSignal, ...]
    summary: ControlAssessmentSummary


@dataclass(frozen=True, slots=True)
class ParsedJobSignals:
    """Snapshot of parsed job artifacts/log signals."""

    command_flags: frozenset[str]
    artifacts: dict[str, str]
    existing_artifacts: dict[str, str]
    log_lines: tuple[str, ...]
    llm_enabled: bool | None
    llm_source: str


class _JobLike(Protocol):
    """Minimal protocol for web job assessment."""

    id: str
    status: str
    command: list[str] | tuple[str, ...]
    log_lines: list[str]


DEFAULT_CRITICAL_COMBOS: tuple[tuple[str, str, str], ...] = (
    ("policy", "qgate", "integrity"),
    ("autonomy", "qgate", "integrity"),
)


DEMO_CONTROL_PROFILE = ControlImpactProfile(
    components=(
        ControlComponent(
            id="policy",
            name="Policy",
            description="Allowed behavior policy and guardrails.",
        ),
        ControlComponent(
            id="context",
            name="Context",
            description="Execution context and approved baseline continuity.",
        ),
        ControlComponent(
            id="logging",
            name="Logging",
            description="Action and decision logging.",
        ),
        ControlComponent(
            id="iteration",
            name="Iteration",
            description="One change to one verification discipline.",
        ),
        ControlComponent(
            id="qgate",
            name="Quality Gate",
            description="Quality checkpoint before propagation.",
        ),
        ControlComponent(
            id="autonomy",
            name="Autonomy Limits",
            description="Scope and autonomy restrictions.",
        ),
        ControlComponent(
            id="integrity",
            name="Integrity",
            description="Report, log, and artifact integrity checks.",
        ),
    ),
    metrics=(
        ControlMetric(id="quality", name="Quality"),
        ControlMetric(id="control", name="Control"),
        ControlMetric(id="observability", name="Observability"),
        ControlMetric(id="resilience", name="Resilience"),
        ControlMetric(id="recovery", name="Recovery"),
    ),
    impacts={
        "policy": {"quality": 12.0, "control": 25.0},
        "context": {"quality": 10.0, "resilience": 28.0, "recovery": 5.0},
        "logging": {"observability": 35.0, "recovery": 10.0},
        "iteration": {"quality": 12.0, "recovery": 18.0},
        "qgate": {"quality": 25.0, "recovery": 12.0},
        "autonomy": {"control": 30.0, "quality": 5.0},
        "integrity": {"observability": 22.0, "quality": 18.0},
    },
    disable_order=("autonomy", "qgate", "integrity", "policy", "context", "iteration", "logging"),
    scenario_disable_order=("autonomy", "qgate", "integrity"),
)


_ARTIFACT_PATH_RE = re.compile(r"^([a-zA-Z0-9_]+):\s*(.+)$")
_LLM_ENABLED_RE = re.compile(r"^LLM enabled:\s*(True|False)\s*$")
_LLM_SOURCE_RE = re.compile(r"^LLM source:\s*(.+)$")
_PUBLICATION_FLAGS = {
    "--publication-study",
    "--chapter10",
    "--paper-bundle",
    "--carbon-study",
}
_ITERATION_FLAGS = _PUBLICATION_FLAGS | {"--smoke", "--repro-check", "--replay-manifest"}


def default_enabled_components(
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
) -> dict[str, bool]:
    """Build all-enabled component map for profile."""
    return {component.id: True for component in profile.components}


def normalized_enabled_components(
    enabled_components: Mapping[str, bool],
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
) -> dict[str, bool]:
    """Normalize input component map against profile schema."""
    normalized = default_enabled_components(profile)
    for component in profile.components:
        if component.id in enabled_components:
            normalized[component.id] = bool(enabled_components[component.id])
    return normalized


def recompute_control_metrics(
    enabled_components: Mapping[str, bool],
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
    *,
    controlled_state: bool = False,
) -> dict[str, float]:
    """Recompute demo metrics from enabled/disabled control components."""
    normalized = normalized_enabled_components(enabled_components, profile)
    metrics = {metric.id: float(metric.baseline) for metric in profile.metrics}

    for component_id, is_enabled in normalized.items():
        if is_enabled:
            continue
        impact = profile.impacts.get(component_id, {})
        for metric_id, drop in impact.items():
            if metric_id not in metrics:
                continue
            metrics[metric_id] = max(0.0, metrics[metric_id] - float(drop))

    if controlled_state:
        band_min, band_max = profile.controlled_band
        for metric_id, value in list(metrics.items()):
            clamped = max(band_min, min(band_max, max(value, band_min)))
            metrics[metric_id] = clamped

    return metrics


def critical_combo_triggered(
    enabled_components: Mapping[str, bool],
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
) -> bool:
    """Check whether disabled components hit a critical combination."""
    normalized = normalized_enabled_components(enabled_components, profile)
    for first, second, third in DEFAULT_CRITICAL_COMBOS:
        if (not normalized.get(first, True)) and (not normalized.get(second, True)) and (
            not normalized.get(third, True)
        ):
            return True
    return False


def recompute_control_status(
    enabled_components: Mapping[str, bool],
    controlled_state: bool,
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
) -> ControlStatus:
    """Recompute process status from active controls."""
    if controlled_state:
        return "CONTROLLED_STATE"

    normalized = normalized_enabled_components(enabled_components, profile)
    disabled_count = sum(1 for value in normalized.values() if not value)
    if disabled_count == 0:
        return "STABLE"
    if critical_combo_triggered(normalized, profile) or disabled_count >= 4:
        return "CRITICAL"
    return "WARNING"


def build_control_assessment(
    enabled_components: Mapping[str, bool],
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
    *,
    controlled_state: bool = False,
) -> ControlAssessment:
    """Build full demo control assessment with metrics and status."""
    normalized = normalized_enabled_components(enabled_components, profile)
    metrics = recompute_control_metrics(normalized, profile, controlled_state=controlled_state)
    status = recompute_control_status(normalized, controlled_state, profile)
    disabled_components = tuple(
        component.id for component in profile.components if not normalized.get(component.id, True)
    )
    return ControlAssessment(
        status=status,
        controlled_state=bool(controlled_state),
        metrics=metrics,
        enabled_components=normalized,
        disabled_components=disabled_components,
        enabled_count=len(profile.components) - len(disabled_components),
        total_components=len(profile.components),
        critical_combo_triggered=critical_combo_triggered(normalized, profile),
    )


def next_component_to_disable(
    enabled_components: Mapping[str, bool],
    profile: ControlImpactProfile = DEMO_CONTROL_PROFILE,
) -> str | None:
    """Return next component id from deterministic disable order."""
    normalized = normalized_enabled_components(enabled_components, profile)
    for component_id in profile.disable_order:
        if normalized.get(component_id, True):
            return component_id
    return None


def demo_profile_payload(profile: ControlImpactProfile = DEMO_CONTROL_PROFILE) -> dict[str, object]:
    """Serialize demo profile for JS rendering."""
    return {
        "components": [
            {
                "id": component.id,
                "name": component.name,
                "description": component.description,
            }
            for component in profile.components
        ],
        "metrics": [
            {
                "id": metric.id,
                "name": metric.name,
                "baseline": metric.baseline,
            }
            for metric in profile.metrics
        ],
        "impacts": profile.impacts,
        "disable_order": list(profile.disable_order),
        "scenario_disable_order": list(profile.scenario_disable_order),
        "critical_combos": [list(combo) for combo in DEFAULT_CRITICAL_COMBOS],
        "controlled_band": [profile.controlled_band[0], profile.controlled_band[1]],
        "demonstration_only": profile.demonstration_only,
    }


def parse_job_signals(job: _JobLike) -> ParsedJobSignals:
    """Extract command/log/artifact signals from web job object."""
    lines = _snapshot_lines(job)
    artifacts: dict[str, str] = {}
    llm_enabled: bool | None = None
    llm_source = ""

    for raw_line in lines:
        line = str(raw_line).strip()
        match = _ARTIFACT_PATH_RE.match(line)
        if match is not None:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key and value:
                artifacts[key] = value

        llm_enabled_match = _LLM_ENABLED_RE.match(line)
        if llm_enabled_match is not None:
            llm_enabled = llm_enabled_match.group(1) == "True"

        llm_source_match = _LLM_SOURCE_RE.match(line)
        if llm_source_match is not None:
            llm_source = llm_source_match.group(1).strip().lower()

    existing_artifacts = {
        key: value for key, value in artifacts.items() if Path(value).exists() and Path(value).is_file()
    }
    command_flags = frozenset(
        str(token).strip().lower()
        for token in getattr(job, "command", [])
        if str(token).strip().startswith("--")
    )
    return ParsedJobSignals(
        command_flags=command_flags,
        artifacts=artifacts,
        existing_artifacts=existing_artifacts,
        log_lines=tuple(lines),
        llm_enabled=llm_enabled,
        llm_source=llm_source,
    )


def assess_job_control(job: _JobLike) -> JobControlAssessment:
    """Build real-job control assessment from available artifacts/signals."""
    status = str(getattr(job, "status", "")).strip().lower()
    terminal = status in {"success", "failed", "timeout", "stopped"}
    parsed = parse_job_signals(job)
    publication_like = bool(parsed.command_flags.intersection(_PUBLICATION_FLAGS))

    context_signal = _assess_context_signal(parsed, terminal)
    integrity_signal = _assess_integrity_signal(parsed, terminal)
    logging_signal = _assess_logging_signal(parsed, terminal)
    iteration_signal = _assess_iteration_signal(parsed, terminal)
    qgate_signal = _assess_qgate_signal(parsed, terminal, publication_like)
    autonomy_signal = _assess_autonomy_signal(parsed)
    policy_signal = _assess_policy_signal(parsed, autonomy_signal)

    signals = (
        policy_signal,
        context_signal,
        logging_signal,
        iteration_signal,
        qgate_signal,
        autonomy_signal,
        integrity_signal,
    )
    return JobControlAssessment(
        job_id=str(getattr(job, "id", "")),
        job_status=status,
        mode="real-job",
        signals=signals,
        summary=summarize_control_signals(signals),
    )


def job_control_assessment_payload(assessment: JobControlAssessment) -> dict[str, object]:
    """Serialize job control assessment dataclasses into JSON-friendly payload."""
    return {
        "job_id": assessment.job_id,
        "job_status": assessment.job_status,
        "mode": assessment.mode,
        "summary": {
            "overall_state": assessment.summary.overall_state,
            "counts": dict(assessment.summary.counts),
            "failing_components": list(assessment.summary.failing_components),
        },
        "signals": [
            {
                "component_id": signal.component_id,
                "state": signal.state,
                "reason": signal.reason,
                "evidence": list(signal.evidence),
            }
            for signal in assessment.signals
        ],
    }


def summarize_control_signals(signals: Sequence[ControlSignal]) -> ControlAssessmentSummary:
    """Aggregate component-level control signals into one compact summary."""
    counts: dict[str, int] = {"pass": 0, "fail": 0, "present": 0, "unknown": 0}
    failing_components: list[str] = []
    for signal in signals:
        state = str(signal.state).strip().lower()
        if state in counts:
            counts[state] += 1
        else:
            counts["unknown"] += 1
        if state == "fail":
            failing_components.append(signal.component_id)

    if counts["fail"] > 0:
        overall: ControlSignalState = "fail"
    elif counts["unknown"] > 0:
        overall = "unknown"
    elif counts["present"] > 0:
        overall = "present"
    else:
        overall = "pass"

    return ControlAssessmentSummary(
        overall_state=overall,
        counts=counts,
        failing_components=tuple(failing_components),
    )


def _snapshot_lines(job: _JobLike) -> list[str]:
    """Read job log lines with lock if available."""
    lock = getattr(job, "_lock", None)
    if lock is None:
        return list(getattr(job, "log_lines", []))
    try:
        with lock:
            return list(getattr(job, "log_lines", []))
    except Exception:  # noqa: BLE001
        return list(getattr(job, "log_lines", []))


def _assess_context_signal(parsed: ParsedJobSignals, terminal: bool) -> ControlSignal:
    """Assess context continuity via manifest artifacts."""
    manifest_keys = [key for key in parsed.artifacts if "manifest" in key.lower()]
    existing_manifests = [key for key in parsed.existing_artifacts if "manifest" in key.lower()]

    if existing_manifests:
        return ControlSignal(
            component_id="context",
            state="pass",
            reason="Manifest artifacts detected.",
            evidence=tuple(sorted(existing_manifests)),
        )
    if manifest_keys:
        return ControlSignal(
            component_id="context",
            state="fail",
            reason="Manifest paths were reported but files are missing.",
            evidence=tuple(sorted(manifest_keys)),
        )
    if terminal:
        return ControlSignal(
            component_id="context",
            state="fail",
            reason="No manifest artifacts were produced.",
        )
    return ControlSignal(
        component_id="context",
        state="unknown",
        reason="Manifest signals are not available yet.",
    )


def _assess_integrity_signal(parsed: ParsedJobSignals, terminal: bool) -> ControlSignal:
    """Assess integrity checks via artifact integrity payload."""
    integrity_keys = [
        key
        for key in parsed.artifacts
        if "artifact_integrity" in key.lower() or key.lower().endswith("integrity_json")
    ]
    for key in integrity_keys:
        candidate = parsed.existing_artifacts.get(key, "").strip()
        if not candidate:
            continue
        ok, errors = verify_artifact_integrity_file(candidate)
        if ok:
            return ControlSignal(
                component_id="integrity",
                state="pass",
                reason="Artifact integrity report is present and valid.",
                evidence=(key,),
            )
        error = errors[0] if errors else "Integrity verification failed."
        return ControlSignal(
            component_id="integrity",
            state="fail",
            reason=error,
            evidence=(key,),
        )

    if integrity_keys:
        return ControlSignal(
            component_id="integrity",
            state="fail",
            reason="Integrity report path was reported but file is missing.",
            evidence=tuple(sorted(integrity_keys)),
        )
    if terminal:
        return ControlSignal(
            component_id="integrity",
            state="fail",
            reason="No integrity report was produced.",
        )
    return ControlSignal(
        component_id="integrity",
        state="unknown",
        reason="Integrity signals are not available yet.",
    )


def _assess_logging_signal(parsed: ParsedJobSignals, terminal: bool) -> ControlSignal:
    """Assess logging observability via log lines and telemetry artifacts."""
    log_line_count = len(parsed.log_lines)
    telemetry_keys = tuple(
        key
        for key in parsed.existing_artifacts
        if key
        in {
            "history_csv",
            "history_json",
            "events_csv",
            "events_json",
            "decision_trace_csv",
            "decision_trace_json",
            "summary_json",
        }
    )

    if log_line_count > 0 and telemetry_keys:
        return ControlSignal(
            component_id="logging",
            state="pass",
            reason="Logs and telemetry artifacts are available.",
            evidence=telemetry_keys,
        )
    if log_line_count > 0:
        return ControlSignal(
            component_id="logging",
            state="present",
            reason="Runtime logs are present but telemetry artifacts are incomplete.",
        )
    if terminal:
        return ControlSignal(
            component_id="logging",
            state="fail",
            reason="No logs were captured for completed job.",
        )
    return ControlSignal(
        component_id="logging",
        state="unknown",
        reason="Job is running and no log signals are available yet.",
    )


def _assess_iteration_signal(parsed: ParsedJobSignals, terminal: bool) -> ControlSignal:
    """Assess iteration discipline from run mode and gate commands."""
    has_gate_mode = bool(parsed.command_flags.intersection(_ITERATION_FLAGS))
    if not has_gate_mode:
        return ControlSignal(
            component_id="iteration",
            state="unknown",
            reason="Run mode does not expose explicit iteration gates.",
        )
    if terminal:
        return ControlSignal(
            component_id="iteration",
            state="pass",
            reason="Gate-oriented run mode completed with deterministic workflow.",
            evidence=tuple(sorted(parsed.command_flags.intersection(_ITERATION_FLAGS))),
        )
    return ControlSignal(
        component_id="iteration",
        state="present",
        reason="Gate-oriented run mode is active.",
    )


def _assess_qgate_signal(
    parsed: ParsedJobSignals,
    terminal: bool,
    publication_like: bool,
) -> ControlSignal:
    """Assess quality gate using publication/chapter10 validation outputs."""
    validation_keys = [
        key
        for key in parsed.existing_artifacts
        if "validation" in key.lower() or key.lower().startswith("claims_report")
    ]
    for key in validation_keys:
        candidate = parsed.existing_artifacts.get(key, "")
        if not candidate:
            continue
        verdict = _read_json_ok_field(candidate)
        if verdict is True:
            return ControlSignal(
                component_id="qgate",
                state="pass",
                reason="Validation gate reports successful checks.",
                evidence=(key,),
            )
        if verdict is False:
            return ControlSignal(
                component_id="qgate",
                state="fail",
                reason="Validation gate reported a failed check.",
                evidence=(key,),
            )

    if publication_like and terminal:
        return ControlSignal(
            component_id="qgate",
            state="fail",
            reason="Publication-like run completed without quality-gate artifacts.",
        )
    if publication_like:
        return ControlSignal(
            component_id="qgate",
            state="present",
            reason="Publication-like run is in progress; waiting for quality-gate artifacts.",
        )
    return ControlSignal(
        component_id="qgate",
        state="unknown",
        reason="Quality-gate artifacts are not expected for this run mode.",
    )


def _assess_autonomy_signal(parsed: ParsedJobSignals) -> ControlSignal:
    """Assess autonomy restrictions from command flags and LLM runtime info."""
    if "--disable-llm" in parsed.command_flags:
        return ControlSignal(
            component_id="autonomy",
            state="pass",
            reason="LLM autonomy is explicitly disabled.",
            evidence=("--disable-llm",),
        )
    if parsed.llm_enabled is False:
        return ControlSignal(
            component_id="autonomy",
            state="pass",
            reason="Runtime indicates LLM is disabled.",
            evidence=("LLM enabled: False",),
        )
    if parsed.llm_enabled is True:
        source = parsed.llm_source or "unknown"
        return ControlSignal(
            component_id="autonomy",
            state="present",
            reason="LLM is enabled and constrained by configured provider.",
            evidence=(f"llm_source={source}",),
        )
    return ControlSignal(
        component_id="autonomy",
        state="unknown",
        reason="Autonomy constraints cannot be inferred from current job signals.",
    )


def _assess_policy_signal(
    parsed: ParsedJobSignals,
    autonomy_signal: ControlSignal,
) -> ControlSignal:
    """Assess policy guard evidence using decision-trace artifacts."""
    decision_keys = tuple(
        key
        for key in parsed.existing_artifacts
        if key in {"decision_trace_csv", "decision_trace_json"}
    )
    if decision_keys:
        guard_count = _count_llm_guard_events(parsed.existing_artifacts)
        if guard_count > 0:
            return ControlSignal(
                component_id="policy",
                state="pass",
                reason="Decision trace contains LLM policy-guard events.",
                evidence=decision_keys,
            )
        return ControlSignal(
            component_id="policy",
            state="present",
            reason="Decision trace is present but guard events were not found.",
            evidence=decision_keys,
        )

    if autonomy_signal.state == "pass":
        return ControlSignal(
            component_id="policy",
            state="pass",
            reason="LLM autonomy is disabled, policy risk is bounded.",
        )
    if parsed.llm_enabled is True:
        return ControlSignal(
            component_id="policy",
            state="fail",
            reason="LLM is enabled but no decision trace artifacts were produced.",
        )
    return ControlSignal(
        component_id="policy",
        state="unknown",
        reason="Policy-guard evidence is not available yet.",
    )


def _count_llm_guard_events(artifacts: Mapping[str, str]) -> int:
    """Count `llm_policy_guard` events in decision-trace JSON when available."""
    path = artifacts.get("decision_trace_json", "")
    if not path:
        return 0
    payload = _read_json(path)
    if not isinstance(payload, list):
        return 0
    count = 0
    for item in payload:
        if not isinstance(item, dict):
            continue
        if str(item.get("event", "")).strip() == "llm_policy_guard":
            count += 1
    return count


def _read_json_ok_field(path: str) -> bool | None:
    """Read optional `ok` field from JSON payload."""
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    value = payload.get("ok")
    if isinstance(value, bool):
        return value
    return None


def _read_json(path: str) -> object:
    """Load JSON payload with defensive fallback."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
