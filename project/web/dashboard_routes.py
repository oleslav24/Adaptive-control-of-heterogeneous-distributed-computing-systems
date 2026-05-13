"""Route handlers for the dashboard page."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Protocol

from project.web.dashboard_views import build_dashboard_html
from project.web.route_responses import RouteResponse, html_response
from project.web.routing import lang_from_parsed


class _DashboardJobManager(Protocol):
    """Minimal protocol for dashboard route dependencies."""

    def list_jobs(self): ...


def build_dashboard_response(
    parsed,
    job_manager: _DashboardJobManager,
    *,
    workspace_root: Path,
    default_config: str,
) -> RouteResponse:
    """Create response payload for dashboard route (`/`)."""
    lang = lang_from_parsed(parsed)
    jobs = job_manager.list_jobs()
    html = build_dashboard_html(
        lang,
        jobs,
        workspace_root=workspace_root,
        default_config=default_config,
    )
    return html_response(HTTPStatus.OK, html)
