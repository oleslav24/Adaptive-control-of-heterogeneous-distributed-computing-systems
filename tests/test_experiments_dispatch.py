"""Unit tests for experiments run mode dispatch helpers."""

from __future__ import annotations

from argparse import Namespace

import pytest

from project.core.config import ExperimentConfig, load_config
from project.experiments.dispatch import dispatch_mode, resolve_mode


def _minimal_args(**overrides: object) -> Namespace:
    """Create parsed-args like namespace for mode resolution tests."""
    defaults = {
        "publication_study": False,
        "ab_llm": False,
        "ab_intelligence": False,
        "compare": False,
        "batch": False,
        "repro_check": False,
        "replay_manifest": None,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def test_resolve_mode_uses_expected_priority_order() -> None:
    """Mode resolution should follow explicit priority from most specific to fallback."""
    assert resolve_mode(_minimal_args(publication_study=True, batch=True)) == "publication-study"
    assert (
        resolve_mode(_minimal_args(replay_manifest="outputs/demo/run_manifest.json", compare=True))
        == "replay-manifest"
    )
    assert resolve_mode(_minimal_args(ab_llm=True, compare=True)) == "ab-llm"
    assert resolve_mode(_minimal_args(ab_intelligence=True, compare=True)) == "ab-intelligence"
    assert resolve_mode(_minimal_args(compare=True, batch=True)) == "compare"
    assert resolve_mode(_minimal_args(batch=True, repro_check=True)) == "batch"
    assert resolve_mode(_minimal_args(repro_check=True)) == "repro-check"
    assert resolve_mode(_minimal_args()) == "single"


def test_dispatch_mode_calls_matching_handler() -> None:
    """Dispatcher should execute only handler for requested mode."""
    calls: list[str] = []

    def _handler(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
        _ = (config, args, cli_args)
        calls.append("single")

    config = load_config("config.yaml")
    args = _minimal_args()
    dispatch_mode(
        mode="single",
        handlers={"single": _handler},
        config=config,
        args=args,
        cli_args=["--unit-test"],
    )
    assert calls == ["single"]


def test_dispatch_mode_raises_on_unknown_mode() -> None:
    """Dispatcher should fail fast for unsupported mode keys."""
    with pytest.raises(ValueError, match="Unsupported mode: unknown"):
        dispatch_mode(
            mode="unknown",
            handlers={},
            config=load_config("config.yaml"),
            args=_minimal_args(),
            cli_args=[],
        )
