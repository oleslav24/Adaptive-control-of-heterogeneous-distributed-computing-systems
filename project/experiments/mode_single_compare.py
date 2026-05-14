"""Single-run and comparison mode handlers for experiment CLI."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from project.core.config import ExperimentConfig
from project.core.models import SystemState
from project.experiments.common import persist_run_artifacts, slug, with_algorithm
from project.experiments.controller import Experiment
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest, write_manifest
from project.metrics import summarize_state


def run_single_mode(config: ExperimentConfig, cli_args: list[str]) -> tuple[SystemState, dict[str, str]]:
    """Run single experiment and persist observability artifacts."""
    final_state = Experiment(config=config).run()
    artifacts = persist_run_artifacts(config, final_state, mode="single", cli_args=cli_args)
    return final_state, artifacts


def run_comparison_mode(
    config: ExperimentConfig,
    algorithms: list[str],
    cli_args: list[str],
) -> None:
    """Run same scenario with multiple algorithms and export comparison table."""
    print(f"Experiment '{config.name}' comparison")
    print(
        "scenario | algorithm | completed | pending | deadline_violations | latency | throughput | avg_load"
    )
    print("-" * 118)

    rows: list[dict[str, object]] = []
    for algorithm in algorithms:
        scenario_config = with_algorithm(config, algorithm)
        scenario_config = replace(
            scenario_config,
            intelligence=replace(scenario_config.intelligence, adaptive_algorithm=False),
            llm=replace(scenario_config.llm, enabled=False),
        )
        state = Experiment(config=scenario_config).run()
        rows.append(summarize_state(state))
        persist_run_artifacts(
            scenario_config,
            state,
            mode="comparison",
            cli_args=cli_args,
            extra={"comparison_algorithm": algorithm},
        )
        print(
            f"{state.scenario} | {state.selected_algorithm} | {state.completed_tasks} | {state.pending_tasks} | "
            f"{state.deadline_violations} | {state.avg_latency:.3f} | "
            f"{state.throughput:.3f} | {state.avg_load:.3f}"
        )

    comparison_df = pd.DataFrame(rows)
    comparison_dir = Path(config.observability.output_dir) / config.name / slug(config.scenario)
    comparison_dir.mkdir(parents=True, exist_ok=True)
    comparison_csv = comparison_dir / "comparison.csv"
    comparison_df.to_csv(comparison_csv, index=False)
    print(f"Comparison CSV: {comparison_csv}")

    manifest_path = comparison_dir / "comparison_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="comparison",
            cli_args=cli_args,
            extra={
                "algorithms": algorithms,
                "rows": comparison_df.to_dict(orient="records"),
                "comparison_csv": str(comparison_csv),
            },
        ),
    )
    print(f"Comparison manifest: {manifest_path}")
    integrity_path = write_artifact_integrity_file(
        comparison_dir / "comparison_artifact_integrity.json",
        {
            "comparison_csv": str(comparison_csv),
            "comparison_manifest_json": str(manifest_path),
        },
    )
    print(f"Comparison artifact integrity: {integrity_path}")
