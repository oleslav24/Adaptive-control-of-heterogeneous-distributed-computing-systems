"""End-to-end HTTP integration tests for the modular web app."""

from __future__ import annotations

from contextlib import contextmanager
import http.client
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
import time
from typing import Iterator
from urllib.parse import parse_qs, urlencode, urlparse

from project.web import app as web_app
from project.web.i18n import tr
from project.web.jobs import JobManager
from project.web import run_routes


def _request(
    host: str,
    port: int,
    method: str,
    path: str,
    *,
    form: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """Send one HTTP request to local test server and return full response."""
    headers: dict[str, str] = {}
    body = ""
    if form is not None:
        body = urlencode(form)
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    connection = http.client.HTTPConnection(host, port, timeout=10)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        response_headers = {name: value for name, value in response.getheaders()}
        return response.status, response_headers, data
    finally:
        connection.close()


def _wait_until(predicate, *, timeout_seconds: float = 5.0) -> bool:
    """Wait for predicate to return True until timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


@contextmanager
def _running_server(
    manager: JobManager,
    *,
    workspace_root: Path,
) -> Iterator[tuple[str, int]]:
    """Run web server in background thread for integration tests."""
    had_job_manager = hasattr(web_app.WebHandler, "job_manager")
    previous_job_manager = getattr(web_app.WebHandler, "job_manager", None)
    previous_workspace_root = web_app.WORKSPACE_ROOT
    web_app.WebHandler.job_manager = manager
    web_app.WORKSPACE_ROOT = workspace_root

    server = web_app.ExperimentWebServer(("127.0.0.1", 0), web_app.WebHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield str(host), int(port)
    finally:
        for job in manager.list_jobs():
            job.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        web_app.WORKSPACE_ROOT = previous_workspace_root
        if had_job_manager:
            web_app.WebHandler.job_manager = previous_job_manager
        else:
            delattr(web_app.WebHandler, "job_manager")


def _extract_job_id(location: str) -> str:
    """Extract job id query parameter from redirect location."""
    query = parse_qs(urlparse(location).query)
    job_ids = query.get("id", [])
    assert job_ids
    return str(job_ids[0])


def _workspace_dir(name: str) -> Path:
    """Create clean per-test workspace inside repository outputs folder."""
    workspace = (Path("outputs") / name).resolve()
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_web_http_routes_for_dashboard_files_and_download() -> None:
    """Server should serve core GET routes through real HTTP stack."""
    workspace = _workspace_dir("__test_web_app_integration_routes")
    try:
        outputs = workspace / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        (outputs / "sample.txt").write_text("sample-data", encoding="utf-8")
        manager = JobManager()

        with _running_server(manager, workspace_root=workspace) as (host, port):
            status, _headers, body = _request(host, port, "GET", "/health")
            assert status == 200
            assert body == b"ok"

            status, _headers, body = _request(host, port, "GET", "/?lang=ru")
            assert status == 200
            html = body.decode("utf-8")
            assert tr("ru", "console_title") in html

            status, _headers, body = _request(host, port, "GET", "/files?lang=ru&path=outputs")
            assert status == 200
            assert "sample.txt" in body.decode("utf-8")

            status, headers, body = _request(host, port, "GET", "/download?path=outputs/sample.txt")
            assert status == 200
            assert headers["Content-Disposition"] == "inline; filename=sample.txt"
            assert body == b"sample-data"

            status, _headers, body = _request(host, port, "GET", "/missing?lang=en")
            assert status == 404
            assert body.decode("utf-8") == tr("en", "not_found")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_web_http_run_route_produces_job_and_metrics_payload(monkeypatch) -> None:
    """`/run` -> `/job` -> `/job-data` should work end-to-end via HTTP."""

    def _fake_command_builder(_form, *, default_config: str) -> list[str]:
        _ = default_config
        inline = (
            "print('Simulation initialized: scenario=static algorithm=round-robin', flush=True);"
            "print('t=0 queue=3 completed=0 latency=1.200 throughput=0.000 avg_load=0.400', flush=True);"
            "print('t=1 queue=1 completed=2 latency=0.800 throughput=2.000 avg_load=0.500', flush=True)"
        )
        return [sys.executable, "-c", inline]

    monkeypatch.setattr(run_routes, "build_run_command", _fake_command_builder)
    workspace = _workspace_dir("__test_web_app_integration_run")
    try:
        (workspace / "config.yaml").write_text("name: web-test\n", encoding="utf-8")
        manager = JobManager()

        with _running_server(manager, workspace_root=workspace) as (host, port):
            status, headers, _body = _request(
                host,
                port,
                "POST",
                "/run",
                form={"lang": "en", "mode": "single", "config": "config.yaml"},
            )
            assert status == 303
            location = headers["Location"]
            assert location.startswith("/job?lang=en&id=")
            job_id = _extract_job_id(location)

            assert _wait_until(
                lambda: (manager.get(job_id) is not None and manager.get(job_id).status in {"success", "failed"}),
                timeout_seconds=5,
            )

            status, _headers, body = _request(host, port, "GET", location)
            assert status == 200
            assert f"job {job_id}".lower() in body.decode("utf-8").lower()

            status, _headers, body = _request(host, port, "GET", f"/job-data?id={job_id}&lang=en")
            assert status == 200
            payload = json.loads(body.decode("utf-8"))
            assert payload["id"] == job_id
            assert payload["status"] == "success"
            assert payload["metrics"]["time"] == [0, 1]
            assert payload["metrics"]["queue"] == [3, 1]
            assert payload["metrics"]["throughput"] == [0.0, 2.0]
            assert isinstance(payload["insights"], list)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_web_http_stop_route_stops_running_job(monkeypatch) -> None:
    """`/stop` should terminate running process and append stop marker."""

    def _fake_command_builder(_form, *, default_config: str) -> list[str]:
        _ = default_config
        inline = (
            "import time;"
            "print('Simulation initialized: scenario=peak algorithm=min-load', flush=True);"
            "time.sleep(30)"
        )
        return [sys.executable, "-c", inline]

    monkeypatch.setattr(run_routes, "build_run_command", _fake_command_builder)
    workspace = _workspace_dir("__test_web_app_integration_stop")
    try:
        (workspace / "config.yaml").write_text("name: web-test\n", encoding="utf-8")
        manager = JobManager()

        with _running_server(manager, workspace_root=workspace) as (host, port):
            status, headers, _body = _request(
                host,
                port,
                "POST",
                "/run",
                form={"lang": "ru", "mode": "single", "config": "config.yaml"},
            )
            assert status == 303
            location = headers["Location"]
            job_id = _extract_job_id(location)

            assert _wait_until(
                lambda: (manager.get(job_id) is not None and manager.get(job_id).process is not None),
                timeout_seconds=5,
            )

            status, headers, _body = _request(
                host,
                port,
                "POST",
                "/stop",
                form={"lang": "ru", "id": job_id},
            )
            assert status == 303
            assert headers["Location"] == f"/job?lang=ru&id={job_id}"

            assert _wait_until(
                lambda: (manager.get(job_id) is not None and manager.get(job_id).status == "stopped"),
                timeout_seconds=5,
            )

            status, _headers, body = _request(host, port, "GET", f"/job-data?id={job_id}&lang=ru")
            assert status == 200
            payload = json.loads(body.decode("utf-8"))
            assert payload["status"] == "stopped"
            assert "[web-ui] stop requested." in payload["log_text"]
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_web_http_run_route_rejects_invalid_request() -> None:
    """`/run` should return HTTP 400 for invalid server-side validated payload."""
    workspace = _workspace_dir("__test_web_app_integration_invalid_run")
    try:
        manager = JobManager()
        with _running_server(manager, workspace_root=workspace) as (host, port):
            status, _headers, body = _request(
                host,
                port,
                "POST",
                "/run",
                form={"lang": "en", "mode": "single", "config": "missing.yaml"},
            )
            assert status == 400
            assert b"Invalid request:" in body
            assert manager.list_jobs() == []
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_web_http_failed_job_exposes_diagnostics_and_bundle(monkeypatch) -> None:
    """Failed job should expose diagnostics JSON and downloadable zip bundle."""

    def _failing_command_builder(_form, *, default_config: str) -> list[str]:
        _ = default_config
        inline = (
            "print('Simulation initialized: scenario=static algorithm=min-load', flush=True);"
            "print('fatal error', flush=True);"
            "raise SystemExit(4)"
        )
        return [sys.executable, "-c", inline]

    monkeypatch.setattr(run_routes, "build_run_command", _failing_command_builder)
    workspace = _workspace_dir("__test_web_app_integration_diagnostics")
    try:
        (workspace / "config.yaml").write_text("name: web-test\n", encoding="utf-8")
        manager = JobManager()
        with _running_server(manager, workspace_root=workspace) as (host, port):
            status, headers, _body = _request(
                host,
                port,
                "POST",
                "/run",
                form={"lang": "en", "mode": "single", "config": "config.yaml"},
            )
            assert status == 303
            job_id = _extract_job_id(headers["Location"])

            assert _wait_until(
                lambda: (manager.get(job_id) is not None and manager.get(job_id).status in {"failed", "timeout"}),
                timeout_seconds=5,
            )

            status, _headers, body = _request(host, port, "GET", f"/job-diagnostics?id={job_id}&lang=en")
            assert status == 200
            payload = json.loads(body.decode("utf-8"))
            assert payload["id"] == job_id
            assert payload["can_export_bundle"] is True
            assert payload["status"] in {"failed", "timeout"}

            status, headers, body = _request(host, port, "GET", f"/job-bundle?id={job_id}&lang=en")
            assert status == 200
            assert headers.get("Content-Disposition", "").endswith(".zip")
            assert body[:2] == b"PK"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
