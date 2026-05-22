"""Regression tests for publication artifact export helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.experiments import publication as pub


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _sample_tables() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Build minimal publication tables for artifact persistence tests."""
    raw_runs = pd.DataFrame(
        [
            {
                "study_id": "E1_scalability",
                "scenario": "static",
                "node_count": 10,
                "task_count": 100,
                "task_type": "mixed",
                "network_profile": "medium",
                "topology": "ring",
                "seed": 42,
                "method": "min-load",
                "method_label": "Min-Load",
                "method_family": "baseline",
                "algorithm": "min-load",
                "completed_tasks": 100,
                "pending_tasks": 0,
                "makespan": 44.0,
                "avg_latency": 1.2,
                "latency_p95": 2.0,
                "load_imbalance": 0.2,
                "sla_violations": 1,
                "throughput": 2.5,
                "resource_utilization": 0.68,
                "adaptivity": 0.11,
                "stability_latency_var": 0.02,
                "stability_throughput_var": 0.03,
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "study_id": "E1_scalability",
                "scenario": "static",
                "method": "min-load",
                "method_label": "Min-Load",
                "method_family": "baseline",
                "node_count": 10,
                "task_count": 100,
                "n_runs": 1,
                "avg_latency_mean": 1.2,
            }
        ]
    )
    hypotheses = pd.DataFrame(
        [
            {"hypothesis": "H1", "title": "Adaptivity", "criterion": "c", "confirmed": True},
            {"hypothesis": "H2", "title": "MAS", "criterion": "c", "confirmed": False},
            {"hypothesis": "H3", "title": "ML/ZNN", "criterion": "c", "confirmed": True},
            {"hypothesis": "H4", "title": "Hybrid", "criterion": "c", "confirmed": True},
            {"hypothesis": "H5", "title": "LLM", "criterion": "c", "confirmed": True},
        ]
    )
    methods = pd.DataFrame(
        [
            {"key": "min-load", "label": "Min-Load", "family": "baseline", "ready": True},
            {"key": "abc", "label": "ABC", "family": "metaheuristic", "ready": False},
        ]
    )
    unsupported = methods[methods["ready"] == False].copy()  # noqa: E712
    decision_trace = pd.DataFrame(
        [
            {
                "study_id": "E1_scalability",
                "scenario": "static",
                "seed": 42,
                "method": "min-load",
                "time": 0,
                "agent": "optimization",
                "event": "algorithm_policy",
                "selected_algorithm": "min-load",
            }
        ]
    )
    return raw_runs, summary, hypotheses, methods, unsupported, decision_trace


def test_persist_publication_outputs_writes_expected_files() -> None:
    """Exporter should persist all base CSV/JSON publication artifacts."""
    output_dir = _workspace_test_output_dir("publication-artifacts")
    raw_runs, summary, hypotheses, methods, unsupported, decision_trace = _sample_tables()

    output_paths = pub._persist_publication_outputs(  # noqa: SLF001
        output_dir=output_dir,
        raw_runs=raw_runs,
        summary=summary,
        hypotheses=hypotheses,
        methods_df=methods,
        unsupported_df=unsupported,
        decision_trace=decision_trace,
        save_plots=False,
    )

    required = {
        "raw_runs_csv",
        "summary_csv",
        "hypotheses_csv",
        "methods_catalog_csv",
        "unsupported_methods_csv",
        "decision_trace_csv",
        "raw_runs_json",
        "summary_json",
        "hypotheses_json",
        "methods_catalog_json",
        "decision_trace_json",
    }
    assert required.issubset(set(output_paths.keys()))
    for key in required:
        assert Path(output_paths[key]).exists(), key


def test_write_publication_report_contains_required_sections() -> None:
    """Markdown publication report should include expected section headings."""
    output_dir = _workspace_test_output_dir("publication-report")
    raw_runs, summary, hypotheses, methods, _unsupported, _decision_trace = _sample_tables()
    report_path = pub._write_publication_report(  # noqa: SLF001
        output_dir=output_dir,
        summary=summary,
        hypotheses=hypotheses,
        methods_df=methods,
        seed_count=3,
        quick_mode=True,
    )
    content = report_path.read_text(encoding="utf-8")
    assert "# Experimental Study Report" in content
    assert "## 1. Experimental Setup" in content
    assert "## 2. Compared Methods" in content
    assert "## 3. Metrics" in content
    assert "## 4. Results" in content
    assert "### Carbon-Performance Interpretation" in content
    assert "### Related Literature Evidence (Local RAG)" in content
    assert "### Evidence-backed Claims" in content
    assert "## 5. Hypotheses" in content
    assert "### Hypothesis Support Status" in content
    assert "`H1` `supported`" in content
    assert "`H2` `not-supported`" in content
    assert "## 6. Threats to Validity" in content
    assert "E6` results are reported separately" in content
    assert "## 7. Monograph Alignment" in content
    assert "docs/monograph_alignment.md" in content
    assert "## 8. Known Gaps / Future Work" in content
    assert "Seed count: 3" in content
    assert "Quick mode: True" in content
    gate_path = output_dir / "literature_evidence_gate.json"
    claims_path = output_dir / "claims_report.json"
    assert gate_path.exists()
    assert claims_path.exists()
    assert "report-H1" in claims_path.read_text(encoding="utf-8")
    assert not raw_runs.empty


def test_persist_publication_outputs_writes_carbon_summary_when_available() -> None:
    """Exporter should persist carbon summary artifacts when carbon metrics are present."""
    output_dir = _workspace_test_output_dir("publication-carbon-summary")
    raw_runs, summary, hypotheses, methods, unsupported, decision_trace = _sample_tables()
    summary = pd.DataFrame(
        [
            {
                "study_id": "E6_carbon_vs_performance",
                "scenario": "dynamic-load",
                "method": "min-load",
                "method_label": "Min-Load",
                "method_family": "baseline",
                "node_count": 50,
                "task_count": 300,
                "n_runs": 3,
                "avg_latency_mean": 1.20,
                "throughput_mean": 2.10,
                "co2_total_lb_mean": 210.0,
                "co2_per_completed_task_lb_mean": 2.10,
            },
            {
                "study_id": "E6_carbon_vs_performance",
                "scenario": "dynamic-load",
                "method": "carbon-aware",
                "method_label": "Carbon-Aware",
                "method_family": "baseline",
                "node_count": 50,
                "task_count": 300,
                "n_runs": 3,
                "avg_latency_mean": 1.35,
                "throughput_mean": 2.00,
                "co2_total_lb_mean": 150.0,
                "co2_per_completed_task_lb_mean": 1.50,
            },
        ]
    )

    output_paths = pub._persist_publication_outputs(  # noqa: SLF001
        output_dir=output_dir,
        raw_runs=raw_runs,
        summary=summary,
        hypotheses=hypotheses,
        methods_df=methods,
        unsupported_df=unsupported,
        decision_trace=decision_trace,
        save_plots=False,
    )

    assert "carbon_summary_csv" in output_paths
    assert "carbon_summary_json" in output_paths
    assert Path(output_paths["carbon_summary_csv"]).exists()
    assert Path(output_paths["carbon_summary_json"]).exists()

