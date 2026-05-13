"""Shared normalized HTTP response payload helpers for web routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
import json


@dataclass(frozen=True)
class RouteResponse:
    """Normalized HTTP response payload for route helper functions."""

    status: HTTPStatus
    content_type: str
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


def text_response(status: HTTPStatus, text: str) -> RouteResponse:
    """Build plain-text response payload."""
    return RouteResponse(
        status=status,
        content_type="text/plain; charset=utf-8",
        body=text.encode("utf-8"),
    )


def html_response(status: HTTPStatus, html: str) -> RouteResponse:
    """Build HTML response payload."""
    return RouteResponse(
        status=status,
        content_type="text/html; charset=utf-8",
        body=html.encode("utf-8"),
    )


def json_response(
    status: HTTPStatus,
    payload: dict[str, object],
    *,
    ensure_ascii: bool = False,
    cache_control: str | None = "no-store",
) -> RouteResponse:
    """Build JSON response payload with optional cache header."""
    headers: dict[str, str] = {}
    if cache_control:
        headers["Cache-Control"] = cache_control
    return RouteResponse(
        status=status,
        content_type="application/json; charset=utf-8",
        body=json.dumps(payload, ensure_ascii=ensure_ascii).encode("utf-8"),
        headers=headers,
    )


def redirect_response(
    location: str,
    *,
    status: HTTPStatus = HTTPStatus.SEE_OTHER,
) -> RouteResponse:
    """Build redirect response payload with `Location` header."""
    return RouteResponse(
        status=status,
        content_type="text/plain; charset=utf-8",
        body=b"",
        headers={"Location": location},
    )
