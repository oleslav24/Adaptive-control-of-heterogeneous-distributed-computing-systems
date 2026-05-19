"""Unit tests for experiment CLI parser schema."""

from __future__ import annotations

from project.experiments.cli import parse_args


def test_parse_args_defaults() -> None:
    """Parser should keep expected defaults for all top-level modes."""
    args = parse_args([])
    assert args.config == "config.yaml"
    assert args.algorithm is None
    assert args.scenario is None
    assert args.disable_intelligence is False
    assert args.disable_llm is False
    assert args.compare is False
    assert args.batch is False
    assert args.batch_runs == 3
    assert args.repro_check is False
    assert args.repro_runs == 3
    assert args.replay_manifest is None
    assert args.replay_runs == 3
    assert args.publication_study is False
    assert args.carbon_study is False
    assert args.carbon_seeds is None
    assert args.carbon_quick is False
    assert args.chapter10 is False
    assert args.chapter10_seeds is None
    assert args.chapter10_quick is False
    assert args.paper_bundle is False
    assert args.paper_bundle_name == "paper_bundle"
    assert args.scalability_profile is False
    assert args.scalability_nodes == "10,50,100,500"
    assert args.scalability_tasks == "100,500,1000,5000"
    assert args.scalability_runs == 1
    assert args.scalability_algorithms is None
    assert args.scalability_topology == "ring"
    assert args.scalability_keep_adaptive is False
    assert args.study_seeds == "42-71"
    assert args.study_quick is False


def test_parse_args_mode_flags_and_overrides() -> None:
    """Parser should correctly parse flags and override values."""
    args = parse_args(
        [
            "--config",
            "custom.yaml",
            "--algorithm",
            "min-load",
            "--scenario",
            "dynamic-load",
            "--disable-intelligence",
            "--disable-llm",
            "--llm-provider",
            "mock",
            "--batch",
            "--batch-scenarios",
            "static,peak-load",
            "--batch-algorithms",
            "round-robin,greedy",
            "--batch-runs",
            "7",
            "--batch-save-runs",
            "--batch-keep-adaptive",
            "--output-dir",
            "outputs/demo",
            "--log-level",
            "DEBUG",
            "--no-csv",
            "--no-plots",
        ]
    )
    assert args.config == "custom.yaml"
    assert args.algorithm == "min-load"
    assert args.scenario == "dynamic-load"
    assert args.disable_intelligence is True
    assert args.disable_llm is True
    assert args.llm_provider == "mock"
    assert args.batch is True
    assert args.batch_scenarios == "static,peak-load"
    assert args.batch_algorithms == "round-robin,greedy"
    assert args.batch_runs == 7
    assert args.batch_save_runs is True
    assert args.batch_keep_adaptive is True
    assert args.output_dir == "outputs/demo"
    assert args.log_level == "DEBUG"
    assert args.no_csv is True
    assert args.no_plots is True


def test_parse_args_ab_publication_and_repro_flags() -> None:
    """Parser should support A/B, publication, and reproducibility switches."""
    args = parse_args(
        [
            "--ab-llm",
            "--ab-intelligence",
            "--compare",
            "--compare-algorithms",
            "min-load,greedy",
            "--repro-check",
            "--repro-runs",
            "9",
            "--replay-manifest",
            "outputs/demo/run_manifest.json",
            "--replay-runs",
            "5",
            "--publication-study",
            "--carbon-study",
            "--carbon-seeds",
            "20-22",
            "--carbon-quick",
            "--chapter10",
            "--chapter10-seeds",
            "10-12",
            "--chapter10-quick",
            "--paper-bundle",
            "--paper-bundle-name",
            "ase_bundle_v1",
            "--scalability-profile",
            "--scalability-nodes",
            "12,24,48",
            "--scalability-tasks",
            "120,240",
            "--scalability-runs",
            "3",
            "--scalability-algorithms",
            "min-load,greedy",
            "--scalability-topology",
            "star",
            "--scalability-keep-adaptive",
            "--study-seeds",
            "1,2,3",
            "--study-quick",
        ]
    )
    assert args.ab_llm is True
    assert args.ab_intelligence is True
    assert args.compare is True
    assert args.compare_algorithms == "min-load,greedy"
    assert args.repro_check is True
    assert args.repro_runs == 9
    assert args.replay_manifest == "outputs/demo/run_manifest.json"
    assert args.replay_runs == 5
    assert args.publication_study is True
    assert args.carbon_study is True
    assert args.carbon_seeds == "20-22"
    assert args.carbon_quick is True
    assert args.chapter10 is True
    assert args.chapter10_seeds == "10-12"
    assert args.chapter10_quick is True
    assert args.paper_bundle is True
    assert args.paper_bundle_name == "ase_bundle_v1"
    assert args.scalability_profile is True
    assert args.scalability_nodes == "12,24,48"
    assert args.scalability_tasks == "120,240"
    assert args.scalability_runs == 3
    assert args.scalability_algorithms == "min-load,greedy"
    assert args.scalability_topology == "star"
    assert args.scalability_keep_adaptive is True
    assert args.study_seeds == "1,2,3"
    assert args.study_quick is True
