"""Integration-style tests for run.py mode handlers wiring."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass

from project.core.config import ExperimentConfig, load_config
from project.experiments import run


def _args(**overrides: object) -> Namespace:
    """Create args namespace compatible with run handlers."""
    values: dict[str, object] = {
        "compare_algorithms": None,
        "batch_scenarios": None,
        "batch_algorithms": None,
        "batch_runs": 3,
        "batch_save_runs": False,
        "batch_keep_adaptive": False,
        "scalability_nodes": "10,50,100,500",
        "scalability_tasks": "100,500,1000,5000",
        "scalability_runs": 1,
        "scalability_algorithms": None,
        "scalability_topology": "ring",
        "scalability_keep_adaptive": False,
        "repro_runs": 3,
        "replay_manifest": None,
        "replay_runs": 3,
        "study_seeds": "42-71",
        "study_quick": False,
        "carbon_seeds": None,
        "carbon_quick": False,
        "chapter10_seeds": None,
        "chapter10_quick": False,
        "paper_bundle_name": "paper_bundle",
        "no_plots": False,
    }
    values.update(overrides)
    return Namespace(**values)


def _config() -> ExperimentConfig:
    """Load shared config for handler invocation tests."""
    return load_config("config.yaml")


def test_handle_publication_mode_calls_publication_runner(monkeypatch) -> None:
    """Publication handler should delegate to publication mode module."""
    calls: dict[str, object] = {}
    result_marker = object()

    def _fake_run_publication_mode(
        config: ExperimentConfig,
        *,
        seeds: list[int],
        quick: bool,
        save_plots: bool,
        cli_args: list[str],
    ):
        calls["config_name"] = config.name
        calls["seeds"] = list(seeds)
        calls["quick"] = quick
        calls["save_plots"] = save_plots
        calls["cli_args"] = list(cli_args)
        return result_marker

    def _fake_print(name: str, seeds: list[int], result: object) -> None:
        calls["print_name"] = name
        calls["print_seeds"] = list(seeds)
        calls["print_result"] = result

    monkeypatch.setattr(run, "run_publication_mode", _fake_run_publication_mode)
    monkeypatch.setattr(run, "_print_publication_result", _fake_print)

    run._handle_publication_mode(
        _config(),
        _args(study_seeds="10-12", study_quick=True, no_plots=True),
        ["--publication-study"],
    )
    assert calls["seeds"] == [10, 11, 12]
    assert calls["quick"] is True
    assert calls["save_plots"] is False
    assert calls["print_result"] is result_marker


def test_handle_carbon_study_mode_calls_publication_runner_with_filter(monkeypatch) -> None:
    """Carbon-study handler should call publication runner with dedicated mode/filter."""
    calls: dict[str, object] = {}
    result_marker = object()

    def _fake_run_publication_mode(
        config: ExperimentConfig,
        *,
        seeds: list[int],
        quick: bool,
        save_plots: bool,
        cli_args: list[str],
        mode: str,
        output_dir_name: str,
        include_study_ids: list[str] | None,
    ):
        calls["config_name"] = config.name
        calls["seeds"] = list(seeds)
        calls["quick"] = quick
        calls["save_plots"] = save_plots
        calls["cli_args"] = list(cli_args)
        calls["mode"] = mode
        calls["output_dir_name"] = output_dir_name
        calls["include_study_ids"] = list(include_study_ids or [])
        return result_marker

    def _fake_print(name: str, seeds: list[int], result: object) -> None:
        calls["print_name"] = name
        calls["print_seeds"] = list(seeds)
        calls["print_result"] = result

    monkeypatch.setattr(run, "run_publication_mode", _fake_run_publication_mode)
    monkeypatch.setattr(run, "_print_carbon_study_result", _fake_print)

    run._handle_carbon_study_mode(
        _config(),
        _args(carbon_seeds="21-23", carbon_quick=True, no_plots=True),
        ["--carbon-study"],
    )
    assert calls["seeds"] == [21, 22, 23]
    assert calls["quick"] is True
    assert calls["save_plots"] is False
    assert calls["mode"] == "carbon-study"
    assert calls["output_dir_name"] == "carbon-study"
    assert calls["include_study_ids"] == ["E6_carbon_vs_performance"]
    assert calls["print_result"] is result_marker


def test_handle_ab_modes_delegate_to_advanced_handlers(monkeypatch) -> None:
    """AB handlers should route to dedicated advanced mode functions."""
    calls: list[str] = []

    monkeypatch.setattr(run, "run_llm_ab_mode", lambda *_args, **_kwargs: calls.append("llm"))
    monkeypatch.setattr(
        run,
        "run_intelligence_ab_mode",
        lambda *_args, **_kwargs: calls.append("intelligence"),
    )

    run._handle_ab_llm_mode(_config(), _args(), ["--ab-llm"])
    run._handle_ab_intelligence_mode(_config(), _args(), ["--ab-intelligence"])
    assert calls == ["llm", "intelligence"]


def test_handle_compare_mode_parses_and_routes_algorithms(monkeypatch) -> None:
    """Compare handler should normalize list and pass to comparison mode."""
    calls: dict[str, object] = {}

    def _fake_run(config: ExperimentConfig, algorithms: list[str], cli_args: list[str]) -> None:
        calls["config_name"] = config.name
        calls["algorithms"] = list(algorithms)
        calls["cli_args"] = list(cli_args)

    monkeypatch.setattr(run, "run_comparison_mode", _fake_run)
    run._handle_compare_mode(
        _config(),
        _args(compare_algorithms="round-robin,min-load,round-robin"),
        ["--compare"],
    )
    assert calls["algorithms"] == ["round-robin", "min-load"]


def test_handle_batch_mode_builds_spec_and_prints(monkeypatch) -> None:
    """Batch handler should build BatchRunSpec and call printer with result."""
    calls: dict[str, object] = {}

    @dataclass
    class _Result:
        marker: str = "ok"

    def _fake_run_batch_mode(config: ExperimentConfig, *, spec, cli_args: list[str]):
        calls["config_name"] = config.name
        calls["spec"] = spec
        calls["cli_args"] = list(cli_args)
        return _Result()

    def _fake_print(name: str, spec, result) -> None:
        calls["print_name"] = name
        calls["print_spec"] = spec
        calls["print_result"] = result

    monkeypatch.setattr(run, "run_batch_mode", _fake_run_batch_mode)
    monkeypatch.setattr(run, "_print_batch_result", _fake_print)

    run._handle_batch_mode(
        _config(),
        _args(
            batch_scenarios="static,dynamic-load",
            batch_algorithms="round-robin,greedy",
            batch_runs=5,
            batch_save_runs=True,
            batch_keep_adaptive=True,
        ),
        ["--batch"],
    )
    spec = calls["spec"]
    assert spec.scenarios == ["static", "dynamic-load"]
    assert spec.algorithms == ["round-robin", "greedy"]
    assert spec.repeats == 5
    assert spec.persist_individual_runs is True
    assert spec.strict_algorithm_comparison is False
    assert getattr(calls["print_result"], "marker") == "ok"


def test_handle_scalability_profile_mode_builds_spec_and_prints(monkeypatch) -> None:
    """Scalability handler should normalize sweep parameters and print outputs."""
    calls: dict[str, object] = {}

    @dataclass
    class _Result:
        marker: str = "ok"

    def _fake_run_scalability_sweep(*, config: ExperimentConfig, spec, cli_args: list[str]):
        calls["config_name"] = config.name
        calls["spec"] = spec
        calls["cli_args"] = list(cli_args)
        return _Result()

    def _fake_print(name: str, spec, result) -> None:
        calls["print_name"] = name
        calls["print_spec"] = spec
        calls["print_result"] = result

    monkeypatch.setattr(run, "run_scalability_sweep", _fake_run_scalability_sweep)
    monkeypatch.setattr(run, "_print_scalability_result", _fake_print)

    run._handle_scalability_profile_mode(
        _config(),
        _args(
            scalability_nodes="12,24,24",
            scalability_tasks="120,240",
            scalability_runs=3,
            scalability_algorithms="round-robin,greedy",
            scalability_topology="star",
            scalability_keep_adaptive=True,
        ),
        ["--scalability-profile"],
    )
    spec = calls["spec"]
    assert spec.node_counts == [12, 24]
    assert spec.task_counts == [120, 240]
    assert spec.algorithms == ["round-robin", "greedy"]
    assert spec.repeats == 3
    assert spec.topology == "star"
    assert spec.scenario == "peak-load"
    assert spec.strict_algorithm_comparison is False
    assert getattr(calls["print_result"], "marker") == "ok"


def test_handle_repro_mode_uses_minimum_two_runs(monkeypatch) -> None:
    """Repro handler should clamp runs to at least 2 before delegation."""
    calls: dict[str, object] = {}

    def _fake_run_repro(config: ExperimentConfig, runs: int, cli_args: list[str]) -> None:
        calls["config_name"] = config.name
        calls["runs"] = runs
        calls["cli_args"] = list(cli_args)

    monkeypatch.setattr(run, "run_repro_check_mode", _fake_run_repro)
    run._handle_repro_check_mode(_config(), _args(repro_runs=1), ["--repro-check"])
    assert calls["runs"] == 2


def test_handle_replay_mode_uses_minimum_two_runs(monkeypatch) -> None:
    """Replay handler should clamp runs and pass source manifest path."""
    calls: dict[str, object] = {}

    def _fake_run_replay_manifest_mode(*, manifest_path: str, runs: int, cli_args: list[str]) -> None:
        calls["manifest_path"] = manifest_path
        calls["runs"] = runs
        calls["cli_args"] = list(cli_args)

    monkeypatch.setattr(run, "run_replay_manifest_mode", _fake_run_replay_manifest_mode)
    run._handle_replay_manifest_mode(
        _config(),
        _args(replay_manifest="outputs/demo/run_manifest.json", replay_runs=1),
        ["--replay-manifest", "outputs/demo/run_manifest.json"],
    )
    assert calls["manifest_path"] == "outputs/demo/run_manifest.json"
    assert calls["runs"] == 2


def test_handle_single_mode_routes_result_to_printer(monkeypatch) -> None:
    """Single handler should call single-mode runner and printer with outputs."""
    calls: dict[str, object] = {}
    fake_state = object()
    fake_artifacts = {"summary_json": "path/to/summary.json"}

    def _fake_run_single_mode(config: ExperimentConfig, cli_args: list[str]):
        calls["config_name"] = config.name
        calls["cli_args"] = list(cli_args)
        return fake_state, fake_artifacts

    def _fake_print(name: str, state: object, artifacts: dict[str, str]) -> None:
        calls["print_name"] = name
        calls["print_state"] = state
        calls["print_artifacts"] = dict(artifacts)

    monkeypatch.setattr(run, "run_single_mode", _fake_run_single_mode)
    monkeypatch.setattr(run, "_print_single_result", _fake_print)

    run._handle_single_mode(_config(), _args(), ["--config", "config.yaml"])
    assert calls["print_state"] is fake_state
    assert calls["print_artifacts"] == fake_artifacts


def test_handle_paper_bundle_mode_routes_result_to_printer(monkeypatch) -> None:
    """Paper-bundle handler should delegate orchestration and print outputs."""
    calls: dict[str, object] = {}
    result_marker = object()

    def _fake_run_paper_bundle(
        config: ExperimentConfig,
        *,
        seeds: list[int] | None,
        quick: bool | None,
        save_plots: bool,
        bundle_name: str,
        strict: bool,
        cli_args: list[str],
    ):
        calls["config_name"] = config.name
        calls["seeds"] = seeds
        calls["quick"] = quick
        calls["save_plots"] = save_plots
        calls["bundle_name"] = bundle_name
        calls["strict"] = strict
        calls["cli_args"] = list(cli_args)
        return result_marker

    def _fake_print(name: str, result: object) -> None:
        calls["print_name"] = name
        calls["print_result"] = result

    monkeypatch.setattr(run, "run_paper_bundle", _fake_run_paper_bundle)
    monkeypatch.setattr(run, "_print_paper_bundle_result", _fake_print)

    run._handle_paper_bundle_mode(
        _config(),
        _args(
            chapter10_seeds="42,43",
            chapter10_quick=True,
            no_plots=True,
            paper_bundle_name="ase_bundle_v2",
        ),
        ["--paper-bundle"],
    )

    assert calls["seeds"] == [42, 43]
    assert calls["quick"] is True
    assert calls["save_plots"] is False
    assert calls["bundle_name"] == "ase_bundle_v2"
    assert calls["strict"] is True
    assert calls["print_result"] is result_marker
