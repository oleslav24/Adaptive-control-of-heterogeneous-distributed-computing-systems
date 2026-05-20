"""Tests for Chapter 10 experiment package pipeline."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.core.config import load_config
from project.experiments import chapter10
from project.experiments.cli import parse_args
from project.experiments.dispatch import resolve_mode
from project.experiments.publication import StudyResult


def test_resolve_mode_selects_chapter10() -> None:
    """CLI mode resolver should route --chapter10 to chapter10-study mode."""
    args = parse_args(["--chapter10"])
    assert resolve_mode(args) == "chapter10-study"


def test_load_config_parses_chapter10_section() -> None:
    """Base config should expose parsed chapter10 and energy settings."""
    config = load_config("config.yaml")
    assert config.chapter10.enabled is False
    assert config.chapter10.quick is False
    assert config.chapter10.save_plots is True
    assert config.chapter10.seeds[:3] == [42, 43, 44]
    assert config.energy.enabled is True
    assert config.energy.egrid_level == "srl"
    assert config.energy.egrid_dataset_path.endswith("eGRID2021_data.xlsx")
    assert config.nodes[0].egrid_subregion == "CAMX"
    assert config.carbon_study.enabled is False
    assert config.carbon_study.quick is False
    assert config.carbon_study.study_ids == ["E6_carbon_vs_performance"]


def test_run_chapter10_experiment_persists_outputs(monkeypatch) -> None:
    """Chapter10 pipeline should persist tables/report/manifest/integrity artifacts."""
    workspace = _workspace_dir("chapter10")
    output_root = workspace / "outputs"
    publication_out = output_root / "pub"
    publication_out.mkdir(parents=True, exist_ok=True)
    publication_stub = publication_out / "publication_stub.txt"
    publication_stub.write_text("ok", encoding="utf-8")

    def _fake_publication_pipeline(*, base_config, seeds, quick, save_plots, cli_args):
        _ = base_config
        _ = seeds
        _ = quick
        _ = save_plots
        _ = cli_args
        raw_runs = pd.DataFrame(
            [
                {
                    "scenario": "static",
                    "method": "min-load",
                    "avg_latency": 1.1,
                    "throughput": 2.3,
                    "sla_violations": 0,
                    "load_imbalance": 0.2,
                },
                {
                    "scenario": "dynamic-load",
                    "method": "greedy",
                    "avg_latency": 1.4,
                    "throughput": 2.0,
                    "sla_violations": 1,
                    "load_imbalance": 0.4,
                },
            ]
        )
        summary = pd.DataFrame(
            [
                {
                    "study_id": "E1_scalability",
                    "method": "min-load",
                    "node_count": 10,
                    "avg_latency_mean": 1.1,
                    "throughput_mean": 2.3,
                    "load_imbalance_mean": 0.2,
                },
                {
                    "study_id": "E1_scalability",
                    "method": "greedy",
                    "node_count": 50,
                    "avg_latency_mean": 1.4,
                    "throughput_mean": 2.0,
                    "load_imbalance_mean": 0.4,
                },
            ]
        )
        hypotheses = pd.DataFrame(
            [
                {"hypothesis": "H1", "title": "Adaptivity", "confirmed": True},
                {"hypothesis": "H2", "title": "MAS", "confirmed": True},
            ]
        )
        return StudyResult(
            output_dir=publication_out,
            raw_runs=raw_runs,
            summary=summary,
            hypothesis_df=hypotheses,
            methods_df=pd.DataFrame(),
            output_paths={"publication_stub_txt": str(publication_stub)},
        )

    monkeypatch.setattr(chapter10, "run_publication_pipeline", _fake_publication_pipeline)

    config = load_config("config.yaml")
    config = replace(
        config,
        name=f"chapter10-test-{uuid4().hex[:6]}",
        observability=replace(
            config.observability,
            output_dir=str(output_root),
            save_plots=False,
        ),
    )

    result = chapter10.run_chapter10_experiment(
        config,
        seeds=[42, 43],
        quick=True,
        save_plots=False,
        cli_args=["--chapter10"],
    )
    required_keys = {
        "method_ranking_csv",
        "method_ranking_json",
        "scenario_overview_csv",
        "scenario_overview_json",
        "hypotheses_csv",
        "hypotheses_json",
        "chapter10_report_md",
        "chapter10_manifest_json",
        "chapter10_artifact_integrity_json",
        "publication_publication_stub_txt",
    }
    assert required_keys.issubset(set(result.output_paths.keys()))
    for key in required_keys:
        assert Path(result.output_paths[key]).exists(), key

    report_text = Path(result.output_paths["chapter10_report_md"]).read_text(encoding="utf-8")
    assert "## Carbon Interpretation" in report_text
    assert "## Related Literature Evidence (Local RAG)" in report_text
    assert "chapter10_literature_evidence_gate_json" in result.output_paths
    assert Path(result.output_paths["chapter10_literature_evidence_gate_json"]).exists()

    manifest_path = Path(result.output_paths["chapter10_manifest_json"])
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["mode"] == "chapter10-study"


def _workspace_dir(suffix: str) -> Path:
    """Create a unique test workspace directory under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
