"""File path and preview helpers for the web interface."""

from __future__ import annotations

from html import escape
from pathlib import Path

from project.web.i18n import tr
from project.web.routing import with_lang


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PREVIEW_CHAR_LIMIT = 120_000


def resolve_path(
    raw: str,
    *,
    workspace_root: Path = WORKSPACE_ROOT,
    default_subdir: str = "outputs",
) -> Path:
    """Resolve user path and ensure it stays inside workspace root."""
    candidate = (raw or "").strip()
    if not candidate:
        path = workspace_root / default_subdir
    else:
        path = Path(candidate)
        if not path.is_absolute():
            path = workspace_root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise ValueError("Path must stay within workspace root.") from exc
    return resolved


def rel_workspace(path: Path, *, workspace_root: Path = WORKSPACE_ROOT) -> str:
    """Return path relative to workspace using forward slashes."""
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def build_preview_html(
    path: Path,
    rel: str,
    lang: str,
    *,
    max_preview_chars: int = DEFAULT_PREVIEW_CHAR_LIMIT,
) -> str:
    """Build safe preview block for common file types."""
    suffix = path.suffix.lower()
    download_url = with_lang("/download", lang, path=rel)

    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
        return (
            "<div class='card'>"
            f"<h2>{escape(tr(lang, 'preview'))}</h2>"
            f"<img src='{escape(download_url)}' alt='{escape(path.name)}' class='preview' />"
            "</div>"
        )

    if suffix in {".txt", ".log", ".md", ".json", ".csv", ".yaml", ".yml"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_preview_chars:
            text = text[:max_preview_chars] + "\n... [truncated]"
        return (
            "<div class='card'>"
            f"<h2>{escape(tr(lang, 'preview'))}</h2>"
            f"<pre class='log'>{escape(text)}</pre>"
            "</div>"
        )

    return (
        "<div class='card'>"
        f"<p>{escape(tr(lang, 'no_inline_preview'))}</p>"
        "</div>"
    )

