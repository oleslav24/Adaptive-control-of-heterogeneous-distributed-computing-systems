"""Advanced run mode handlers: publication, A/B, batch, reproducibility."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from project.core.config import ExperimentConfig
from project.experiments.common import persist_run_artifacts, slug
from project.experiments.controller import Experiment
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.publication import StudyResult, run_publication_pipeline
from project.experiments.runner import BatchRunResult, BatchRunSpec, ExperimentRunner
from project.metrics import summarize_state


def run_publication_mode(
    config: ExperimentConfig,
    *,
    seeds: list[int],
    quick: bool,
    save_plots: bool,
    cli_args: list[str],
) -> StudyResult:
    """Run publication-study pipeline and return produced study result."""
    return run_publication_pipeline(
        config,
        seeds=seeds,
        quick=quick,
        save_plots=save_plots,
        cli_args=cli_args,
    )


def run_batch_mode(
    config: ExperimentConfig,
    *,
    spec: BatchRunSpec,
    cli_args: list[str],
) -> BatchRunResult:
    """Run scenario/algorithm matrix batch and return aggregate result."""
    return ExperimentRunner(config=config).run_batch(spec, cli_args=cli_args)


def run_intelligence_ab_mode(config: ExperimentConfig, cli_args: list[str]) -> None:
    """Run A/B experiment with intelligence layer disabled vs enabled."""
    baseline_config = replace(
        config,
        intelligence=replace(config.intelligence, enabled=False, adaptive_algorithm=False),
    )
    smart_config = replace(
        config,
        intelligence=replace(config.intelligence, enabled=True),
    )
    baseline_state = Experiment(config=baseline_config).run()
    smart_state = Experiment(config=smart_config).run()
    persist_run_artifacts(
        baseline_config,
        baseline_state,
        mode="ab-intelligence",
        cli_args=cli_args,
        extra={"mode": "baseline"},
    )
    persist_run_artifacts(
        smart_config,
        smart_state,
        mode="ab-intelligence",
        cli_args=cli_args,
        extra={"mode": "intelligent"},
    )

    print(f"Experiment '{config.name}' intelligence A/B")
    print("mode | algorithm | completed | pending | latency | throughput | avg_load")
    print("-" * 86)
    print(
        f"baseline | {baseline_state.selected_algorithm} | {baseline_state.completed_tasks} | "
        f"{baseline_state.pending_tasks} | {baseline_state.avg_latency:.3f} | "
        f"{baseline_state.throughput:.3f} | {baseline_state.avg_load:.3f}"
    )
    print(
        f"intelligent | {smart_state.selected_algorithm} | {smart_state.completed_tasks} | "
        f"{smart_state.pending_tasks} | {smart_state.avg_latency:.3f} | "
        f"{smart_state.throughput:.3f} | {smart_state.avg_load:.3f}"
    )

    improvement_latency = baseline_state.avg_latency - smart_state.avg_latency
    improvement_throughput = smart_state.throughput - baseline_state.throughput
    print(
        f"Delta: latency={improvement_latency:+.3f}, throughput={improvement_throughput:+.3f}"
    )

    rows = [
        {"mode": "baseline", **summarize_state(baseline_state)},
        {"mode": "intelligent", **summarize_state(smart_state)},
    ]
    ab_df = pd.DataFrame(rows)
    ab_dir = Path(config.observability.output_dir) / config.name / slug(config.scenario)
    ab_dir.mkdir(parents=True, exist_ok=True)
    ab_csv = ab_dir / "intelligence_ab.csv"
    ab_df.to_csv(ab_csv, index=False)
    print(f"A/B CSV: {ab_csv}")

    manifest_path = ab_dir / "intelligence_ab_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="ab-intelligence",
            cli_args=cli_args,
            extra={"rows": ab_df.to_dict(orient="records"), "ab_csv": str(ab_csv)},
        ),
    )
    print(f"A/B manifest: {manifest_path}")


def run_llm_ab_mode(config: ExperimentConfig, cli_args: list[str]) -> None:
    """Run A/B experiment with and without LLM agent influence."""
    baseline_config = replace(
        config,
        intelligence=replace(config.intelligence, adaptive_algorithm=False),
        llm=replace(config.llm, enabled=False),
    )
    llm_config = replace(
        config,
        llm=replace(config.llm, enabled=True),
    )
    baseline_state = Experiment(config=baseline_config).run()
    llm_state = Experiment(config=llm_config).run()
    persist_run_artifacts(
        baseline_config,
        baseline_state,
        mode="ab-llm",
        cli_args=cli_args,
        extra={"mode": "baseline"},
    )
    persist_run_artifacts(
        llm_config,
        llm_state,
        mode="ab-llm",
        cli_args=cli_args,
        extra={"mode": "llm"},
    )

    print(f"Experiment '{config.name}' LLM A/B")
    print(
        "mode | algorithm | llm_source | completed | pending | latency | throughput | avg_load"
    )
    print("-" * 102)
    print(
        f"baseline | {baseline_state.selected_algorithm} | {baseline_state.llm_source} | "
        f"{baseline_state.completed_tasks} | {baseline_state.pending_tasks} | "
        f"{baseline_state.avg_latency:.3f} | {baseline_state.throughput:.3f} | "
        f"{baseline_state.avg_load:.3f}"
    )
    print(
        f"llm | {llm_state.selected_algorithm} | {llm_state.llm_source} | "
        f"{llm_state.completed_tasks} | {llm_state.pending_tasks} | "
        f"{llm_state.avg_latency:.3f} | {llm_state.throughput:.3f} | "
        f"{llm_state.avg_load:.3f}"
    )

    improvement_latency = baseline_state.avg_latency - llm_state.avg_latency
    improvement_throughput = llm_state.throughput - baseline_state.throughput
    print(
        f"Delta: latency={improvement_latency:+.3f}, throughput={improvement_throughput:+.3f}"
    )

    rows = [
        {"mode": "baseline", **summarize_state(baseline_state)},
        {"mode": "llm", **summarize_state(llm_state)},
    ]
    ab_df = pd.DataFrame(rows)
    ab_dir = Path(config.observability.output_dir) / config.name / slug(config.scenario)
    ab_dir.mkdir(parents=True, exist_ok=True)
    ab_csv = ab_dir / "llm_ab.csv"
    ab_df.to_csv(ab_csv, index=False)
    print(f"LLM A/B CSV: {ab_csv}")

    manifest_path = ab_dir / "llm_ab_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="ab-llm",
            cli_args=cli_args,
            extra={"rows": ab_df.to_dict(orient="records"), "ab_csv": str(ab_csv)},
        ),
    )
    print(f"LLM A/B manifest: {manifest_path}")


def run_repro_check_mode(config: ExperimentConfig, runs: int, cli_args: list[str]) -> None:
    """Repeat identical run several times and verify deterministic outputs."""
    rows: list[dict[str, object]] = []
    for idx in range(runs):
        state = Experiment(config=config).run()
        rows.append({"run": idx + 1, **summarize_state(state)})

    repro_df = pd.DataFrame(rows)
    out_dir = (
        Path(config.observability.output_dir)
        / config.name
        / slug(config.scenario)
        / config.optimization.algorithm
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    repro_csv = out_dir / "repro_check.csv"
    repro_df.to_csv(repro_csv, index=False)

    reproducible, details = _evaluate_reproducibility(repro_df)
    print(f"Experiment '{config.name}' reproducibility check")
    print(f"Scenario: {config.scenario}")
    print(f"Algorithm: {config.optimization.algorithm}")
    print(f"Runs: {runs}")
    print(f"Reproducible: {reproducible}")
    print("Runs table:")
    print(repro_df.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print("Details:")
    for line in details:
        print(f"- {line}")
    print(f"Repro CSV: {repro_csv}")

    manifest_path = out_dir / "repro_check_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="repro-check",
            cli_args=cli_args,
            extra={
                "runs": runs,
                "reproducible": reproducible,
                "details": details,
                "repro_csv": str(repro_csv),
            },
        ),
    )
    print(f"Repro manifest: {manifest_path}")


def _evaluate_reproducibility(repro_df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Evaluate equality of key metrics across repeated runs."""
    if repro_df.empty:
        return False, ["No runs were executed."]

    strict_columns = [
        "completed_tasks",
        "pending_tasks",
        "deadline_violations",
        "generated_tasks",
        "scenario",
        "algorithm",
    ]
    float_columns = ["avg_latency", "throughput", "avg_load"]
    baseline = repro_df.iloc[0]

    details: list[str] = []
    reproducible = True
    for column in strict_columns:
        if column not in repro_df.columns:
            continue
        if not (repro_df[column] == baseline[column]).all():
            reproducible = False
            details.append(f"Mismatch in '{column}'.")

    tolerance = 1e-9
    for column in float_columns:
        if column not in repro_df.columns:
            continue
        max_diff = float((repro_df[column] - float(baseline[column])).abs().max())
        if max_diff > tolerance:
            reproducible = False
            details.append(f"Mismatch in '{column}' (max diff {max_diff:.12f}).")

    if reproducible:
        details.append("All tracked metrics are identical across repeated runs.")
    return reproducible, details

