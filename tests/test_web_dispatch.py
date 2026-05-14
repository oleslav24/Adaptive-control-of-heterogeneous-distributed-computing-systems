"""Unit tests for web path dispatch tables."""

from project.web.dispatch import resolve_get_action, resolve_post_action


def test_resolve_get_action_for_known_routes() -> None:
    """Known GET routes should map to stable action names."""
    assert resolve_get_action("/") == "dashboard"
    assert resolve_get_action("/job") == "job"
    assert resolve_get_action("/job-data") == "job_data"
    assert resolve_get_action("/job-diagnostics") == "job_diagnostics"
    assert resolve_get_action("/job-bundle") == "job_bundle"
    assert resolve_get_action("/files") == "files"
    assert resolve_get_action("/download") == "download"
    assert resolve_get_action("/health") == "health"


def test_resolve_get_action_returns_none_for_unknown_routes() -> None:
    """Unknown GET route should return None."""
    assert resolve_get_action("/unknown") is None
    assert resolve_get_action("/job/123") is None


def test_resolve_post_action_for_known_routes() -> None:
    """Known POST routes should map to stable action names."""
    assert resolve_post_action("/run") == "run"
    assert resolve_post_action("/stop") == "stop"


def test_resolve_post_action_returns_none_for_unknown_routes() -> None:
    """Unknown POST route should return None."""
    assert resolve_post_action("/unknown") is None
    assert resolve_post_action("/run-now") is None
