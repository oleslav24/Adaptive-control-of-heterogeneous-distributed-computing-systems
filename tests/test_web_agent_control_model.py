"""Unit tests for agent control model and status transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
from threading import Lock

from project.experiments.integrity import write_artifact_integrity_file
from project.web.agent_control import (
    assess_job_control,
    build_control_assessment,
    default_enabled_components,
)


def test_control_assessment_all_components_enabled_is_stable() -> None:
    """All components enabled should keep all demo metrics at 100 and STABLE."""
    assessment = build_control_assessment(default_enabled_components())
    assert assessment.status == "STABLE"
    assert assessment.enabled_count == assessment.total_components == 7
    assert assessment.disabled_components == ()
    for value in assessment.metrics.values():
        assert value == 100.0


def test_control_assessment_single_disabled_component_drops_metrics_and_warns() -> None:
    """One disabled component should produce WARNING and expected metric drop profile."""
    enabled = default_enabled_components()
    enabled["policy"] = False
    assessment = build_control_assessment(enabled)

    assert assessment.status == "WARNING"
    assert assessment.disabled_components == ("policy",)
    assert assessment.metrics["quality"] == 88.0
    assert assessment.metrics["control"] == 75.0
    assert assessment.metrics["observability"] == 100.0
    assert assessment.metrics["resilience"] == 100.0
    assert assessment.metrics["recovery"] == 100.0


def test_control_assessment_critical_combo_autonomy_qgate_integrity_off() -> None:
    """Critical combination from original HTML scenario should switch status to CRITICAL."""
    enabled = default_enabled_components()
    enabled["autonomy"] = False
    enabled["qgate"] = False
    enabled["integrity"] = False

    assessment = build_control_assessment(enabled)
    assert assessment.status == "CRITICAL"
    assert assessment.critical_combo_triggered is True


def test_control_assessment_controlled_state_clamps_metrics_to_partial_recovery_band() -> None:
    """Controlled state should clamp all metrics into [55, 75] range."""
    enabled = default_enabled_components()
    enabled["autonomy"] = False
    enabled["qgate"] = False
    enabled["integrity"] = False

    assessment = build_control_assessment(enabled, controlled_state=True)
    assert assessment.status == "CONTROLLED_STATE"
    for value in assessment.metrics.values():
        assert 55.0 <= value <= 75.0


@dataclass
class _FakeJob:
    id: str
    status: str = "success"
    command: list[str] = field(
        default_factory=lambda: ["python", "-m", "project.experiments.run", "--publication-study"]
    )
    log_lines: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)


def _signal_map(job) -> dict[str, object]:
    assessment = assess_job_control(job)
    return {item.component_id: item for item in assessment.signals}


def test_assess_job_control_marks_missing_manifest_and_integrity_as_fail() -> None:
    """Completed publication-like run without artifacts should fail context/integrity gates."""
    job = _FakeJob(id="job-missing")
    signals = _signal_map(job)
    assert signals["context"].state == "fail"
    assert signals["integrity"].state == "fail"
    assert signals["qgate"].state == "fail"
    assessment = assess_job_control(job)
    assert assessment.summary.overall_state == "fail"
    assert "context" in assessment.summary.failing_components
    assert assessment.summary.counts["fail"] >= 1


def test_assess_job_control_uses_artifacts_for_pass_and_unknown_states() -> None:
    """Assessment should mark manifest/integrity pass and keep unknown signals as unknown."""
    workspace = (Path("outputs") / "__test_web_agent_control_model").resolve()
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        manifest_path = workspace / "run_manifest.json"
        manifest_path.write_text("{\"ok\": true}", encoding="utf-8")
        summary_path = workspace / "summary.json"
        summary_path.write_text("{\"value\": 1}", encoding="utf-8")
        validation_path = workspace / "summary_validation.json"
        validation_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        decision_trace_path = workspace / "decision_trace.json"
        decision_trace_path.write_text(
            json.dumps([{"event": "llm_policy_guard"}, {"event": "algorithm_policy"}]),
            encoding="utf-8",
        )
        integrity_path = workspace / "artifact_integrity.json"
        write_artifact_integrity_file(
            integrity_path,
            {
                "run_manifest_json": manifest_path,
                "summary_json": summary_path,
                "decision_trace_json": decision_trace_path,
            },
        )

        job = _FakeJob(
            id="job-artifacts",
            status="success",
            log_lines=[
                f"run_manifest_json: {manifest_path}",
                f"summary_json: {summary_path}",
                f"summary_validation_json: {validation_path}",
                f"decision_trace_json: {decision_trace_path}",
                f"artifact_integrity_json: {integrity_path}",
                "LLM enabled: False",
            ],
        )
        signals = _signal_map(job)
        assert signals["context"].state == "pass"
        assert signals["integrity"].state == "pass"
        assert signals["qgate"].state == "pass"
        assert signals["policy"].state == "pass"
        assert signals["autonomy"].state == "pass"
        assessment = assess_job_control(job)
        assert assessment.summary.overall_state == "pass"
        assert assessment.summary.counts["pass"] >= 5

        running_job = _FakeJob(
            id="job-running",
            status="running",
            command=["python", "-m", "project.experiments.run", "--single"],
            log_lines=[],
        )
        running_signals = _signal_map(running_job)
        assert running_signals["qgate"].state == "unknown"
        assert running_signals["context"].state == "unknown"
        running_assessment = assess_job_control(running_job)
        assert running_assessment.summary.overall_state in {"unknown", "present"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
