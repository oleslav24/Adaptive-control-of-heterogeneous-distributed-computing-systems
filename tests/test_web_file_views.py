"""Unit tests for web file path and preview helpers."""

from pathlib import Path
import shutil

import pytest

from project.web.file_views import (
    build_directory_body,
    build_file_body,
    build_preview_html,
    read_download_payload,
    rel_workspace,
    resolve_path,
)


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


def test_build_directory_body_renders_entries_and_parent_link() -> None:
    """Directory page body includes child entries and parent navigation."""
    workspace_root = (Path("outputs") / "__test_web_file_views_dir").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        directory = workspace_root / "outputs"
        nested_dir = directory / "charts"
        nested_dir.mkdir(parents=True, exist_ok=True)
        report_file = directory / "report.txt"
        report_file.write_text("ok", encoding="utf-8")

        html = build_directory_body(
            directory,
            rel="outputs",
            lang="en",
            workspace_root=workspace_root,
        )
        assert "report.txt" in html
        assert "charts" in html
        assert "href='/files?lang=en&amp;path=outputs%2Fcharts'" in html
        assert "href='/files?lang=en&amp;path=.'" in html
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_build_file_body_renders_navigation_and_preview() -> None:
    """File page body includes nav links and inline preview block."""
    workspace_root = (Path("outputs") / "__test_web_file_views_file").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        file_path = workspace_root / "outputs" / "run.log"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("line-1", encoding="utf-8")

        html = build_file_body(
            file_path,
            rel="outputs/run.log",
            lang="en",
            workspace_root=workspace_root,
        )
        assert "href=\"/?lang=en\"" in html
        assert "href=\"/files?lang=en&amp;path=outputs\"" in html
        assert "href=\"/download?lang=en&amp;path=outputs%2Frun.log\"" in html
        assert "<pre class='log'>" in html
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_read_download_payload_guesses_type_and_reads_bytes() -> None:
    """Download payload helper should infer mime type and return file bytes."""
    workspace_root = (Path("outputs") / "__test_web_file_views_download").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        file_path = workspace_root / "sample.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello", encoding="utf-8")

        content_type, payload = read_download_payload(file_path)
        assert content_type == "text/plain"
        assert payload == b"hello"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)
