"""Unit tests for chapter10 operational control-health appendix builder."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from project.experiments.control_health import (
    build_control_health_assessment,
    control_health_payload,
    write_control_health_artifacts,
)
from project.experiments.integrity import write_artifact_integrity_file


def test_control_health_assessment_stable_when_all_gates_pass() -> None:
    """Complete chapter10/publication artifact set should yield stable health."""
    output_dir = _workspace_dir("control-health-stable")
    output_paths = _build_artifacts(output_dir, with_integrity=True)

    assessment = build_control_health_assessment(output_paths, mode="chapter10-study")
    payload = control_health_payload(assessment)

    assert assessment.overall_status == "STABLE"
    assert assessment.signal_counts["fail"] == 0
    assert payload["scope"] == "operational_quality_gate"
    assert payload["overall_status"] == "STABLE"
    assert len(payload["signals"]) == 7

    written = write_control_health_artifacts(output_dir, assessment)
    assert Path(written["chapter10_control_health_json"]).exists()
    assert Path(written["chapter10_control_health_md"]).exists()


def test_control_health_assessment_is_critical_when_integrity_missing() -> None:
    """Missing integrity reports should force CRITICAL operational status."""
    output_dir = _workspace_dir("control-health-critical")
    output_paths = _build_artifacts(output_dir, with_integrity=False)

    assessment = build_control_health_assessment(output_paths, mode="chapter10-study")
    lookup = {item.component_id: item for item in assessment.signals}

    assert assessment.overall_status == "CRITICAL"
    assert lookup["integrity"].state == "fail"
    assert lookup["qgate"].state in {"pass", "present"}


def _build_artifacts(output_dir: Path, *, with_integrity: bool) -> dict[str, str]:
    """Create minimal artifact set required by control-health assessment."""
    output_dir.mkdir(parents=True, exist_ok=True)

    publication_manifest = output_dir / "publication_manifest.json"
    publication_manifest.write_text("{}", encoding="utf-8")
    chapter10_manifest = output_dir / "chapter10_manifest.json"
    chapter10_manifest.write_text("{}", encoding="utf-8")

    raw_runs_json = output_dir / "raw_runs.json"
    raw_runs_json.write_text(
        json.dumps(
            [
                {
                    "method": "mas-llm",
                    "llm_guarded_decisions": 3,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    raw_runs_csv = output_dir / "raw_runs.csv"
    raw_runs_csv.write_text("method,llm_guarded_decisions\nmas-llm,3\n", encoding="utf-8")
    summary_csv = output_dir / "summary.csv"
    summary_csv.write_text("study_id,method,avg_latency_mean\nE5_llm_vs_algorithmic,mas-llm,1.0\n", encoding="utf-8")
    decision_trace_json = output_dir / "decision_trace.json"
    decision_trace_json.write_text(
        json.dumps([{"event": "llm_policy_guard"}], indent=2),
        encoding="utf-8",
    )

    summary_validation = output_dir / "summary_validation.json"
    summary_validation.write_text('{"ok": true}', encoding="utf-8")
    hypotheses_validation = output_dir / "hypotheses_validation.json"
    hypotheses_validation.write_text('{"ok": true}', encoding="utf-8")
    chapter10_validation = output_dir / "chapter10_package_validation.json"
    chapter10_validation.write_text('{"ok": true}', encoding="utf-8")
    claims_report = output_dir / "claims_report.json"
    claims_report.write_text('{"gate": {"ok": true}}', encoding="utf-8")
    literature_gate = output_dir / "chapter10_literature_evidence_gate.json"
    literature_gate.write_text('{"ok": true, "source_count": 2}', encoding="utf-8")

    output_paths: dict[str, str] = {
        "publication_publication_manifest_json": str(publication_manifest),
        "chapter10_manifest_json": str(chapter10_manifest),
        "publication_raw_runs_json": str(raw_runs_json),
        "publication_raw_runs_csv": str(raw_runs_csv),
        "publication_summary_csv": str(summary_csv),
        "publication_decision_trace_json": str(decision_trace_json),
        "publication_summary_validation_json": str(summary_validation),
        "publication_hypotheses_validation_json": str(hypotheses_validation),
        "chapter10_package_validation_json": str(chapter10_validation),
        "chapter10_claims_report_json": str(claims_report),
        "chapter10_literature_evidence_gate_json": str(literature_gate),
    }
    if with_integrity:
        publication_integrity_inputs = {
            "publication_publication_manifest_json": str(publication_manifest),
            "publication_raw_runs_json": str(raw_runs_json),
            "publication_raw_runs_csv": str(raw_runs_csv),
            "publication_summary_csv": str(summary_csv),
            "publication_decision_trace_json": str(decision_trace_json),
            "publication_summary_validation_json": str(summary_validation),
            "publication_hypotheses_validation_json": str(hypotheses_validation),
        }
        chapter10_integrity_inputs = {
            "chapter10_manifest_json": str(chapter10_manifest),
            "chapter10_package_validation_json": str(chapter10_validation),
            "chapter10_claims_report_json": str(claims_report),
            "chapter10_literature_evidence_gate_json": str(literature_gate),
        }
        publication_integrity = output_dir / "publication_artifact_integrity.json"
        chapter10_integrity = output_dir / "chapter10_artifact_integrity.json"
        output_paths["publication_artifact_integrity_json"] = write_artifact_integrity_file(
            publication_integrity,
            publication_integrity_inputs,
        )
        output_paths["chapter10_artifact_integrity_json"] = write_artifact_integrity_file(
            chapter10_integrity,
            chapter10_integrity_inputs,
        )
    return output_paths


def _workspace_dir(suffix: str) -> Path:
    """Create unique test workspace directory under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
