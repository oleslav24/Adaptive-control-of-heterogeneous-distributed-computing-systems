"""High-level request orchestration for web GET/POST handlers."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Callable

from project.web.dashboard_routes import build_dashboard_response
from project.web.diagnostics_routes import (
    build_job_bundle_response,
    build_job_diagnostics_response,
)
from project.web.dispatch import resolve_get_action, resolve_post_action
from project.web.file_routes import build_download_response, build_files_response
from project.web.i18n import tr
from project.web.job_page_routes import build_job_page_response
from project.web.job_routes import build_job_data_response
from project.web.route_responses import RouteResponse, text_response
from project.web.routing import lang_from_form, lang_from_parsed
from project.web.run_routes import build_start_run_response, build_stop_run_response


def build_get_response(
    parsed,
    job_manager,
    *,
    workspace_root: Path,
    default_config: str,
    payload_builder: Callable[[object, str], dict[str, object]],
) -> RouteResponse:
    """Build GET response for supported web routes."""
    action = resolve_get_action(parsed.path)
    if action == "dashboard":
        return build_dashboard_response(
            parsed,
            job_manager,
            workspace_root=workspace_root,
            default_config=default_config,
        )
    if action == "job":
        return build_job_page_response(parsed, job_manager)
    if action == "job_data":
        return build_job_data_response(
            parsed,
            job_manager,
            payload_builder=payload_builder,
        )
    if action == "job_diagnostics":
        return build_job_diagnostics_response(parsed, job_manager)
    if action == "job_bundle":
        return build_job_bundle_response(
            parsed,
            job_manager,
            workspace_root=workspace_root,
        )
    if action == "files":
        return build_files_response(parsed, workspace_root=workspace_root)
    if action == "download":
        return build_download_response(parsed, workspace_root=workspace_root)
    if action == "health":
        return text_response(HTTPStatus.OK, "ok")
    lang = lang_from_parsed(parsed)
    return text_response(HTTPStatus.NOT_FOUND, tr(lang, "not_found"))


def build_post_response(
    parsed,
    form: dict[str, list[str]],
    job_manager,
    *,
    workspace_root: Path,
    default_config: str,
) -> RouteResponse:
    """Build POST response for supported web routes."""
    action = resolve_post_action(parsed.path)
    if action == "run":
        return build_start_run_response(
            form,
            job_manager,
            workspace_root=workspace_root,
            default_config=default_config,
        )
    if action == "stop":
        return build_stop_run_response(form, job_manager)
    lang = lang_from_form(form)
    return text_response(HTTPStatus.NOT_FOUND, tr(lang, "not_found"))
