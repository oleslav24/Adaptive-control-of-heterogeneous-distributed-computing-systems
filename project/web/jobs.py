"""Background job models and execution manager for web UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess
from threading import Event
from threading import Lock, Thread
import time
from uuid import uuid4

from project.web.diagnostics import export_job_control_assessment_artifact


MAX_LOG_LINES = 4000
DEFAULT_JOB_TIMEOUT_SECONDS = 3600
MIN_JOB_TIMEOUT_SECONDS = 10
MAX_JOB_TIMEOUT_SECONDS = 86400
JOB_POLL_INTERVAL_SECONDS = 0.2
JOB_TERMINATE_GRACE_SECONDS = 3.0


@dataclass(slots=True)
class RunJob:
    """Background experiment process state."""

    id: str
    command: list[str]
    cwd: Path
    status: str = "queued"  # queued | running | success | failed | stopped | timeout
    started_at: datetime | None = None
    finished_at: datetime | None = None
    return_code: int | None = None
    timeout_seconds: int | None = DEFAULT_JOB_TIMEOUT_SECONDS
    timed_out: bool = False
    stop_requested: bool = False
    status_details: str = ""
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
            self.stop_requested = True
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

    def create(
        self,
        command: list[str],
        cwd: Path,
        *,
        timeout_seconds: int | None = None,
    ) -> RunJob:
        """Create and launch background job for command."""
        job = RunJob(
            id=uuid4().hex[:10],
            command=list(command),
            cwd=cwd,
            timeout_seconds=self._normalize_timeout_seconds(timeout_seconds),
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
        job.status_details = ""
        job.started_at = datetime.now(timezone.utc)
        process: subprocess.Popen[str] | None = None
        stream_done = Event()
        output_thread: Thread | None = None
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
            output_thread = Thread(
                target=self._capture_stdout,
                args=(job, process, stream_done),
                daemon=True,
            )
            output_thread.start()
            self._supervise_process(job, process)
            code = process.wait()
            job.return_code = code
            if job.status == "timeout":
                pass
            elif job.stop_requested:
                job.status = "stopped"
                if not job.status_details:
                    job.status_details = "stop-requested"
            elif code == 0:
                job.status = "success"
                if not job.status_details:
                    job.status_details = "completed"
            else:
                job.status = "failed"
                if not job.status_details:
                    job.status_details = f"exit-code:{code}"
        except Exception as exc:  # noqa: BLE001
            job.append_log(f"[web-ui] runner error: {exc!r}")
            job.return_code = -1
            if job.status not in {"stopped", "timeout"}:
                job.status = "failed"
            if not job.status_details:
                job.status_details = f"runner-error:{type(exc).__name__}"
        finally:
            if output_thread is not None:
                stream_done.set()
                output_thread.join(timeout=1.0)
            with job._lock:
                job.process = None
            job.finished_at = datetime.now(timezone.utc)
            self._persist_control_assessment(job)

    def _supervise_process(self, job: RunJob, process: subprocess.Popen[str]) -> None:
        """Poll running process and enforce timeout/stop semantics."""
        started = job.started_at or datetime.now(timezone.utc)
        while process.poll() is None:
            if job.stop_requested:
                self._terminate_with_grace(process)
                break
            timeout_seconds = job.timeout_seconds
            if timeout_seconds is not None and timeout_seconds > 0:
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed >= timeout_seconds:
                    job.timed_out = True
                    job.status = "timeout"
                    job.status_details = f"timeout>{int(timeout_seconds)}s"
                    job.append_log(
                        f"[web-ui] timeout reached ({int(timeout_seconds)}s), terminating process."
                    )
                    self._terminate_with_grace(process)
                    break
            time.sleep(JOB_POLL_INTERVAL_SECONDS)

    def _capture_stdout(
        self,
        job: RunJob,
        process: subprocess.Popen[str],
        done_event: Event,
    ) -> None:
        """Consume process stdout line-by-line to prevent PIPE blocking."""
        stream = process.stdout
        if stream is None:
            return
        while not done_event.is_set():
            line = stream.readline()
            if not line:
                if process.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            job.append_log(line)

    def _terminate_with_grace(self, process: subprocess.Popen[str]) -> None:
        """Attempt graceful terminate, then force kill on timeout."""
        if process.poll() is not None:
            return
        process.terminate()
        deadline = time.monotonic() + JOB_TERMINATE_GRACE_SECONDS
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if process.poll() is None:
            process.kill()

    def _normalize_timeout_seconds(self, raw_value: int | None) -> int:
        """Normalize optional timeout input to safe bounded value."""
        if raw_value is None:
            return DEFAULT_JOB_TIMEOUT_SECONDS
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return DEFAULT_JOB_TIMEOUT_SECONDS
        if parsed < MIN_JOB_TIMEOUT_SECONDS:
            return MIN_JOB_TIMEOUT_SECONDS
        if parsed > MAX_JOB_TIMEOUT_SECONDS:
            return MAX_JOB_TIMEOUT_SECONDS
        return parsed

    def _persist_control_assessment(self, job: RunJob) -> None:
        """Persist control-assessment artifact for completed jobs when output paths exist."""
        if job.status not in {"success", "failed", "timeout", "stopped"}:
            return
        try:
            artifact_path = export_job_control_assessment_artifact(
                job=job,
                workspace_root=job.cwd,
            )
        except Exception as exc:  # noqa: BLE001
            job.append_log(f"[web-ui] control assessment export failed: {exc!r}")
            return
        if artifact_path is not None:
            job.append_log(f"control_assessment_json: {artifact_path}")

