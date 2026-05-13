"""Simple web interface for controlling experiment runs and browsing artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from project.web.dashboard_routes import build_dashboard_response as _build_dashboard_response
from project.web.file_routes import (
    build_download_response as _build_download_response,
    build_files_response as _build_files_response,
)
from project.web.i18n import (
    tr as _tr,
)
from project.web.job_page_routes import build_job_page_response as _build_job_page_response
from project.web.job_routes import build_job_data_response as _build_job_data_response
from project.web.jobs import JobManager, RunJob
from project.web.payloads import job_payload as _job_payload
from project.web.route_responses import RouteResponse as _RouteResponse
from project.web.run_routes import (
    build_start_run_response as _build_start_run_response,
    build_stop_run_response as _build_stop_run_response,
)
from project.web.routing import (
    lang_from_form as _lang_from_form,
    lang_from_parsed as _lang_from_parsed,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "config.yaml"
DEFAULT_PORT = 8080
DEFAULT_HOST = "127.0.0.1"


class ExperimentWebServer(ThreadingHTTPServer):
    """Threaded HTTP server with reusable socket and daemon workers."""

    daemon_threads = True
    allow_reuse_address = True


class WebHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard, job control, and artifact browsing."""

    job_manager: ClassVar[JobManager]
    server_version = "TestbedWeb/1.0"

    def do_GET(self) -> None:  # noqa: N802
        """Route GET requests."""
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_dashboard(parsed)
            return
        if parsed.path == "/job":
            self._serve_job(parsed)
            return
        if parsed.path == "/job-data":
            self._serve_job_data(parsed)
            return
        if parsed.path == "/files":
            self._serve_files(parsed)
            return
        if parsed.path == "/download":
            self._serve_download(parsed)
            return
        if parsed.path == "/health":
            self._send_text(HTTPStatus.OK, "ok")
            return
        lang = _lang_from_parsed(parsed)
        self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "not_found"))

    def do_POST(self) -> None:  # noqa: N802
        """Route POST requests."""
        parsed = urlparse(self.path)
        form = self._parse_form()
        if parsed.path == "/run":
            self._start_run(form)
            return
        if parsed.path == "/stop":
            self._stop_run(form)
            return
        lang = _lang_from_form(form)
        self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "not_found"))

    def _serve_dashboard(self, parsed) -> None:
        response = _build_dashboard_response(
            parsed,
            self.job_manager,
            workspace_root=WORKSPACE_ROOT,
            default_config=DEFAULT_CONFIG,
        )
        self._send_route_response(response)

    def _serve_job(self, parsed) -> None:
        response = _build_job_page_response(parsed, self.job_manager)
        self._send_route_response(response)

    def _serve_job_data(self, parsed) -> None:
        """Return JSON payload with live job status, logs, and chart metrics."""
        response = _build_job_data_response(
            parsed,
            self.job_manager,
            payload_builder=_job_payload,
        )
        self._send_route_response(response)

    def _serve_files(self, parsed) -> None:
        response = _build_files_response(parsed, workspace_root=WORKSPACE_ROOT)
        self._send_route_response(response)

    def _serve_download(self, parsed) -> None:
        response = _build_download_response(parsed, workspace_root=WORKSPACE_ROOT)
        self._send_route_response(response)

    def _start_run(self, form: dict[str, list[str]]) -> None:
        response = _build_start_run_response(
            form,
            self.job_manager,
            workspace_root=WORKSPACE_ROOT,
            default_config=DEFAULT_CONFIG,
        )
        self._send_route_response(response)

    def _stop_run(self, form: dict[str, list[str]]) -> None:
        response = _build_stop_run_response(form, self.job_manager)
        self._send_route_response(response)

    def _parse_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return parse_qs(raw, keep_blank_values=True)

    def _send_text(self, status: HTTPStatus, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_route_response(self, response: _RouteResponse) -> None:
        """Send normalized route response payload."""
        self.send_response(int(response.status))
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format: str, *args) -> None:
        """Silence routine access logs to keep console output clean."""
        return


def _build_parser() -> ArgumentParser:
    """Create CLI parser for web app startup."""
    parser = ArgumentParser(description="Run local web UI for experiment testbed.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port.")
    return parser


def main() -> None:
    """Start threaded HTTP server for web interface."""
    args = _build_parser().parse_args()
    manager = JobManager()
    WebHandler.job_manager = manager
    server = ExperimentWebServer((str(args.host), int(args.port)), WebHandler)
    print(f"[web-ui] running at http://{args.host}:{args.port}")
    print(f"[web-ui] workspace: {WORKSPACE_ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()


