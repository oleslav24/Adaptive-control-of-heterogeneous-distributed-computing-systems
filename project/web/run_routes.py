"""Route handlers for run/start and run/stop actions."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Protocol

from project.web.commands import build_run_command
from project.web.i18n import tr
from project.web.route_responses import RouteResponse, redirect_response, text_response
from project.web.routing import first, lang_from_form, with_lang


class _RunnableJobManager(Protocol):
    """Minimal protocol for run control route helpers."""

    def create(self, *, command: list[str], cwd: Path): ...

    def get(self, job_id: str): ...


def build_start_run_response(
    form: dict[str, list[str]],
    job_manager: _RunnableJobManager,
    *,
    workspace_root: Path,
    default_config: str,
) -> RouteResponse:
    """Create redirect response for `/run` action."""
    lang = lang_from_form(form)
    command = build_run_command(form, default_config=default_config)
    job = job_manager.create(command=command, cwd=workspace_root)
    return redirect_response(with_lang("/job", lang, id=job.id))


def build_stop_run_response(
    form: dict[str, list[str]],
    job_manager: _RunnableJobManager,
) -> RouteResponse:
    """Create response payload for `/stop` action."""
    lang = lang_from_form(form)
    job_id = first(form, "id", "")
    job = job_manager.get(job_id)
    if job is None:
        return text_response(HTTPStatus.NOT_FOUND, tr(lang, "job_not_found"))
    stopped = job.stop()
    if stopped:
        job.status = "stopped"
        job.append_log("[web-ui] stop requested.")
    return redirect_response(with_lang("/job", lang, id=job_id))
