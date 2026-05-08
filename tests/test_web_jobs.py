"""Unit tests for web background job models and manager."""

from datetime import datetime, timezone
from pathlib import Path

from project.web.jobs import JobManager, MAX_LOG_LINES, RunJob


class _FakeProcess:
    def __init__(self, poll_value: int | None) -> None:
        self._poll_value = poll_value
        self.terminated = False

    def poll(self) -> int | None:
        return self._poll_value

    def terminate(self) -> None:
        self.terminated = True


def test_run_job_command_text_and_log_capping() -> None:
    """RunJob should format command and cap in-memory log size."""
    job = RunJob(
        id="job-1",
        command=["python", "-m", "project.experiments.run", "--output-dir", "dir with space"],
        cwd=Path("."),
    )
    assert "'dir with space'" in job.command_text()

    for idx in range(MAX_LOG_LINES + 2):
        job.append_log(f"line-{idx}")
    assert len(job.log_lines) == MAX_LOG_LINES
    assert job.log_lines[0] == "line-2"


def test_run_job_stop_terminates_only_running_process() -> None:
    """Stop should terminate running process and ignore finished one."""
    running = RunJob(id="running", command=["python"], cwd=Path("."))
    running.process = _FakeProcess(poll_value=None)  # type: ignore[assignment]
    assert running.stop() is True
    assert running.process is not None
    assert running.process.terminated is True  # type: ignore[union-attr]

    finished = RunJob(id="finished", command=["python"], cwd=Path("."))
    finished.process = _FakeProcess(poll_value=0)  # type: ignore[assignment]
    assert finished.stop() is False


def test_job_manager_get_and_sorted_list() -> None:
    """Manager should return jobs and sort by newest timestamp."""
    manager = JobManager()
    older = RunJob(
        id="older",
        command=["python"],
        cwd=Path("."),
        started_at=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
    )
    newer = RunJob(
        id="newer",
        command=["python"],
        cwd=Path("."),
        started_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
    )
    manager._jobs[older.id] = older
    manager._jobs[newer.id] = newer

    assert manager.get("older") is older
    ordered = manager.list_jobs()
    assert [item.id for item in ordered[:2]] == ["newer", "older"]
