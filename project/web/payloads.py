"""Payload builders for web API endpoints."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol

from project.agents import ResearcherAgent
from project.evidence_claims import build_runtime_claims
from project.literature_evidence import (
    build_query_from_metrics,
    search_literature,
    validate_evidence_items,
)
from project.web.i18n import (
    ALGORITHM_LABELS,
    SCENARIO_LABELS,
    catalog_label,
    tr,
)
from project.web.job_views import fmt_dt, status_badge
from project.web.metrics_parser import extract_metrics_from_logs


RESEARCHER_AGENT = ResearcherAgent()


class _JobPayloadLike(Protocol):
    """Minimal job protocol for API payload serialization."""

    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    return_code: int | None
    timeout_seconds: int | None
    timed_out: bool
    status_details: str
    log_lines: list[str]
    _lock: Lock

    def command_text(self) -> str: ...


def job_payload(job: _JobPayloadLike, lang: str) -> dict[str, object]:
    """Serialize job state for live UI polling endpoint."""
    with job._lock:
        lines = list(job.log_lines)
    metrics = extract_metrics_from_logs(lines)
    analysis_metrics: dict[str, list[float | int]] = {
        "time": list(metrics.get("time", [])),
        "queue": list(metrics.get("queue", [])),
        "completed": list(metrics.get("completed", [])),
        "latency": list(metrics.get("latency", [])),
        "throughput": list(metrics.get("throughput", [])),
        "avg_load": list(metrics.get("avg_load", [])),
    }
    run_segments = metrics.get("runs", [])
    last_run: dict[str, object] | None = None
    if isinstance(run_segments, list):
        for run in run_segments:
            if not isinstance(run, dict):
                continue
            scenario_token = str(run.get("scenario", "")).strip()
            algorithm_token = str(run.get("algorithm", "")).strip()
            run["scenario_label"] = (
                catalog_label(SCENARIO_LABELS, lang, scenario_token, scenario_token)
                if scenario_token
                else tr(lang, "unknown")
            )
            run["algorithm_label"] = (
                catalog_label(ALGORITHM_LABELS, lang, algorithm_token, algorithm_token)
                if algorithm_token
                else tr(lang, "unknown")
            )
    if isinstance(run_segments, list) and run_segments:
        last = run_segments[-1]
        if isinstance(last, dict):
            last_run = last
            analysis_metrics = {
                "time": list(last.get("time", [])),
                "queue": list(last.get("queue", [])),
                "completed": list(last.get("completed", [])),
                "latency": list(last.get("latency", [])),
                "throughput": list(last.get("throughput", [])),
                "avg_load": list(last.get("avg_load", [])),
            }
    insights = RESEARCHER_AGENT.analyze_metrics(
        analysis_metrics,
        lang=lang,
        status=job.status,
        max_items=6,
    )
    literature_query = build_query_from_metrics(
        analysis_metrics,
        scenario=str((last_run or {}).get("scenario", "")),
        algorithm=str((last_run or {}).get("algorithm", "")),
    )
    literature_evidence = search_literature(
        literature_query,
        top_k=5,
        min_score=0.03,
    )
    literature_gate: dict[str, object] = {
        "ok": False,
        "errors": [],
        "source_count": 0,
        "min_sources": 2,
        "skipped": False,
    }
    if not literature_evidence.get("available", False):
        literature_gate["skipped"] = True
    else:
        validation = validate_evidence_items(literature_evidence.get("items", []), min_sources=2)
        literature_gate.update(validation)
    claims_payload = build_runtime_claims(
        analysis_metrics,
        literature_evidence,
        scenario=str((last_run or {}).get("scenario", "")),
        algorithm=str((last_run or {}).get("algorithm", "")),
        min_sources_per_claim=2,
        min_score=0.03,
    )
    status_details = str(job.status_details or "").strip()
    if not status_details:
        status_details = _default_status_details(job)
    command_text = job.command_text()
    carbon_outcomes = _carbon_outcomes(lines, command_text)
    return {
        "id": job.id,
        "status": job.status,
        "status_badge_html": status_badge(job.status, lang),
        "status_details": status_details,
        "started_at": fmt_dt(job.started_at),
        "finished_at": fmt_dt(job.finished_at),
        "return_code": job.return_code,
        "timeout_seconds": job.timeout_seconds,
        "timed_out": bool(job.timed_out),
        "command": command_text,
        "log_text": "\n".join(lines),
        "metrics": metrics,
        "insights": insights,
        "carbon_outcomes": carbon_outcomes,
        "literature_evidence": literature_evidence,
        "literature_evidence_gate": literature_gate,
        "claims": claims_payload["claims"],
        "claims_gate": claims_payload["gate"],
        "lang": lang,
    }


def _default_status_details(job: _JobPayloadLike) -> str:
    """Build fallback status detail text when explicit detail is not set."""
    if job.status == "timeout":
        if job.timeout_seconds is None:
            return "timeout"
        return f"timeout>{int(job.timeout_seconds)}s"
    if job.status == "stopped":
        return "stop-requested"
    if job.status == "success":
        return "completed"
    if job.status == "failed":
        if job.return_code is None:
            return "failed"
        return f"exit-code:{job.return_code}"
    return "-"


def _carbon_outcomes(lines: list[str], command_text: str) -> dict[str, object] | None:
    """Build carbon-study outcome payload from generated artifact CSV."""
    command = str(command_text or "")
    if "--carbon-study" not in command and "--publication-study" not in command:
        return None

    csv_path = _extract_artifact_path(lines, "carbon_summary_csv")
    if not csv_path:
        return {"available": False, "reason": "pending-artifact"}
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        return {"available": False, "reason": "missing-artifact", "path": str(path)}

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({str(k): str(v) for k, v in row.items() if k is not None})
    if not rows:
        return {"available": False, "reason": "empty-artifact", "path": str(path)}

    best = _best_carbon_row(rows)
    baseline = _baseline_row(rows)
    if best is None:
        return {"available": False, "reason": "invalid-artifact", "path": str(path)}
    if baseline is None:
        baseline = best

    return {
        "available": True,
        "path": str(path),
        "best_method": best.get("method_label") or best.get("method") or "unknown",
        "baseline_method": baseline.get("method_label") or baseline.get("method") or "min-load",
        "co2_per_task_lb": _as_float(best.get("co2_per_completed_task_lb_mean")),
        "co2_total_lb": _as_float(best.get("co2_total_lb_mean")),
        "latency_delta_vs_baseline": _as_float(best.get("delta_latency_vs_min_load")),
        "throughput_delta_vs_baseline": _as_float(best.get("delta_throughput_vs_min_load")),
        "co2_reduction_vs_baseline_pct": _as_float(
            best.get("co2_per_task_reduction_vs_min_load_pct")
        ),
    }


def _extract_artifact_path(lines: list[str], key: str) -> str | None:
    """Extract latest '<key>: <path>' line from job log output."""
    prefix = f"{key}:"
    for line in reversed(lines):
        text = str(line).strip()
        if not text.startswith(prefix):
            continue
        candidate = text[len(prefix) :].strip()
        if candidate:
            return candidate
    return None


def _best_carbon_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    """Pick row with minimal per-task CO2 value."""
    best_row: dict[str, str] | None = None
    best_value: float | None = None
    for row in rows:
        value = _as_float(row.get("co2_per_completed_task_lb_mean"))
        if value is None:
            continue
        if best_value is None or value < best_value:
            best_row = row
            best_value = value
    return best_row


def _baseline_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
    """Pick min-load baseline row from carbon summary."""
    for row in rows:
        if str(row.get("method", "")).strip() == "min-load":
            return row
    return rows[0] if rows else None


def _as_float(raw: str | None) -> float | None:
    """Parse float from optional string."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

