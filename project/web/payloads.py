"""Payload builders for web API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Protocol

from project.agents import ResearcherAgent
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
    status_details = str(job.status_details or "").strip()
    if not status_details:
        status_details = _default_status_details(job)
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
        "command": job.command_text(),
        "log_text": "\n".join(lines),
        "metrics": metrics,
        "insights": insights,
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

