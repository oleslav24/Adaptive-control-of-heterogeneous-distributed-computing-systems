"""Unit tests for web job route response builders."""

from http import HTTPStatus
import json
from urllib.parse import urlparse

from project.web.job_routes import build_job_data_response


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class _FakeJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, _FakeJob] = {}

    def add(self, job: _FakeJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str):
        return self._jobs.get(job_id)


def test_build_job_data_response_returns_not_found_payload() -> None:
    """Missing job should return localized JSON error response."""
    manager = _FakeJobManager()
    parsed = urlparse("/job-data?id=missing")

    response = build_job_data_response(
        parsed,
        manager,
        payload_builder=lambda _job, _lang: {},
    )
    assert response.status == HTTPStatus.NOT_FOUND
    assert response.content_type == "application/json; charset=utf-8"
    assert response.headers["Cache-Control"] == "no-store"
    assert json.loads(response.body.decode("utf-8")) == {"error": "Job not found."}


def test_build_job_data_response_returns_payload_for_existing_job() -> None:
    """Existing job should return payload from provided builder."""
    manager = _FakeJobManager()
    manager.add(_FakeJob("job-42"))
    parsed = urlparse("/job-data?id=job-42&lang=ru")

    response = build_job_data_response(
        parsed,
        manager,
        payload_builder=lambda job, lang: {"id": job.id, "lang": lang, "status": "queued"},
    )
    assert response.status == HTTPStatus.OK
    assert response.content_type == "application/json; charset=utf-8"
    assert response.headers["Cache-Control"] == "no-store"
    assert json.loads(response.body.decode("utf-8")) == {
        "id": "job-42",
        "lang": "ru",
        "status": "queued",
    }
