"""Unit tests for diagnostics route handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from uuid import uuid4
import zipfile

from project.web.diagnostics_routes import (
    build_job_bundle_response,
    build_job_diagnostics_response,
)


@dataclass
class _FakeJob:
    id: str
    status: str = "failed"
    status_details: str = "exit-code:1"
    started_at: datetime | None = datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = datetime(2026, 5, 14, 10, 1, tzinfo=timezone.utc)
    return_code: int | None = 1
    timeout_seconds: int | None = 3600
    timed_out: bool = False
    log_lines: list[str] = field(default_factory=lambda: ["line-1", "line-2"])
    _lock: Lock = field(default_factory=Lock)
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)


class _FakeJobManager:
    def __init__(self, jobs: dict[str, _FakeJob] | None = None) -> None:
        self._jobs = jobs or {}

    def get(self, job_id: str) -> _FakeJob | None:
        return self._jobs.get(job_id)


def _workspace_dir(name: str) -> Path:
    target = (Path("outputs") / "test-suite" / f"{name}-{uuid4().hex[:8]}").resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_build_job_diagnostics_response_not_found() -> None:
    """Diagnostics endpoint should return 404 JSON for unknown job."""
    response = build_job_diagnostics_response(urlparse("/job-diagnostics?id=missing"), _FakeJobManager())
    assert response.status.value == 404
    assert b"Job not found." in response.body


def test_build_job_diagnostics_response_returns_payload() -> None:
    """Diagnostics endpoint should return diagnostics payload for existing job."""
    manager = _FakeJobManager({"job-1": _FakeJob(id="job-1", status="timeout", timed_out=True)})
    response = build_job_diagnostics_response(urlparse("/job-diagnostics?id=job-1&lang=en"), manager)
    assert response.status.value == 200
    body = response.body.decode("utf-8")
    assert '"id": "job-1"' in body
    assert '"status": "timeout"' in body
    assert '"can_export_bundle": true' in body


def test_build_job_bundle_response_rejects_success_status() -> None:
    """Bundle export should be limited to failure-like statuses."""
    manager = _FakeJobManager({"job-ok": _FakeJob(id="job-ok", status="success", return_code=0)})
    response = build_job_bundle_response(
        urlparse("/job-bundle?id=job-ok&lang=en"),
        manager,
        workspace_root=_workspace_dir("diag-bundle-reject"),
    )
    assert response.status.value == 400
    assert b"Diagnostics bundle is available only" in response.body


def test_build_job_bundle_response_exports_zip_for_failed_job() -> None:
    """Bundle route should return zip payload with diagnostics files."""
    manager = _FakeJobManager({"job-failed": _FakeJob(id="job-failed", status="failed")})
    response = build_job_bundle_response(
        urlparse("/job-bundle?id=job-failed&lang=en"),
        manager,
        workspace_root=_workspace_dir("diag-bundle-ok"),
    )
    assert response.status.value == 200
    assert response.content_type == "application/zip"
    assert "attachment; filename=job-job-failed-diagnostics.zip" == response.headers["Content-Disposition"]

    with zipfile.ZipFile(BytesIO(response.body), mode="r") as zf:
        names = sorted(zf.namelist())
    assert names == ["diagnostics.json", "diagnostics.log"]
