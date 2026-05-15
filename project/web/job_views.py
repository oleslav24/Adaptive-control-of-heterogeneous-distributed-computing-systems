"""HTML helpers for job tables and status badges."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Protocol

from project.web.i18n import STATUS_LABELS, tr
from project.web.routing import with_lang


class _JobRowLike(Protocol):
    """Minimal protocol for job row rendering."""

    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    return_code: int | None

    def command_text(self) -> str: ...


def fmt_dt(value: datetime | None) -> str:
    """Format datetime for UI tables."""
    if value is None:
        return "-"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def status_badge(status: str, lang: str = "en") -> str:
    """Render status as colored badge."""
    color = {
        "queued": "#6b7280",
        "running": "#2563eb",
        "success": "#16a34a",
        "failed": "#dc2626",
        "stopped": "#b45309",
        "timeout": "#7c3aed",
    }.get(status, "#6b7280")
    label = STATUS_LABELS.get(lang, STATUS_LABELS["en"]).get(status, status)
    return (
        f"<span class='badge' style='background:{color}'>"
        f"{escape(label)}</span>"
    )


def job_row_html(job: _JobRowLike, lang: str) -> str:
    """Render one row of job list table."""
    command = escape(job.command_text())
    open_url = with_lang("/job", lang, id=job.id)
    return (
        "<tr>"
        f"<td><a href='{escape(open_url)}'><code>{escape(job.id)}</code></a></td>"
        f"<td>{status_badge(job.status, lang)}</td>"
        f"<td>{escape(fmt_dt(job.started_at))}</td>"
        f"<td>{escape(fmt_dt(job.finished_at))}</td>"
        f"<td><code>{escape(str(job.return_code))}</code></td>"
        f"<td><code>{command}</code></td>"
        f"<td><a href='{escape(open_url)}'>{escape(tr(lang, 'open'))}</a></td>"
        "</tr>"
    )

