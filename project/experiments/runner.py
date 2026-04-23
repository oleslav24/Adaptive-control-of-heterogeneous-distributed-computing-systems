from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig
from project.experiments.controller import Experiment
from project.metrics import persist_observability, summarize_state


@dataclass(slots=True)
class BatchRunSpec:
    scenarios: list[str]
    algorithms: list[str]
    repeats: int = 1
    persist_individual_runs: bool = False
    strict_algorithm_comparison: bool = True


@dataclass(slots=True)
class BatchRunResult:
    runs_df: pd.DataFrame
    summary_df: pd.DataFrame
    ranking_df: pd.DataFrame
    winners_df: pd.DataFrame
    output_paths: dict[str, str]


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def run_batch(self, spec: BatchRunSpec) -> BatchRunResult:
        repeats = max(1, int(spec.repeats))
        rows: list[dict[str, object]] = []

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
                    if spec.persist_individual_runs:
                        self._persist_single_run(run_config, state, repeat_idx)

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

        output_paths = self._persist_batch_tables(
            runs_df=runs_df,
            summary_df=summary_df,
            ranking_df=ranking_df,
            winners_df=winners_df,
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
    ) -> None:
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
        )

    def _persist_batch_tables(
        self,
        runs_df: pd.DataFrame,
        summary_df: pd.DataFrame,
        ranking_df: pd.DataFrame,
        winners_df: pd.DataFrame,
    ) -> dict[str, str]:
        out_dir = Path(self.config.observability.output_dir) / self.config.name / "batch"
        out_dir.mkdir(parents=True, exist_ok=True)

        paths = {
            "runs_csv": str(out_dir / "batch_runs.csv"),
            "summary_csv": str(out_dir / "batch_summary.csv"),
            "ranking_csv": str(out_dir / "batch_ranking.csv"),
            "winners_csv": str(out_dir / "batch_winners.csv"),
        }
        runs_df.to_csv(paths["runs_csv"], index=False)
        summary_df.to_csv(paths["summary_csv"], index=False)
        ranking_df.to_csv(paths["ranking_csv"], index=False)
        winners_df.to_csv(paths["winners_csv"], index=False)
        return paths


def _build_batch_summary(runs_df: pd.DataFrame) -> pd.DataFrame:
    if runs_df.empty:
        return pd.DataFrame()

    metric_columns = [
        "completed_tasks",
        "pending_tasks",
        "deadline_violations",
        "avg_latency",
        "throughput",
        "avg_load",
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
    return str(name).strip().lower().replace("_", "-").replace(" ", "-")
