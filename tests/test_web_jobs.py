"""Unit tests for web background job models and manager."""

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

from project.web.jobs import (
    DEFAULT_JOB_TIMEOUT_SECONDS,
    JobManager,
    MAX_LOG_LINES,
    RunJob,
)


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


def test_job_manager_timeout_normalization() -> None:
    """Timeout normalization should keep safe defaults and clamp bounds."""
    manager = JobManager()
    assert manager._normalize_timeout_seconds(None) == DEFAULT_JOB_TIMEOUT_SECONDS  # noqa: SLF001
    assert manager._normalize_timeout_seconds(-1) == 10  # noqa: SLF001
    assert manager._normalize_timeout_seconds(1000000) == 86400  # noqa: SLF001
    assert manager._normalize_timeout_seconds(120) == 120  # noqa: SLF001


def test_run_job_timeout_marks_timeout_status() -> None:
    """Supervisor should stop long-running process and set timeout status."""
    manager = JobManager()
    job = RunJob(
        id="timeout-case",
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=Path(".").resolve(),
        timeout_seconds=1,
    )
    manager._run_job(job)  # noqa: SLF001
    assert job.status == "timeout"
    assert job.timed_out is True
    assert job.finished_at is not None
    assert job.status_details.startswith("timeout>")


def test_run_job_failed_exit_sets_status_details() -> None:
    """Non-zero process exit should produce failed status details."""
    manager = JobManager()
    job = RunJob(
        id="failed-case",
        command=[sys.executable, "-c", "raise SystemExit(3)"],
        cwd=Path(".").resolve(),
        timeout_seconds=30,
    )
    manager._run_job(job)  # noqa: SLF001
    assert job.status == "failed"
    assert job.return_code == 3
    assert job.status_details == "exit-code:3"


def test_run_job_exports_control_assessment_artifact() -> None:
    """Completed run should persist control assessment near reported manifest artifacts."""
    manager = JobManager()
    artifact_dir = (Path("outputs") / "test-suite" / f"job-control-{uuid4().hex[:8]}").resolve()
    script = (
        "from pathlib import Path;"
        f"target=Path({artifact_dir.as_posix()!r});"
        "target.mkdir(parents=True, exist_ok=True);"
        "manifest=target/'run_manifest.json';"
        "manifest.write_text('{}', encoding='utf-8');"
        "print(f'run_manifest_json: {manifest}', flush=True)"
    )
    job = RunJob(
        id="control-artifact",
        command=[sys.executable, "-c", script],
        cwd=Path(".").resolve(),
        timeout_seconds=30,
    )

    manager._run_job(job)  # noqa: SLF001

    control_path = artifact_dir / "control_assessment.json"
    assert job.status == "success"
    assert control_path.exists()
    payload = json.loads(control_path.read_text(encoding="utf-8"))
    assert payload["job_id"] == "control-artifact"
    assert any("control_assessment_json:" in line for line in job.log_lines)
