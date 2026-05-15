"""Route handlers for diagnostics JSON and bundle export endpoints."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs

from project.web.diagnostics import (
    build_job_diagnostics,
    export_job_diagnostics_bundle,
    is_failure_like_status,
)
from project.web.i18n import tr
from project.web.route_responses import RouteResponse, json_response, text_response
from project.web.routing import first, lang_from_parsed


class _DiagnosticsJobManager(Protocol):
    """Minimal protocol for diagnostics route dependencies."""

    def get(self, job_id: str): ...


def build_job_diagnostics_response(
    parsed,
    job_manager: _DiagnosticsJobManager,
) -> RouteResponse:
    """Return JSON diagnostics payload for one job."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    job_id = first(query, "id", "")
    job = job_manager.get(job_id)
    if job is None:
        return json_response(HTTPStatus.NOT_FOUND, {"error": tr(lang, "job_not_found")})

    diagnostics = build_job_diagnostics(job).to_payload()
    diagnostics["can_export_bundle"] = is_failure_like_status(job.status)
    diagnostics["lang"] = lang
    return json_response(HTTPStatus.OK, diagnostics)


def build_job_bundle_response(
    parsed,
    job_manager: _DiagnosticsJobManager,
    *,
    workspace_root: Path,
) -> RouteResponse:
    """Export diagnostics bundle and return zip response."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    job_id = first(query, "id", "")
    job = job_manager.get(job_id)
    if job is None:
        return text_response(HTTPStatus.NOT_FOUND, tr(lang, "job_not_found"))
    if not is_failure_like_status(job.status):
        return text_response(
            HTTPStatus.BAD_REQUEST,
            tr(lang, "diagnostics_bundle_unavailable"),
        )

    bundle_path = export_job_diagnostics_bundle(job=job, workspace_root=workspace_root)
    data = bundle_path.read_bytes()
    return RouteResponse(
        status=HTTPStatus.OK,
        content_type="application/zip",
        body=data,
        headers={
            "Content-Disposition": f"attachment; filename={bundle_path.name}",
            "Content-Length": str(len(data)),
            "Cache-Control": "no-store",
        },
    )
