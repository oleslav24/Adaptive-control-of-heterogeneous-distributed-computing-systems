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
        "repro_runs": 3,
        "replay_manifest": None,
        "replay_runs": 3,
        "study_seeds": "42-71",
        "study_quick": False,
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
