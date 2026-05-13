"""Simple web interface for controlling experiment runs and browsing artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from project.web.jobs import JobManager, RunJob
from project.web.payloads import job_payload as _job_payload
from project.web.request_handlers import (
    build_get_response as _build_get_response,
    build_post_response as _build_post_response,
)
from project.web.route_responses import RouteResponse as _RouteResponse


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
        response = _build_get_response(
            parsed,
            self.job_manager,
            workspace_root=WORKSPACE_ROOT,
            default_config=DEFAULT_CONFIG,
            payload_builder=_job_payload,
        )
        self._send_route_response(response)

    def do_POST(self) -> None:  # noqa: N802
        """Route POST requests."""
        parsed = urlparse(self.path)
        form = self._parse_form()
        response = _build_post_response(
            parsed,
            form,
            self.job_manager,
            workspace_root=WORKSPACE_ROOT,
            default_config=DEFAULT_CONFIG,
        )
        self._send_route_response(response)

    def _parse_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return parse_qs(raw, keep_blank_values=True)

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


