"""Unit tests for web API payload builders."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import project.web.payloads as payloads


@dataclass
class _FakeJob:
    id: str = "job-1"
    status: str = "queued"
    started_at: datetime | None = datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc)
    finished_at: datetime | None = None
    return_code: int | None = None
    timeout_seconds: int | None = 3600
    timed_out: bool = False
    status_details: str = ""
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
    result = payloads.job_payload(job, "en")
    runs = result["metrics"]["runs"]
    assert isinstance(runs, list)
    assert runs[0]["scenario_label"] == "Static"
    assert runs[0]["algorithm_label"] == "Min-load"
    assert "queued" in result["status_badge_html"]
    assert result["insights"] == ["lang=en", "status=queued", "max=6"]
    assert result["status_details"] == "-"
    assert result["carbon_outcomes"] is None
    assert "claims" in result
    assert "claims_gate" in result


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


def test_job_payload_extracts_carbon_outcomes_from_artifact(monkeypatch) -> None:
    """Carbon-study payload should expose parsed carbon outcomes from CSV artifact."""
    fake_researcher = _FakeResearcher()
    monkeypatch.setattr(payloads, "RESEARCHER_AGENT", fake_researcher)

    artifact_dir = Path("outputs") / "test-suite" / f"web-payload-carbon-{uuid4().hex[:8]}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / "carbon_summary.csv"
    artifact.write_text(
        "\n".join(
            [
                "rank_co2,method,method_label,co2_per_completed_task_lb_mean,co2_total_lb_mean,delta_latency_vs_min_load,delta_throughput_vs_min_load,co2_per_task_reduction_vs_min_load_pct",
                "1,carbon-aware,Carbon-Aware,1.1000,120.0,0.050,-0.040,32.0",
                "2,min-load,Min-Load,1.6200,180.0,0.000,0.000,0.0",
            ]
        ),
        encoding="utf-8",
    )
    job = _FakeJob(
        command=["python", "-m", "project.experiments.run", "--carbon-study"],
        log_lines=[
            "Experiment 'demo' carbon study",
            f"carbon_summary_csv: {artifact}",
        ],
    )
    result = payloads.job_payload(job, "en")
    outcomes = result["carbon_outcomes"]
    assert isinstance(outcomes, dict)
    assert outcomes["available"] is True
    assert outcomes["best_method"] == "Carbon-Aware"
    assert outcomes["baseline_method"] == "Min-Load"
    assert outcomes["co2_per_task_lb"] == 1.1


def test_job_payload_includes_literature_evidence_payload(monkeypatch) -> None:
    """Job payload should include normalized literature evidence and quality gate."""
    fake_researcher = _FakeResearcher()
    monkeypatch.setattr(payloads, "RESEARCHER_AGENT", fake_researcher)

    folder = Path("outputs") / "test-suite" / f"web-payload-lit-{uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    pdf_a = (folder / "a.pdf").resolve()
    pdf_a.write_text("x", encoding="utf-8")
    pdf_b = (folder / "b.pdf").resolve()
    pdf_b.write_text("y", encoding="utf-8")

    monkeypatch.setattr(payloads, "build_query_from_metrics", lambda *args, **kwargs: "demo query")
    monkeypatch.setattr(
        payloads,
        "search_literature",
        lambda *args, **kwargs: {
            "available": True,
            "reason": "",
            "query": "demo query",
            "items": [
                {
                    "rank": 1,
                    "score": 0.41,
                    "article_id": "doc-1",
                    "title": "Doc 1",
                    "page": 2,
                    "pdf_path": str(pdf_a),
                    "snippet": "snippet 1",
                },
                {
                    "rank": 2,
                    "score": 0.32,
                    "article_id": "doc-2",
                    "title": "Doc 2",
                    "page": 5,
                    "pdf_path": str(pdf_b),
                    "snippet": "snippet 2",
                },
            ],
        },
    )

    job = _FakeJob(
        log_lines=[
            "Simulation initialized: scenario=dynamic-load algorithm=min-load",
            "t=0 queue=3 completed=0 latency=1.2 throughput=0.0 avg_load=0.4",
            "t=1 queue=2 completed=1 latency=1.0 throughput=1.0 avg_load=0.5",
        ]
    )
    result = payloads.job_payload(job, "en")

    evidence = result["literature_evidence"]
    gate = result["literature_evidence_gate"]
    claims = result["claims"]
    claims_gate = result["claims_gate"]
    assert evidence["available"] is True
    assert evidence["query"] == "demo query"
    assert len(evidence["items"]) == 2
    assert gate["ok"] is True
    assert gate["source_count"] == 2
    assert len(claims) >= 2
    assert claims[0]["hypothesis"] == "H1"
    assert claims[0]["evidence"][0]["article_id"] == "doc-1"
    assert claims_gate["ok"] is True
