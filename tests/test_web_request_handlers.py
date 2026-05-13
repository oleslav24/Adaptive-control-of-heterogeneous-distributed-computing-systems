"""Unit tests for high-level web request orchestration helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse

from project.web.request_handlers import build_get_response, build_post_response


@dataclass
class _FakeJob:
    id: str
    status: str = "queued"
    started_at: datetime | None = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    command: tuple[str, ...] = ("python", "-m", "project.experiments.run")

    def command_text(self) -> str:
        return " ".join(self.command)

    def stop(self) -> bool:
        return True

    def append_log(self, _line: str) -> None:
        return


class _FakeJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, _FakeJob] = {"job-1": _FakeJob(id="job-1")}

    def list_jobs(self) -> list[_FakeJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> _FakeJob | None:
        return self._jobs.get(job_id)

    def create(self, *, command: list[str], cwd: Path) -> _FakeJob:
        _ = (command, cwd)
        job = _FakeJob(id="job-2")
        self._jobs[job.id] = job
        return job


def test_build_get_response_health_route() -> None:
    """Health GET route should return short text OK payload."""
    manager = _FakeJobManager()
    response = build_get_response(
        urlparse("/health"),
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
        payload_builder=lambda _job, _lang: {},
    )
    assert response.status.value == 200
    assert response.content_type == "text/plain; charset=utf-8"
    assert response.body == b"ok"


def test_build_get_response_unknown_route_returns_not_found() -> None:
    """Unknown GET path should return localized 404 text response."""
    manager = _FakeJobManager()
    response = build_get_response(
        urlparse("/missing?lang=en"),
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
        payload_builder=lambda _job, _lang: {},
    )
    assert response.status.value == 404
    assert response.body.decode("utf-8") == "Not found."


def test_build_get_response_job_data_uses_payload_builder() -> None:
    """Job-data route should serialize payload from payload_builder."""
    manager = _FakeJobManager()
    response = build_get_response(
        urlparse("/job-data?id=job-1&lang=en"),
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
        payload_builder=lambda job, lang: {"id": job.id, "lang": lang},
    )
    assert response.status.value == 200
    payload = json.loads(response.body.decode("utf-8"))
    assert payload == {"id": "job-1", "lang": "en"}


def test_build_post_response_run_route_redirects_to_new_job() -> None:
    """Run POST route should create job and return redirect payload."""
    manager = _FakeJobManager()
    response = build_post_response(
        urlparse("/run"),
        {"mode": ["single"], "lang": ["ru"], "config": ["config.yaml"]},
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert response.status.value == 303
    assert response.headers["Location"] == "/job?lang=ru&id=job-2"


def test_build_post_response_unknown_route_returns_not_found() -> None:
    """Unknown POST path should return localized 404 text response."""
    manager = _FakeJobManager()
    response = build_post_response(
        urlparse("/missing"),
        {"lang": ["en"]},
        manager,
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert response.status.value == 404
    assert response.body.decode("utf-8") == "Not found."
