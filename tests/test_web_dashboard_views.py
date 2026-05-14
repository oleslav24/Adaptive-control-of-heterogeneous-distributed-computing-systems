"""Unit tests for dashboard HTML rendering helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project.web.dashboard_views import build_dashboard_html
from project.web.i18n import DEFAULT_BATCH_SCENARIOS, tr


@dataclass
class _FakeJob:
    id: str
    status: str
    started_at: datetime | None = datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)


def test_build_dashboard_html_with_empty_jobs_renders_defaults() -> None:
    """Dashboard should include empty-table messages and default config path."""
    html = build_dashboard_html(
        "en",
        [],
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert tr("en", "console_title") in html
    assert tr("en", "no_active_jobs") in html
    assert tr("en", "no_runs_started") in html
    assert 'id="run-form"' in html
    assert 'name="config" value="config.yaml"' in html
    assert 'name="job_timeout_seconds" value="3600"' in html
    assert f'data-default-batch-scenario-count="{len(DEFAULT_BATCH_SCENARIOS)}"' in html
    assert "href=\"/files?lang=en&amp;path=outputs\"" in html


def test_build_dashboard_html_renders_running_and_recent_jobs() -> None:
    """Running and recent jobs should be rendered in dashboard tables."""
    jobs = [
        _FakeJob(id="job-running", status="running"),
        _FakeJob(id="job-success", status="success", finished_at=datetime(2026, 5, 13, 9, 5, tzinfo=timezone.utc)),
    ]
    html = build_dashboard_html(
        "en",
        jobs,
        workspace_root=Path(".").resolve(),
        default_config="alt.yaml",
    )
    assert "job-running" in html
    assert "job-success" in html
    assert "alt.yaml" in html
