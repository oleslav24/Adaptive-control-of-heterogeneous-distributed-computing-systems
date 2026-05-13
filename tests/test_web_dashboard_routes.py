"""Unit tests for dashboard route response builder."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from project.web.dashboard_routes import build_dashboard_response
from project.web.i18n import tr


@dataclass
class _FakeJob:
    id: str
    status: str
    started_at: datetime | None = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)


class _FakeJobManager:
    def __init__(self, jobs: list[_FakeJob]) -> None:
        self._jobs = list(jobs)

    def list_jobs(self) -> list[_FakeJob]:
        return list(self._jobs)


def test_build_dashboard_response_renders_html_payload() -> None:
    """Dashboard route should return HTML document for provided jobs."""
    manager = _FakeJobManager(
        [
            _FakeJob(id="job-1", status="running"),
            _FakeJob(id="job-2", status="success"),
        ]
    )
    response = build_dashboard_response(
        urlparse("/?lang=en"),
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    html = response.body.decode("utf-8")
    assert response.status.value == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert tr("en", "console_title") in html
    assert "job-1" in html
    assert "job-2" in html
    assert "id=\"run-form\"" in html


def test_build_dashboard_response_uses_requested_language() -> None:
    """Dashboard route should respect `lang` query parameter."""
    manager = _FakeJobManager([])
    response = build_dashboard_response(
        urlparse("/?lang=ru"),
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    html = response.body.decode("utf-8")
    assert 'lang="ru"' in html
    assert tr("ru", "console_title") in html
