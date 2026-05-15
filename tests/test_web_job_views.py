"""Unit tests for web job view helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone

from project.web.job_views import fmt_dt, job_row_html, status_badge


@dataclass
class _FakeJob:
    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    return_code: int | None
    command: str

    def command_text(self) -> str:
        return self.command


def test_fmt_dt_handles_none_and_timestamp() -> None:
    """Datetime formatting returns placeholder for None and timestamp for value."""
    assert fmt_dt(None) == "-"
    value = datetime(2026, 5, 8, 10, 30, tzinfo=timezone.utc)
    assert "2026-05-08" in fmt_dt(value)


def test_status_badge_uses_localized_label() -> None:
    """Status badge includes localized label and color style."""
    html = status_badge("running", lang="en")
    assert "running" in html
    assert "background:#2563eb" in html


def test_status_badge_supports_timeout_status() -> None:
    """Timeout status should render dedicated badge color."""
    html = status_badge("timeout", lang="en")
    assert "timeout" in html
    assert "background:#7c3aed" in html


def test_job_row_html_contains_link_and_command() -> None:
    """Rendered row should include job link, command and status."""
    job = _FakeJob(
        id="abc123",
        status="success",
        started_at=datetime(2026, 5, 8, 10, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 5, 8, 10, 1, tzinfo=timezone.utc),
        return_code=0,
        command="python -m project.experiments.run --config config.yaml",
    )
    html = job_row_html(job, lang="en")
    assert "/job?lang=en&amp;id=abc123" in html
    assert "python -m project.experiments.run" in html
    assert "success" in html
