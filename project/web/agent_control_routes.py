"""Route handlers for agent control / quality-gate page."""

from __future__ import annotations

from http import HTTPStatus
from typing import Protocol
from urllib.parse import parse_qs

from project.web.agent_control import assess_job_control, demo_profile_payload
from project.web.agent_control_views import build_agent_control_html
from project.web.route_responses import RouteResponse, html_response
from project.web.routing import first, lang_from_parsed


class _AgentControlJobManager(Protocol):
    """Minimal job-manager protocol used by agent control page."""

    def list_jobs(self): ...

    def get(self, job_id: str): ...


def build_agent_control_response(parsed, job_manager: _AgentControlJobManager) -> RouteResponse:
    """Build `/agent-control` page response."""
    lang = lang_from_parsed(parsed)
    query = parse_qs(parsed.query)
    assess_mode = first(query, "assess", "demo").strip().lower()
    requested_job_id = first(query, "id", "").strip()

    jobs = list(job_manager.list_jobs())
    selected_job = None
    assessment = None
    assessment_message = ""

    if assess_mode == "latest":
        selected_job = jobs[0] if jobs else None
        if selected_job is not None:
            assessment = assess_job_control(selected_job)
        else:
            assessment_message = "No jobs available yet."
    elif assess_mode in {"latest-terminal", "latest_terminal"}:
        selected_job = _latest_terminal_job(jobs)
        if selected_job is not None:
            assessment = assess_job_control(selected_job)
        else:
            assessment_message = "No completed jobs available yet."
    elif assess_mode in {"job", "id"}:
        if requested_job_id:
            selected_job = job_manager.get(requested_job_id)
            if selected_job is None:
                assessment_message = f"Job '{requested_job_id}' not found."
            else:
                assessment = assess_job_control(selected_job)
        else:
            assessment_message = "Provide job id to assess a specific run."

    html = build_agent_control_html(
        lang=lang,
        demo_profile=demo_profile_payload(),
        assessment=assessment,
        assessment_mode=assess_mode,
        requested_job_id=requested_job_id,
        available_jobs=jobs,
        assessment_message=assessment_message,
    )
    return html_response(HTTPStatus.OK, html)


def _latest_terminal_job(jobs: list[object]) -> object | None:
    """Return first job with terminal status from manager list order."""
    for job in jobs:
        status = str(getattr(job, "status", "")).strip().lower()
        if status in {"success", "failed", "timeout", "stopped"}:
            return job
    return None
