"""Background job models and execution manager for web UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess
from threading import Lock, Thread
from uuid import uuid4


MAX_LOG_LINES = 4000


@dataclass(slots=True)
class RunJob:
    """Background experiment process state."""

    id: str
    command: list[str]
    cwd: Path
    status: str = "queued"  # queued | running | success | failed | stopped
    started_at: datetime | None = None
    finished_at: datetime | None = None
    return_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    process: subprocess.Popen[str] | None = field(default=None, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def command_text(self) -> str:
        """Render command as shell-like string."""
        return " ".join(shlex.quote(part) for part in self.command)

    def append_log(self, line: str) -> None:
        """Append one log line and trim history to cap."""
        with self._lock:
            self.log_lines.append(line.rstrip("\n"))
            if len(self.log_lines) > MAX_LOG_LINES:
                over = len(self.log_lines) - MAX_LOG_LINES
                del self.log_lines[:over]

    def stop(self) -> bool:
        """Request process termination if still running."""
        with self._lock:
            process = self.process
        if process is None or process.poll() is not None:
            return False
        process.terminate()
        return True


class JobManager:
    """Thread-safe registry and executor for background experiment jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, RunJob] = {}
        self._lock = Lock()

    def create(self, command: list[str], cwd: Path) -> RunJob:
        """Create and launch background job for command."""
        job = RunJob(
            id=uuid4().hex[:10],
            command=list(command),
            cwd=cwd,
        )
        with self._lock:
            self._jobs[job.id] = job
        thread = Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    def list_jobs(self) -> list[RunJob]:
        """Return jobs sorted by newest start/finish timestamp."""
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(
            jobs,
            key=lambda item: item.started_at or item.finished_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    def get(self, job_id: str) -> RunJob | None:
        """Get one job by identifier."""
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job: RunJob) -> None:
        """Worker routine that executes command and captures logs."""
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                job.command,
                cwd=str(job.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            with job._lock:
                job.process = process
            if process.stdout is not None:
                for line in process.stdout:
                    job.append_log(line)
            code = process.wait()
            job.return_code = code
            if code == 0:
                job.status = "success"
            else:
                # Distinguish regular failures from manual stop if possible.
                if job.status != "stopped":
                    job.status = "failed"
        except Exception as exc:  # noqa: BLE001
            job.append_log(f"[web-ui] runner error: {exc!r}")
            job.return_code = -1
            if job.status != "stopped":
                job.status = "failed"
        finally:
            with job._lock:
                job.process = None
            job.finished_at = datetime.now(timezone.utc)

