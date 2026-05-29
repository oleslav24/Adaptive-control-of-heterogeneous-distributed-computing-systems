"""Unit tests for agent control web route and page rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from project.web.agent_control_routes import build_agent_control_response


@dataclass
class _FakeJob:
    id: str
    status: str = "success"
    command: list[str] = field(default_factory=lambda: ["python", "-m", "project.experiments.run", "--publication-study"])
    log_lines: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)


class _FakeJobManager:
    def __init__(self, jobs: list[_FakeJob]) -> None:
        self._jobs = {job.id: job for job in jobs}

    def list_jobs(self) -> list[_FakeJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> _FakeJob | None:
        return self._jobs.get(job_id)


def test_agent_control_route_renders_html_for_ru() -> None:
    """`/agent-control` should render localized HTML shell."""
    manager = _FakeJobManager([])
    response = build_agent_control_response(urlparse("/agent-control?lang=ru"), manager)
    html = response.body.decode("utf-8")

    assert response.status.value == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert 'lang="ru"' in html
    assert "id=\"ac-run-scenario\"" in html
    assert '"id": "policy"' in html


def test_agent_control_route_latest_assessment_renders_signal_table() -> None:
    """Latest-job assessment mode should render table rows for component signals."""
    manager = _FakeJobManager([_FakeJob(id="job-abc123")])
    response = build_agent_control_response(
        urlparse("/agent-control?lang=en&assess=latest"),
        manager,
    )
    html = response.body.decode("utf-8")

    assert response.status.value == 200
    assert "job-abc123" in html
    assert "Agent Control / Quality Gate" in html
    assert "<th>Component</th>" in html
    assert "<td>policy</td>" in html
    assert "Overall" in html
    assert "/job?lang=en&amp;id=job-abc123" in html
    assert "/job-diagnostics?lang=en&amp;id=job-abc123" in html
    assert "Download diagnostics bundle" not in html


def test_agent_control_route_latest_terminal_picks_completed_job() -> None:
    """Latest-terminal assessment should skip running jobs and pick completed one."""
    manager = _FakeJobManager(
        [
            _FakeJob(id="job-running", status="running"),
            _FakeJob(id="job-done", status="success"),
        ]
    )
    response = build_agent_control_response(
        urlparse("/agent-control?lang=en&assess=latest-terminal"),
        manager,
    )
    html = response.body.decode("utf-8")

    assert response.status.value == 200
    assert "<code>job-done</code>" in html
    assert "<code>job-running</code>" not in html


def test_agent_control_route_terminal_status_renders_bundle_link() -> None:
    """Failed/timeout/stopped assessed jobs should expose diagnostics bundle link."""
    manager = _FakeJobManager([_FakeJob(id="job-timeout", status="timeout")])
    response = build_agent_control_response(
        urlparse("/agent-control?lang=en&assess=latest"),
        manager,
    )
    html = response.body.decode("utf-8")
    assert response.status.value == 200
    assert "/job-bundle?lang=en&amp;id=job-timeout" in html
