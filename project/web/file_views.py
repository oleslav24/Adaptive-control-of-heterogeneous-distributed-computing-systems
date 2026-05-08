"""File path and preview helpers for the web interface."""

from __future__ import annotations

import mimetypes
from html import escape
from pathlib import Path

from project.web.i18n import tr
from project.web.routing import language_switcher, with_lang


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


def build_directory_body(
    path: Path,
    rel: str,
    lang: str,
    *,
    workspace_root: Path = WORKSPACE_ROOT,
) -> str:
    """Render directory listing body for `/files` route."""
    resolved_workspace = workspace_root.resolve()
    parent_link = ""
    if path.resolve() != resolved_workspace:
        parent_rel = rel_workspace(path.parent, workspace_root=workspace_root)
        parent_url = with_lang("/files", lang, path=parent_rel)
        parent_link = (
            f"<p><a href='{escape(parent_url)}'>{escape(tr(lang, 'parent'))}</a></p>"
        )

    rows: list[str] = []
    items = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    for item in items:
        item_rel = rel_workspace(item, workspace_root=workspace_root)
        if item.is_dir():
            item_url = with_lang("/files", lang, path=item_rel)
            rows.append(
                "<tr>"
                f"<td>{escape(tr(lang, 'dir'))}</td><td><a href='{escape(item_url)}'>{escape(item.name)}</a></td>"
                "<td>-</td>"
                "</tr>"
            )
            continue
        size = item.stat().st_size
        item_url = with_lang("/files", lang, path=item_rel)
        rows.append(
            "<tr>"
            f"<td>{escape(tr(lang, 'file'))}</td><td><a href='{escape(item_url)}'>{escape(item.name)}</a></td>"
            f"<td>{size}</td>"
            "</tr>"
        )

    table_body = "".join(rows) or f"<tr><td colspan='3'>{escape(tr(lang, 'empty'))}</td></tr>"
    switcher = language_switcher(lang, "/files", path=rel)
    download_as_is_url = with_lang("/download", lang, path=rel)
    back_dashboard_url = with_lang("/", lang)
    return f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(tr(lang, "browse"))}: <code>{escape(rel)}</code></h1>
<p><a href="{escape(back_dashboard_url)}">{escape(tr(lang, "back_dashboard"))}</a> | <a href="{escape(download_as_is_url)}">{escape(tr(lang, "download_as_is"))}</a></p>
{parent_link}
<table>
  <thead><tr><th>{escape(tr(lang, "type"))}</th><th>{escape(tr(lang, "name"))}</th><th>{escape(tr(lang, "size_bytes"))}</th></tr></thead>
  <tbody>{table_body}</tbody>
</table>
"""


def build_file_body(
    path: Path,
    rel: str,
    lang: str,
    *,
    workspace_root: Path = WORKSPACE_ROOT,
) -> str:
    """Render file detail body for `/files` route."""
    download_url = with_lang("/download", lang, path=rel)
    preview_html = build_preview_html(path, rel, lang)
    switcher = language_switcher(lang, "/files", path=rel)
    back_dashboard_url = with_lang("/", lang)
    back_folder_url = with_lang(
        "/files",
        lang,
        path=rel_workspace(path.parent, workspace_root=workspace_root),
    )
    return f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(tr(lang, "file_page"))}: <code>{escape(rel)}</code></h1>
<p><a href="{escape(back_dashboard_url)}">{escape(tr(lang, "back_dashboard"))}</a> |
<a href="{escape(back_folder_url)}">{escape(tr(lang, "back_folder"))}</a> |
<a href="{escape(download_url)}">{escape(tr(lang, "download"))}</a></p>
{preview_html}
"""


def read_download_payload(path: Path) -> tuple[str, bytes]:
    """Read file bytes and infer content type for `/download` route."""
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream", path.read_bytes()
