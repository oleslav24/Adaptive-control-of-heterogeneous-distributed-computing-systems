"""Unit tests for job page route response builder."""

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from project.web.job_page_routes import build_job_page_response
from project.web.i18n import tr


@dataclass
class _FakeJob:
    id: str
    status: str = "queued"
    started_at: datetime | None = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)


class _FakeJobManager:
    def __init__(self, jobs: list[_FakeJob]) -> None:
        self._jobs = {job.id: job for job in jobs}

    def get(self, job_id: str) -> _FakeJob | None:
        return self._jobs.get(job_id)


def test_build_job_page_response_not_found() -> None:
    """Unknown job id should return localized not-found response."""
    manager = _FakeJobManager([])
    response = build_job_page_response(urlparse("/job?id=missing&lang=en"), manager)
    assert response.status.value == 404
    assert response.content_type == "text/plain; charset=utf-8"
    assert response.body.decode("utf-8") == tr("en", "job_not_found")


def test_build_job_page_response_success_html() -> None:
    """Known job id should return rendered job page HTML."""
    manager = _FakeJobManager([_FakeJob(id="job-42", status="running")])
    response = build_job_page_response(urlparse("/job?id=job-42&lang=ru"), manager)
    html = response.body.decode("utf-8")
    assert response.status.value == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert "job-42" in html
    assert 'lang="ru"' in html
    assert "pollTimer = setInterval(pollJobData, 2000);" in html
