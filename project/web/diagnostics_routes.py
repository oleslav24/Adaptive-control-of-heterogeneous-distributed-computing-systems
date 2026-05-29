"""Route handlers for diagnostics JSON and bundle export endpoints."""

from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs

from project.web.diagnostics import (
    build_job_diagnostics,
    export_job_diagnostics_bundle,
    is_failure_like_status,
)
from project.web.agent_control import (
    assess_job_control,
    job_control_assessment_payload,
    parse_job_signals,
)
from project.web.control_assessment_contract import (
    build_control_assessment_consistency_report,
    normalize_control_assessment_payload,
    validate_control_assessment_payload,
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
    runtime_payload = job_control_assessment_payload(
        assess_job_control(job),
        source="diagnostics-route-runtime",
    )
    source_payloads: dict[str, dict[str, object]] = {"runtime": runtime_payload}
    artifact_payload = _load_job_control_assessment_artifact(job)
    if artifact_payload:
        source_payloads["job-artifact"] = normalize_control_assessment_payload(
            artifact_payload,
            fallback_job_id=str(getattr(job, "id", "")),
            fallback_job_status=str(getattr(job, "status", "")),
            source_override="job-artifact",
        )
    diagnostics["control_assessment"] = runtime_payload
    diagnostics["control_assessment_consistency"] = build_control_assessment_consistency_report(
        source_payloads
    )
    diagnostics["control_assessment_validation"] = {
        source: validate_control_assessment_payload(payload)
        for source, payload in source_payloads.items()
    }
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


def _load_job_control_assessment_artifact(job) -> dict[str, object]:
    """Load exported `control_assessment_json` artifact for diagnostics consistency check."""
    parsed = parse_job_signals(job)
    path = parsed.existing_artifacts.get("control_assessment_json", "").strip()
    if not path:
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload
