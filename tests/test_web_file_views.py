"""Unit tests for web file path and preview helpers."""

from pathlib import Path

import pytest

from project.web.file_views import build_preview_html, rel_workspace, resolve_path


def test_resolve_path_defaults_to_outputs_under_workspace() -> None:
    """Empty path resolves to workspace outputs folder."""
    workspace_root = Path(".").resolve()
    resolved = resolve_path("", workspace_root=workspace_root)
    assert resolved == (workspace_root / "outputs").resolve()


def test_resolve_path_rejects_escape_from_workspace() -> None:
    """Relative traversal outside workspace must be rejected."""
    workspace_root = Path(".").resolve()
    with pytest.raises(ValueError):
        resolve_path("../outside.txt", workspace_root=workspace_root)


def test_rel_workspace_returns_posix_relative_path() -> None:
    """Workspace-relative path should use forward slashes."""
    workspace_root = Path(".").resolve()
    target = workspace_root / "outputs" / "run.log"
    assert rel_workspace(target, workspace_root=workspace_root) == "outputs/run.log"


def test_build_preview_html_for_text_file_and_truncation() -> None:
    """Text preview should render <pre> block and truncate long content."""
    file_path = Path("config.yaml").resolve()
    html = build_preview_html(
        file_path,
        rel="config.yaml",
        lang="en",
        max_preview_chars=3,
    )
    assert "<pre class='log'>" in html
    assert "... [truncated]" in html


def test_build_preview_html_for_binary_fallback() -> None:
    """Unsupported file type should render no-inline-preview message."""
    file_path = Path("artifact.bin").resolve()
    html = build_preview_html(file_path, rel="outputs/artifact.bin", lang="en")
    assert "No inline preview for this file type" in html
