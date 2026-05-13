"""Unit tests for normalized route response helpers."""

from http import HTTPStatus
import json

from project.web.route_responses import (
    html_response,
    json_response,
    redirect_response,
    text_response,
)


def test_text_response_encodes_utf8_text() -> None:
    """Text helper should emit UTF-8 bytes and plain-text content type."""
    response = text_response(HTTPStatus.BAD_REQUEST, "bad input")
    assert response.status == HTTPStatus.BAD_REQUEST
    assert response.content_type == "text/plain; charset=utf-8"
    assert response.body == b"bad input"
    assert response.headers == {}


def test_html_response_encodes_markup() -> None:
    """HTML helper should emit UTF-8 bytes and HTML content type."""
    response = html_response(HTTPStatus.OK, "<h1>ok</h1>")
    assert response.status == HTTPStatus.OK
    assert response.content_type == "text/html; charset=utf-8"
    assert response.body == b"<h1>ok</h1>"
    assert response.headers == {}


def test_json_response_sets_cache_header_and_keeps_payload() -> None:
    """JSON helper should include cache header and keep payload values."""
    response = json_response(HTTPStatus.OK, {"message": "hello"})
    assert response.status == HTTPStatus.OK
    assert response.content_type == "application/json; charset=utf-8"
    assert response.headers["Cache-Control"] == "no-store"
    payload = json.loads(response.body.decode("utf-8"))
    assert payload == {"message": "hello"}


def test_redirect_response_sets_location_header() -> None:
    """Redirect helper should produce SEE_OTHER with Location header."""
    response = redirect_response("/job?lang=en&id=job-1")
    assert response.status == HTTPStatus.SEE_OTHER
    assert response.content_type == "text/plain; charset=utf-8"
    assert response.body == b""
    assert response.headers["Location"] == "/job?lang=en&id=job-1"
