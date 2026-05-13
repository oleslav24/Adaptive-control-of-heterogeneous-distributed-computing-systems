"""Route handlers for file browsing and file downloads."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs

from project.web.file_views import (
    build_directory_body,
    build_file_body,
    read_download_payload,
    rel_workspace,
    resolve_path,
)
from project.web.i18n import tr
from project.web.layout import render_layout
from project.web.route_responses import (
    RouteResponse,
    html_response,
    text_response,
)
from project.web.routing import first, lang_from_parsed


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


def build_files_response(parsed, *, workspace_root: Path = WORKSPACE_ROOT) -> RouteResponse:
    """Create response payload for `/files` route."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    raw_path = first(query, "path", "outputs")
    try:
        path = resolve_path(raw_path, workspace_root=workspace_root)
    except ValueError as exc:
        return text_response(HTTPStatus.BAD_REQUEST, str(exc))

    if not path.exists():
        return text_response(HTTPStatus.NOT_FOUND, tr(lang, "path_not_exist"))

    rel = rel_workspace(path, workspace_root=workspace_root)
    if path.is_dir():
        body = build_directory_body(path, rel, lang, workspace_root=workspace_root)
        html = render_layout(f"{tr(lang, 'browse')}: {rel}", body, lang=lang)
        return html_response(HTTPStatus.OK, html)

    body = build_file_body(path, rel, lang, workspace_root=workspace_root)
    html = render_layout(f"{tr(lang, 'file_page')}: {rel}", body, lang=lang)
    return html_response(HTTPStatus.OK, html)


def build_download_response(parsed, *, workspace_root: Path = WORKSPACE_ROOT) -> RouteResponse:
    """Create response payload for `/download` route."""
    query = parse_qs(parsed.query)
    lang = lang_from_parsed(parsed)
    raw_path = first(query, "path", "")
    try:
        path = resolve_path(raw_path, workspace_root=workspace_root)
    except ValueError as exc:
        return text_response(HTTPStatus.BAD_REQUEST, str(exc))

    if not path.exists() or path.is_dir():
        return text_response(HTTPStatus.NOT_FOUND, tr(lang, "file_not_found"))

    content_type, data = read_download_payload(path)
    return RouteResponse(
        status=HTTPStatus.OK,
        content_type=content_type,
        body=data,
        headers={"Content-Disposition": f"inline; filename={path.name}"},
    )
