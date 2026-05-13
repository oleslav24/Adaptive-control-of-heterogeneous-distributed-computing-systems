"""Route handlers for job page HTML endpoint."""

from __future__ import annotations

from http import HTTPStatus
from typing import Protocol
from urllib.parse import parse_qs

from project.web.i18n import tr
from project.web.job_page_views import build_job_page_html
from project.web.route_responses import RouteResponse, html_response, text_response
from project.web.routing import first, lang_from_parsed


class _JobPageManager(Protocol):
    """Minimal protocol for job page route dependencies."""

    def get(self, job_id: str): ...


def build_job_page_response(parsed, job_manager: _JobPageManager) -> RouteResponse:
    """Create response payload for job details page route (`/job`)."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    job_id = first(query, "id", "")
    job = job_manager.get(job_id)
    if job is None:
        return text_response(HTTPStatus.NOT_FOUND, tr(lang, "job_not_found"))
    html = build_job_page_html(job, lang)
    return html_response(HTTPStatus.OK, html)
