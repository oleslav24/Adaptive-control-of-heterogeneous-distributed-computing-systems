"""Unit tests for web API payload builders."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

import project.web.payloads as payloads


@dataclass
class _FakeJob:
    id: str = "job-1"
    status: str = "queued"
    started_at: datetime | None = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)
    command: list[str] = field(default_factory=lambda: ["python", "-m", "project.experiments.run"])

    def command_text(self) -> str:
        return " ".join(self.command)


class _FakeResearcher:
    def __init__(self) -> None:
        self.last_metrics: dict[str, list[float | int]] | None = None

    def analyze_metrics(
        self,
        metrics: dict[str, list[float | int]],
        *,
        lang: str,
        status: str,
        max_items: int,
    ) -> list[str]:
        self.last_metrics = metrics
        return [f"lang={lang}", f"status={status}", f"max={max_items}"]


def test_job_payload_localizes_runs_and_status(monkeypatch) -> None:
    """Payload should include localized run labels and status badge."""
    fake_researcher = _FakeResearcher()
    monkeypatch.setattr(payloads, "RESEARCHER_AGENT", fake_researcher)

    job = _FakeJob(
        log_lines=[
            "Simulation initialized: scenario=static algorithm=min-load",
            "t=0 queue=3 completed=0 latency=1.0 throughput=0.0 avg_load=0.2",
            "t=1 queue=2 completed=1 latency=0.9 throughput=1.0 avg_load=0.3",
        ]
    )
    result = payloads.job_payload(job, "ru")
    runs = result["metrics"]["runs"]
    assert isinstance(runs, list)
    assert runs[0]["scenario_label"] == "Статический"
    assert runs[0]["algorithm_label"] == "Минимальная нагрузка"
    assert "в очереди" in result["status_badge_html"]
    assert result["insights"] == ["lang=ru", "status=queued", "max=6"]


def test_job_payload_uses_last_run_for_researcher_analysis(monkeypatch) -> None:
    """When multiple runs are present, researcher receives the last run segment."""
    fake_researcher = _FakeResearcher()
    monkeypatch.setattr(payloads, "RESEARCHER_AGENT", fake_researcher)

    job = _FakeJob(
        log_lines=[
            "Simulation initialized: scenario=static algorithm=min-load",
            "t=0 queue=5 completed=0 latency=2.0 throughput=0.0 avg_load=0.4",
            "t=1 queue=4 completed=1 latency=1.8 throughput=1.0 avg_load=0.5",
            "Simulation initialized: scenario=peak-load algorithm=greedy",
            "t=0 queue=8 completed=0 latency=2.5 throughput=0.0 avg_load=0.7",
            "t=1 queue=7 completed=1 latency=2.2 throughput=1.0 avg_load=0.8",
        ]
    )
    result = payloads.job_payload(job, "en")
    assert result["status"] == "queued"
    assert fake_researcher.last_metrics is not None
    assert fake_researcher.last_metrics["time"] == [0, 1]
    assert fake_researcher.last_metrics["queue"] == [8, 7]
