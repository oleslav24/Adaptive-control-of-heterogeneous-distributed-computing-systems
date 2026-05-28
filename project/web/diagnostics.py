"""Diagnostics payload and bundle export helpers for web jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Protocol
import zipfile

from project.web.agent_control import (
    assess_job_control,
    job_control_assessment_payload,
    parse_job_signals,
)


_BUNDLE_ROOT = Path("outputs") / "_web_diagnostics"
_MAX_DIAGNOSTIC_LOG_LINES = 500


class _DiagnosticJobLike(Protocol):
    """Minimal job protocol for diagnostics export."""

    id: str
    status: str
    status_details: str
    started_at: datetime | None
    finished_at: datetime | None
    return_code: int | None
    timeout_seconds: int | None
    timed_out: bool
    log_lines: list[str]
    _lock: Lock

    def command_text(self) -> str: ...


@dataclass(slots=True)
class JobDiagnostics:
    """Serializable diagnostics payload for one job."""

    id: str
    status: str
    status_details: str
    return_code: int | None
    timeout_seconds: int | None
    timed_out: bool
    started_at_utc: str | None
    finished_at_utc: str | None
    duration_seconds: float | None
    command: str
    log_line_count: int
    log_tail: list[str]
    generated_at_utc: str

    def to_payload(self) -> dict[str, object]:
        """Convert diagnostics dataclass to JSON-ready payload."""
        return asdict(self)


def is_failure_like_status(status: str) -> bool:
    """Return True when diagnostics bundle should be available."""
    return str(status).strip().lower() in {"failed", "timeout", "stopped"}


def build_job_diagnostics(job: _DiagnosticJobLike) -> JobDiagnostics:
    """Build stable diagnostics payload from job state snapshot."""
    with job._lock:
        log_lines = list(job.log_lines)
    started = job.started_at
    finished = job.finished_at
    duration: float | None = None
    if started is not None and finished is not None:
        duration = max(0.0, (finished - started).total_seconds())
    return JobDiagnostics(
        id=job.id,
        status=job.status,
        status_details=str(job.status_details or "").strip() or "-",
        return_code=job.return_code,
        timeout_seconds=job.timeout_seconds,
        timed_out=bool(job.timed_out),
        started_at_utc=_fmt_iso(started),
        finished_at_utc=_fmt_iso(finished),
        duration_seconds=duration,
        command=job.command_text(),
        log_line_count=len(log_lines),
        log_tail=log_lines[-_MAX_DIAGNOSTIC_LOG_LINES:],
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def export_job_diagnostics_bundle(
    *,
    job: _DiagnosticJobLike,
    workspace_root: Path,
) -> Path:
    """Export diagnostics JSON + log into zip bundle and return path."""
    diagnostics = build_job_diagnostics(job)
    bundle_dir = workspace_root / _BUNDLE_ROOT / f"job-{job.id}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    diagnostics_json_path = bundle_dir / "diagnostics.json"
    diagnostics_log_path = bundle_dir / "diagnostics.log"
    control_assessment_path = bundle_dir / "control_assessment.json"
    zip_path = bundle_dir / f"job-{job.id}-diagnostics.zip"
    control_assessment_payload = job_control_assessment_payload(assess_job_control(job))

    with diagnostics_json_path.open("w", encoding="utf-8") as f:
        json.dump(diagnostics.to_payload(), f, indent=2, sort_keys=True)
    diagnostics_log_path.write_text("\n".join(diagnostics.log_tail), encoding="utf-8")
    with control_assessment_path.open("w", encoding="utf-8") as f:
        json.dump(control_assessment_payload, f, indent=2, sort_keys=True)

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(diagnostics_json_path, arcname="diagnostics.json")
        zf.write(diagnostics_log_path, arcname="diagnostics.log")
        zf.write(control_assessment_path, arcname="control_assessment.json")

    return zip_path


def export_job_control_assessment_artifact(
    *,
    job: _DiagnosticJobLike,
    workspace_root: Path,
) -> Path | None:
    """Persist `control_assessment.json` near produced run artifacts when possible."""
    parsed = parse_job_signals(job)
    target_dir = _resolve_control_assessment_dir(
        artifact_paths=parsed.existing_artifacts,
        workspace_root=workspace_root,
    )
    if target_dir is None:
        target_dir = _resolve_control_assessment_dir(
            artifact_paths=parsed.artifacts,
            workspace_root=workspace_root,
        )
    if target_dir is None:
        return None

    target_path = target_dir / "control_assessment.json"
    payload = job_control_assessment_payload(assess_job_control(job))
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return target_path


def _resolve_control_assessment_dir(
    *,
    artifact_paths: dict[str, str],
    workspace_root: Path,
) -> Path | None:
    """Resolve writable artifact directory from parsed output paths."""
    candidates = _ordered_artifact_candidates(artifact_paths)
    root = workspace_root.resolve()
    for raw_path in candidates:
        text = str(raw_path).strip()
        if not text:
            continue
        path = Path(text)
        parent = path.parent.resolve()
        if not _is_within(parent, root):
            continue
        parent.mkdir(parents=True, exist_ok=True)
        return parent
    return None


def _ordered_artifact_candidates(artifact_paths: dict[str, str]) -> list[str]:
    """Prioritize manifest-centric paths, then fall back to all parsed artifacts."""
    priority_keys = (
        "chapter10_manifest_json",
        "publication_publication_manifest_json",
        "publication_manifest_json",
        "run_manifest_json",
        "history_csv",
        "history_json",
        "summary_json",
    )
    ordered: list[str] = []
    for key in priority_keys:
        value = artifact_paths.get(key, "").strip()
        if value and value not in ordered:
            ordered.append(value)
    for _key, raw in sorted(artifact_paths.items()):
        value = str(raw).strip()
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _is_within(target: Path, root: Path) -> bool:
    """Return True when target path is inside workspace root."""
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _fmt_iso(value: datetime | None) -> str | None:
    """Format optional datetime for diagnostics payload."""
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()
