"""Unit tests for web file route response builders."""

from http import HTTPStatus
from pathlib import Path
import shutil
from urllib.parse import urlparse

from project.web.file_routes import build_download_response, build_files_response


def test_build_files_response_rejects_workspace_escape() -> None:
    """Path traversal outside workspace should return BAD_REQUEST."""
    workspace_root = Path(".").resolve()
    parsed = urlparse("/files?path=../outside.txt")
    response = build_files_response(parsed, workspace_root=workspace_root)
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == "text/plain; charset=utf-8"
    assert b"within workspace root" in response.body


def test_build_files_response_not_found_for_missing_path() -> None:
    """Missing path should produce localized not-found text response."""
    workspace_root = Path(".").resolve()
    parsed = urlparse("/files?path=outputs/no-such-dir")
    response = build_files_response(parsed, workspace_root=workspace_root)
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == "text/plain; charset=utf-8"
    assert response.body.decode("utf-8") == "Path does not exist."


def test_build_files_response_for_directory_listing() -> None:
    """Directory route should render HTML with entries from target folder."""
    workspace_root = (Path("outputs") / "__test_web_file_routes_dir").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        target_dir = workspace_root / "outputs"
        target_subdir = target_dir / "charts"
        target_subdir.mkdir(parents=True, exist_ok=True)
        (target_dir / "report.txt").write_text("ok", encoding="utf-8")

        parsed = urlparse("/files?path=outputs")
        response = build_files_response(parsed, workspace_root=workspace_root)
        html = response.body.decode("utf-8")
        assert response.status == HTTPStatus.OK
        assert response.content_type == "text/html; charset=utf-8"
        assert "report.txt" in html
        assert "charts" in html
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_build_files_response_for_single_file_page() -> None:
    """File route should render HTML details and download link."""
    workspace_root = (Path("outputs") / "__test_web_file_routes_file").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        target_file = workspace_root / "outputs" / "run.log"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("line-1", encoding="utf-8")

        parsed = urlparse("/files?path=outputs/run.log")
        response = build_files_response(parsed, workspace_root=workspace_root)
        html = response.body.decode("utf-8")
        assert response.status == HTTPStatus.OK
        assert response.content_type == "text/html; charset=utf-8"
        assert "/download?lang=en&amp;path=outputs%2Frun.log" in html
        assert "<pre class='log'>" in html
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_build_download_response_for_file() -> None:
    """Download route should return bytes with content-disposition header."""
    workspace_root = (Path("outputs") / "__test_web_file_routes_download").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        target_file = workspace_root / "outputs" / "metrics.txt"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("sample", encoding="utf-8")

        parsed = urlparse("/download?path=outputs/metrics.txt")
        response = build_download_response(parsed, workspace_root=workspace_root)
        assert response.status == HTTPStatus.OK
        assert response.content_type == "text/plain"
        assert response.body == b"sample"
        assert response.headers["Content-Disposition"] == "inline; filename=metrics.txt"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_build_download_response_for_missing_or_directory_path() -> None:
    """Missing file or directory download target should return NOT_FOUND."""
    workspace_root = (Path("outputs") / "__test_web_file_routes_missing").resolve()
    try:
        shutil.rmtree(workspace_root, ignore_errors=True)
        target_dir = workspace_root / "outputs"
        target_dir.mkdir(parents=True, exist_ok=True)

        missing = build_download_response(
            urlparse("/download?path=outputs/missing.txt"),
            workspace_root=workspace_root,
        )
        as_dir = build_download_response(
            urlparse("/download?path=outputs"),
            workspace_root=workspace_root,
        )
        assert missing.status == HTTPStatus.NOT_FOUND
        assert as_dir.status == HTTPStatus.NOT_FOUND
        assert missing.body.decode("utf-8") == "File not found."
        assert as_dir.body.decode("utf-8") == "File not found."
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)
