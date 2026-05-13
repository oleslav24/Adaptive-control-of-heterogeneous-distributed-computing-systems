"""Route handlers for job-specific API endpoints."""

from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Protocol
from urllib.parse import parse_qs

from project.web.i18n import tr
from project.web.route_responses import RouteResponse, json_response
from project.web.routing import first, lang_from_parsed


class _JobManagerLike(Protocol):
    """Minimal protocol for job lookup used by route helpers."""

    def get(self, job_id: str): ...


def build_job_data_response(
    parsed,
    job_manager: _JobManagerLike,
    *,
    payload_builder: Callable[[object, str], dict[str, object]],
) -> RouteResponse:
    """Create response payload for `/job-data` route."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    job_id = first(query, "id", "")
    job = job_manager.get(job_id)
    if job is None:
        return json_response(HTTPStatus.NOT_FOUND, {"error": tr(lang, "job_not_found")})
    return json_response(HTTPStatus.OK, payload_builder(job, lang))
