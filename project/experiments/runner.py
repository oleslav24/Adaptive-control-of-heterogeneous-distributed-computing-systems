"""Batch experiment orchestration and ranking utilities."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig
from project.experiments.controller import Experiment
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest
from project.metrics import (
    persist_batch_observability,
    persist_observability,
    summarize_state,
)


@dataclass(slots=True)
class BatchRunSpec:
    """Input specification for scenario/algorithm batch matrix."""

    scenarios: list[str]
    algorithms: list[str]
    repeats: int = 1
    persist_individual_runs: bool = False
    strict_algorithm_comparison: bool = True


@dataclass(slots=True)
class BatchRunResult:
    """Tabular outputs and artifact paths produced by batch execution."""

    runs_df: pd.DataFrame
    summary_df: pd.DataFrame
    ranking_df: pd.DataFrame
    winners_df: pd.DataFrame
    output_paths: dict[str, str]


class ExperimentRunner:
    """Execute batch experiment matrix and persist aggregated artifacts."""

    def __init__(self, config: ExperimentConfig) -> None:
        """Store base config used to derive each run configuration."""
        self.config = config

    def run_batch(
        self,
        spec: BatchRunSpec,
        cli_args: list[str] | None = None,
    ) -> BatchRunResult:
        """Run all scenario/algorithm/repeat combinations and aggregate results."""
        repeats = max(1, int(spec.repeats))
        rows: list[dict[str, object]] = []
        cli_args = list(cli_args or [])

        scenarios = [_normalize_scenario_name(name) for name in spec.scenarios]
        algorithms = [normalize_algorithm(name) for name in spec.algorithms]

        for scenario in scenarios:
            for repeat_idx in range(repeats):
                run_seed = int(self.config.simulation.seed + repeat_idx)
                for algorithm in algorithms:
                    run_config = replace(
                        self.config,
                        scenario=scenario,
                        simulation=replace(self.config.simulation, seed=run_seed),
                        optimization=replace(self.config.optimization, algorithm=algorithm),
                    )
                    if spec.strict_algorithm_comparison:
                        run_config = replace(
                            run_config,
                            intelligence=replace(
                                run_config.intelligence,
                                enabled=False,
                                adaptive_algorithm=False,
                            ),
                            llm=replace(run_config.llm, enabled=False),
                        )

                    state = Experiment(config=run_config).run()
                    run_manifest = build_run_manifest(
                        config=run_config,
                        mode="batch-run",
                        cli_args=cli_args,
                        extra={
                            "repeat": repeat_idx + 1,
                            "seed": run_seed,
                            "configured_scenario": scenario,
                            "configured_algorithm": algorithm,
                        },
                    )
                    if spec.persist_individual_runs:
                        self._persist_single_run(
                            config=run_config,
                            state=state,
                            repeat_idx=repeat_idx,
                            run_manifest=run_manifest,
                        )

                    row = {
                        "repeat": repeat_idx + 1,
                        "seed": run_seed,
                        "configured_scenario": scenario,
                        "configured_algorithm": algorithm,
                        **summarize_state(state),
                    }
                    rows.append(row)

        runs_df = pd.DataFrame(rows)
        summary_df = _build_batch_summary(runs_df)
        ranking_df = _build_batch_ranking(summary_df)
        winners_df = (
            ranking_df.groupby("scenario", as_index=False).first()
            if not ranking_df.empty
            else pd.DataFrame()
        )
        batch_manifest = build_run_manifest(
            config=self.config,
            mode="batch",
            cli_args=cli_args,
            extra={
                "repeats": repeats,
                "scenarios": scenarios,
                "algorithms": algorithms,
                "strict_algorithm_comparison": spec.strict_algorithm_comparison,
                "persist_individual_runs": spec.persist_individual_runs,
                "total_runs": len(runs_df),
            },
        )

        output_paths = self._persist_batch_tables(
            runs_df=runs_df,
            summary_df=summary_df,
            ranking_df=ranking_df,
            winners_df=winners_df,
            batch_manifest=batch_manifest,
        )
        return BatchRunResult(
            runs_df=runs_df,
            summary_df=summary_df,
            ranking_df=ranking_df,
            winners_df=winners_df,
            output_paths=output_paths,
        )

    def _persist_single_run(
        self,
        config: ExperimentConfig,
        state,
        repeat_idx: int,
        run_manifest: dict[str, Any] | None = None,
    ) -> None:
        """Persist artifacts for one batch run when detailed saving is enabled."""
        output_dir = (
            Path(config.observability.output_dir)
            / config.name
            / "batch-runs"
            / _normalize_scenario_name(config.scenario)
            / f"repeat-{repeat_idx + 1:02d}"
            / config.optimization.algorithm
        )
        persist_observability(
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

    def _persist_batch_tables(
        self,
        runs_df: pd.DataFrame,
        summary_df: pd.DataFrame,
        ranking_df: pd.DataFrame,
        winners_df: pd.DataFrame,
        batch_manifest: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Persist aggregated batch tables/plots and return artifact map."""
        out_dir = Path(self.config.observability.output_dir) / self.config.name / "batch"
        artifact_paths = persist_batch_observability(
            runs_df=runs_df,
            summary_df=summary_df,
            ranking_df=ranking_df,
            winners_df=winners_df,
            output_dir=out_dir,
            save_csv=self.config.observability.save_csv,
            save_plots=self.config.observability.save_plots,
            save_json=self.config.observability.save_json,
            plot_profile=self.config.observability.plot_profile,
            plot_dpi=self.config.observability.plot_dpi,
            plot_formats=self.config.observability.plot_formats,
            batch_manifest=batch_manifest,
        )
        if artifact_paths:
            integrity_path = write_artifact_integrity_file(
                out_dir / "artifact_integrity.json",
                artifact_paths,
            )
            artifact_paths["artifact_integrity_json"] = integrity_path
        return artifact_paths


def _build_batch_summary(runs_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-run metrics into mean/std summary by scenario and algorithm."""
    if runs_df.empty:
        return pd.DataFrame()

    metric_columns = [
        "completed_tasks",
        "pending_tasks",
        "deadline_violations",
        "avg_latency",
        "throughput",
        "avg_load",
        "energy_consumed_mwh",
        "co2_total_lb",
        "co2e_total_lb",
        "co2_per_completed_task_lb",
        "co2e_per_completed_task_lb",
        "generated_tasks",
        "mas_messages",
        "mas_assignments",
    ]
    agg = runs_df.groupby(["scenario", "algorithm"], as_index=False)[metric_columns].agg(
        ["mean", "std"]
    )
    agg.columns = [
        f"{col}_{stat}" if stat else col
        for col, stat in agg.columns.to_flat_index()
    ]
    agg = agg.rename(
        columns={
            "scenario_": "scenario",
            "algorithm_": "algorithm",
        }
    )
    counts = (
        runs_df.groupby(["scenario", "algorithm"], as_index=False)
        .size()
        .rename(columns={"size": "runs"})
    )
    agg = agg.merge(counts, on=["scenario", "algorithm"], how="left")
    std_columns = [col for col in agg.columns if col.endswith("_std")]
    if std_columns:
        agg[std_columns] = agg[std_columns].fillna(0.0)
    return agg.sort_values(["scenario", "avg_latency_mean", "throughput_mean"], ascending=[True, True, False]).reset_index(
        drop=True
    )


def _build_batch_ranking(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Rank algorithms per scenario using a composite score."""
    if summary_df.empty:
        return pd.DataFrame()

    ranking = summary_df.copy()
    ranking["rank_latency"] = ranking.groupby("scenario")["avg_latency_mean"].rank(
        method="min", ascending=True
    )
    ranking["rank_throughput"] = ranking.groupby("scenario")["throughput_mean"].rank(
        method="min", ascending=False
    )
    ranking["rank_pending"] = ranking.groupby("scenario")["pending_tasks_mean"].rank(
        method="min", ascending=True
    )
    ranking["rank_deadline"] = ranking.groupby("scenario")[
        "deadline_violations_mean"
    ].rank(method="min", ascending=True)
    ranking["composite_score"] = (
        ranking["rank_latency"]
        + ranking["rank_throughput"]
        + ranking["rank_pending"]
        + ranking["rank_deadline"]
    )
    ranking = ranking.sort_values(
        ["scenario", "composite_score", "avg_latency_mean", "throughput_mean"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)
    return ranking


def _normalize_scenario_name(name: str) -> str:
    """Normalize scenario labels for consistent indexing."""
    return str(name).strip().lower().replace("_", "-").replace(" ", "-")
