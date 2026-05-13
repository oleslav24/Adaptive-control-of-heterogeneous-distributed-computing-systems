"""Unit tests for job details page renderer."""

from dataclasses import dataclass
from datetime import datetime, timezone

from project.web.job_page_views import build_job_page_html
from project.web.i18n import tr


@dataclass
class _FakeJob:
    id: str = "job-1"
    status: str = "running"
    started_at: datetime | None = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)


def test_build_job_page_html_includes_stop_for_running_job() -> None:
    """Running job page should include stop form and polling script."""
    html = build_job_page_html(_FakeJob(status="running"), "en")
    assert 'action="/stop"' in html
    assert tr("en", "stop_job") in html
    assert "const jobId =" in html
    assert "pollTimer = setInterval(pollJobData, 2000);" in html
    assert "chart-latency" in html
    assert "chart-queue-completed" in html


def test_build_job_page_html_hides_stop_for_non_running_job() -> None:
    """Completed job page should not render stop form."""
    html = build_job_page_html(
        _FakeJob(
            status="success",
            finished_at=datetime(2026, 5, 13, 10, 5, tzinfo=timezone.utc),
            return_code=0,
        ),
        "en",
    )
    assert 'action="/stop"' not in html
    assert "job-1" in html
    assert "python -m project.experiments.run" in html


def test_build_job_page_html_localizes_static_labels() -> None:
    """Renderer should use requested language for static labels."""
    html = build_job_page_html(_FakeJob(status="queued"), "ru")
    assert 'lang="ru"' in html
    assert tr("ru", "job") in html
    assert tr("ru", "back_dashboard") in html
    assert tr("ru", "log") in html
