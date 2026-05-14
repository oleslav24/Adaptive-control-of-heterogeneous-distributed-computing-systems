"""Shared helpers for experiment run modes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig
from project.core.models import SystemState
from project.experiments.manifest import build_run_manifest
from project.metrics import persist_observability


def slug(value: str) -> str:
    """Normalize free-form labels into filesystem-friendly token."""
    return str(value).strip().lower().replace("_", "-").replace(" ", "-")


def with_algorithm(config: ExperimentConfig, algorithm: str) -> ExperimentConfig:
    """Return config copy with normalized scheduling algorithm."""
    optimization = replace(config.optimization, algorithm=normalize_algorithm(algorithm))
    return replace(config, optimization=optimization)


def persist_run_artifacts(
    config: ExperimentConfig,
    state: SystemState,
    mode: str = "single",
    cli_args: list[str] | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, str]:
    """Persist observability artifacts for a single run flavor."""
    output_dir = (
        Path(config.observability.output_dir)
        / config.name
        / slug(config.scenario)
        / state.selected_algorithm
    )
    run_manifest = build_run_manifest(
        config=config,
        mode=mode,
        cli_args=list(cli_args or []),
        extra=extra or {},
    )
    return persist_observability(
        state=state,
        output_dir=output_dir,
        save_csv=config.observability.save_csv,
        save_plots=config.observability.save_plots,
        save_json=config.observability.save_json,
        plot_profile=config.observability.plot_profile,
        plot_dpi=config.observability.plot_dpi,
        plot_formats=config.observability.plot_formats,
        run_manifest=run_manifest,
    )

