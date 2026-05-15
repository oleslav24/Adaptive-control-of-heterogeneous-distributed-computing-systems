"""Route dispatch tables for web request paths."""

from __future__ import annotations


GET_ROUTE_ACTIONS: dict[str, str] = {
    "/": "dashboard",
    "/job": "job",
    "/job-data": "job_data",
    "/job-diagnostics": "job_diagnostics",
    "/job-bundle": "job_bundle",
    "/files": "files",
    "/download": "download",
    "/health": "health",
}

POST_ROUTE_ACTIONS: dict[str, str] = {
    "/run": "run",
    "/stop": "stop",
}


def resolve_get_action(path: str) -> str | None:
    """Return GET action name for request path."""
    return GET_ROUTE_ACTIONS.get(path)


def resolve_post_action(path: str) -> str | None:
    """Return POST action name for request path."""
    return POST_ROUTE_ACTIONS.get(path)
