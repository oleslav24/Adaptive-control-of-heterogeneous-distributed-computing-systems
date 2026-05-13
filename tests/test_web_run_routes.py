"""Unit tests for run start/stop route helpers."""

from dataclasses import dataclass, field
from pathlib import Path

from project.web.run_routes import build_start_run_response, build_stop_run_response


@dataclass
class _FakeJob:
    id: str
    status: str = "running"
    stop_result: bool = True
    logs: list[str] = field(default_factory=list)

    def stop(self) -> bool:
        return self.stop_result

    def append_log(self, line: str) -> None:
        self.logs.append(line)


class _FakeJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, _FakeJob] = {}
        self.last_create_command: list[str] | None = None
        self.last_create_cwd: Path | None = None
        self._next_id = 1

    def create(self, *, command: list[str], cwd: Path) -> _FakeJob:
        self.last_create_command = list(command)
        self.last_create_cwd = cwd
        job = _FakeJob(id=f"job-{self._next_id}")
        self._jobs[job.id] = job
        self._next_id += 1
        return job

    def get(self, job_id: str) -> _FakeJob | None:
        return self._jobs.get(job_id)


def test_build_start_run_response_creates_job_and_redirects() -> None:
    """Start route should create a job and redirect to job page."""
    manager = _FakeJobManager()
    form = {
        "lang": ["ru"],
        "mode": ["single"],
        "config": ["custom.yaml"],
        "algorithm": ["min-load"],
        "scenario": ["static"],
    }
    workspace_root = Path(".").resolve()

    response = build_start_run_response(
        form,
        manager,
        workspace_root=workspace_root,
        default_config="config.yaml",
    )
    assert response.status.value == 303
    assert response.headers["Location"] == "/job?lang=ru&id=job-1"
    assert manager.last_create_cwd == workspace_root
    assert manager.last_create_command is not None
    assert "--config" in manager.last_create_command
    assert "custom.yaml" in manager.last_create_command
    assert "--algorithm" in manager.last_create_command
    assert "min-load" in manager.last_create_command


def test_build_stop_run_response_returns_not_found_for_unknown_job() -> None:
    """Stop route should return text not-found when job is missing."""
    manager = _FakeJobManager()
    response = build_stop_run_response({"lang": ["en"], "id": ["missing"]}, manager)
    assert response.status.value == 404
    assert response.body.decode("utf-8") == "Job not found."


def test_build_stop_run_response_updates_state_and_redirects() -> None:
    """Stop route should update status/log when stop succeeds."""
    manager = _FakeJobManager()
    job = manager.create(command=["python", "-m", "project.experiments.run"], cwd=Path(".").resolve())
    response = build_stop_run_response({"lang": ["en"], "id": [job.id]}, manager)
    assert response.status.value == 303
    assert response.headers["Location"] == f"/job?lang=en&id={job.id}"
    assert job.status == "stopped"
    assert job.logs[-1] == "[web-ui] stop requested."
