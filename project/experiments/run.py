"""CLI entrypoint for single, batch, A/B, and publication experiment modes."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import replace
import logging
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd

_MPL_DIR = Path(tempfile.gettempdir()) / "mplconfig-codex"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig, load_config
from project.core.models import SystemState
from project.experiments.cli import parse_args
from project.experiments.controller import Experiment
from project.experiments.dispatch import (
    MODE_FINISH_MESSAGES,
    ModeHandler,
    dispatch_mode,
    resolve_mode,
)
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.publication import StudyResult, run_publication_pipeline
from project.experiments.runner import BatchRunResult, BatchRunSpec, ExperimentRunner
from project.metrics import persist_observability, summarize_state

LOGGER = logging.getLogger(__name__)

DEFAULT_BATCH_SCENARIOS = [
    "static",
    "dynamic-load",
    "peak-load",
    "node-failures",
    "heterogeneous-tasks",
]


def main() -> None:
    """Dispatch execution into selected run mode and print summary outputs."""
    args = parse_args()
    cli_args = list(sys.argv[1:])
    config = _apply_runtime_overrides(load_config(args.config), args)
    log_path = _configure_logging(config)
    LOGGER.info("Run started: experiment=%s", config.name)
    mode = resolve_mode(args)
    dispatch_mode(
        mode=mode,
        handlers=_build_mode_handlers(),
        config=config,
        args=args,
        cli_args=cli_args,
    )
    LOGGER.info("%s. Log: %s", MODE_FINISH_MESSAGES[mode], log_path)


def _build_mode_handlers() -> dict[str, ModeHandler]:
    """Create mode-to-handler dispatch table."""
    return {
        "publication-study": _handle_publication_mode,
        "ab-llm": _handle_ab_llm_mode,
        "ab-intelligence": _handle_ab_intelligence_mode,
        "compare": _handle_compare_mode,
        "batch": _handle_batch_mode,
        "repro-check": _handle_repro_check_mode,
        "single": _handle_single_mode,
    }


def _handle_publication_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute publication-study mode."""
    seeds = _parse_study_seeds(args.study_seeds)
    result = run_publication_pipeline(
        config,
        seeds=seeds,
        quick=bool(args.study_quick),
        save_plots=not bool(args.no_plots),
        cli_args=cli_args,
    )
    _print_publication_result(config.name, seeds, result)


def _handle_ab_llm_mode(config: ExperimentConfig, _args: Namespace, cli_args: list[str]) -> None:
    """Execute A/B LLM mode."""
    _run_llm_ab(config, cli_args)


def _handle_ab_intelligence_mode(
    config: ExperimentConfig,
    _args: Namespace,
    cli_args: list[str],
) -> None:
    """Execute A/B intelligence mode."""
    _run_intelligence_ab(config, cli_args)


def _handle_compare_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute algorithm comparison mode."""
    algorithms = _parse_compare_algorithms(args.compare_algorithms)
    if not algorithms:
        algorithms = config.optimization.compare_algorithms
    _run_comparison(config, algorithms, cli_args)


def _handle_batch_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute batch matrix mode."""
    _run_batch(config, args, cli_args)


def _handle_repro_check_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute reproducibility check mode."""
    _run_repro_check(config, max(2, int(args.repro_runs)), cli_args)


def _handle_single_mode(config: ExperimentConfig, _args: Namespace, cli_args: list[str]) -> None:
    """Execute single run mode."""
    final_state = Experiment(config=config).run()
    artifacts = _persist_run_artifacts(config, final_state, mode="single", cli_args=cli_args)
    _print_single_result(config.name, final_state, artifacts)


def _run_comparison(config: ExperimentConfig, algorithms: list[str], cli_args: list[str]) -> None:
    """Run same scenario with multiple algorithms and export comparison table."""
    print(f"Experiment '{config.name}' comparison")
    print(
        "scenario | algorithm | completed | pending | deadline_violations | latency | throughput | avg_load"
    )
    print("-" * 118)

    rows: list[dict[str, object]] = []
    for algorithm in algorithms:
        scenario_config = _with_algorithm(config, algorithm)
        scenario_config = replace(
            scenario_config,
            intelligence=replace(scenario_config.intelligence, adaptive_algorithm=False),
            llm=replace(scenario_config.llm, enabled=False),
        )
        state = Experiment(config=scenario_config).run()
        rows.append(summarize_state(state))
        _persist_run_artifacts(
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
    comparison_dir = Path(config.observability.output_dir) / config.name / _slug(config.scenario)
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


def _run_intelligence_ab(config: ExperimentConfig, cli_args: list[str]) -> None:
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
    _persist_run_artifacts(
        baseline_config,
        baseline_state,
        mode="ab-intelligence",
        cli_args=cli_args,
        extra={"mode": "baseline"},
    )
    _persist_run_artifacts(
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
    ab_dir = Path(config.observability.output_dir) / config.name / _slug(config.scenario)
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


def _run_llm_ab(config: ExperimentConfig, cli_args: list[str]) -> None:
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
    _persist_run_artifacts(
        baseline_config,
        baseline_state,
        mode="ab-llm",
        cli_args=cli_args,
        extra={"mode": "baseline"},
    )
    _persist_run_artifacts(
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
    ab_dir = Path(config.observability.output_dir) / config.name / _slug(config.scenario)
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


def _run_batch(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Run scenario/algorithm matrix and print aggregated winners."""
    scenarios = _parse_batch_scenarios(args.batch_scenarios)
    algorithms = _parse_compare_algorithms(args.batch_algorithms)
    if not algorithms:
        algorithms = config.optimization.compare_algorithms

    spec = BatchRunSpec(
        scenarios=scenarios,
        algorithms=algorithms,
        repeats=max(1, int(args.batch_runs)),
        persist_individual_runs=bool(args.batch_save_runs),
        strict_algorithm_comparison=not bool(args.batch_keep_adaptive),
    )
    result = ExperimentRunner(config=config).run_batch(spec, cli_args=cli_args)
    _print_batch_result(config.name, spec, result)


def _run_repro_check(config: ExperimentConfig, runs: int, cli_args: list[str]) -> None:
    """Repeat identical run several times and verify deterministic outputs."""
    rows: list[dict[str, object]] = []
    for idx in range(runs):
        state = Experiment(config=config).run()
        rows.append({"run": idx + 1, **summarize_state(state)})

    repro_df = pd.DataFrame(rows)
    out_dir = (
        Path(config.observability.output_dir)
        / config.name
        / _slug(config.scenario)
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


def _apply_runtime_overrides(config: ExperimentConfig, args: argparse.Namespace) -> ExperimentConfig:
    """Apply CLI overrides to loaded experiment configuration."""
    if args.algorithm:
        config = _with_algorithm(config, args.algorithm)
    if args.scenario:
        config = replace(config, scenario=str(args.scenario).strip())
    if args.disable_intelligence:
        config = replace(
            config,
            intelligence=replace(config.intelligence, enabled=False, adaptive_algorithm=False),
        )
    if args.disable_llm:
        config = replace(config, llm=replace(config.llm, enabled=False))
    if args.llm_provider:
        config = replace(
            config,
            llm=replace(config.llm, provider=str(args.llm_provider).strip().lower()),
        )

    observability = config.observability
    if args.output_dir:
        observability = replace(observability, output_dir=args.output_dir)
    if args.log_level:
        observability = replace(observability, log_level=args.log_level)
    if args.no_csv:
        observability = replace(observability, save_csv=False)
    if args.no_plots:
        observability = replace(observability, save_plots=False)
    return replace(config, observability=observability)


def _persist_run_artifacts(
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
        / _slug(config.scenario)
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


def _with_algorithm(config: ExperimentConfig, algorithm: str) -> ExperimentConfig:
    """Return config copy with normalized scheduling algorithm."""
    optimization = replace(config.optimization, algorithm=normalize_algorithm(algorithm))
    return replace(config, optimization=optimization)


def _parse_compare_algorithms(raw: str | None) -> list[str]:
    """Parse comma-separated algorithm list from CLI."""
    if not raw:
        return []
    parsed: list[str] = []
    for item in raw.split(","):
        name = normalize_algorithm(item)
        if name not in parsed:
            parsed.append(name)
    return parsed


def _parse_batch_scenarios(raw: str | None) -> list[str]:
    """Parse comma-separated scenario names for batch mode."""
    if not raw:
        return list(DEFAULT_BATCH_SCENARIOS)
    parsed: list[str] = []
    for item in raw.split(","):
        name = _slug(item)
        if name and name not in parsed:
            parsed.append(name)
    return parsed or list(DEFAULT_BATCH_SCENARIOS)


def _parse_study_seeds(raw: str | None) -> list[int]:
    """Parse publication seeds from list or numeric range expression."""
    if not raw:
        return list(range(42, 72))
    text = str(raw).strip()
    if "-" in text and "," not in text:
        parts = [part.strip() for part in text.split("-", maxsplit=1)]
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start = int(parts[0])
            end = int(parts[1])
            if end < start:
                start, end = end, start
            return list(range(start, end + 1))
    seeds: list[int] = []
    for item in text.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            parsed = int(value)
        except ValueError:
            continue
        if parsed not in seeds:
            seeds.append(parsed)
    return seeds or list(range(42, 72))


def _print_single_result(name: str, final_state: SystemState, artifacts: dict[str, str]) -> None:
    """Print concise summary for one experiment run."""
    print(f"Experiment '{name}' completed.")
    print(f"Scenario: {final_state.scenario}")
    print(f"Algorithm: {final_state.selected_algorithm}")
    print(f"Intelligence enabled: {final_state.intelligence_enabled}")
    print(f"LLM enabled: {final_state.llm_enabled}")
    print(f"LLM source: {final_state.llm_source}")
    print(f"LLM confidence: {final_state.llm_confidence:.3f}")
    print(f"LLM algorithm hint: {final_state.llm_algorithm_hint}")
    print(f"LLM actions applied: {final_state.llm_actions_applied}")
    print(f"Predicted queue: {final_state.predicted_queue:.3f}")
    print(f"Predicted avg load: {final_state.predicted_avg_load:.3f}")
    print(f"Simulation time: {final_state.current_time}")
    print(f"Completed tasks: {final_state.completed_tasks}")
    print(f"Pending tasks: {final_state.pending_tasks}")
    print(f"Queue size: {final_state.queue_lengths.get('global', 0)}")
    print(f"Generated tasks: {final_state.generated_tasks}")
    print(f"Inactive nodes: {final_state.inactive_nodes}")
    print(f"Scenario events: {len(final_state.scenario_events)}")
    print(f"Deadline violations: {final_state.deadline_violations}")
    print(f"Latency (avg): {final_state.avg_latency:.3f}")
    print(f"Throughput: {final_state.throughput:.3f}")
    print(f"Load (avg): {final_state.avg_load:.3f}")
    print(f"MAS assignments: {final_state.mas_assignments}")
    print(f"MAS messages: {final_state.mas_messages}")
    print(f"State updates: {len(final_state.history)}")
    print(f"Final node loads: {final_state.node_loads}")
    for key, path in artifacts.items():
        print(f"{key}: {path}")


def _print_batch_result(name: str, spec: BatchRunSpec, result: BatchRunResult) -> None:
    """Print batch summary tables and generated artifact paths."""
    print(f"Experiment '{name}' batch run")
    print(f"Scenarios: {', '.join(spec.scenarios)}")
    print(f"Algorithms: {', '.join(spec.algorithms)}")
    print(f"Repeats per pair: {spec.repeats}")
    print(f"Strict algorithm comparison: {spec.strict_algorithm_comparison}")
    print(
        f"Total runs: {len(result.runs_df)} "
        f"({len(spec.scenarios)} scenarios x {len(spec.algorithms)} algorithms x {spec.repeats} repeats)"
    )

    if result.summary_df.empty:
        print("No batch results were produced.")
    else:
        print("Summary table (mean/std):")
        summary_columns = [
            "scenario",
            "algorithm",
            "runs",
            "avg_latency_mean",
            "avg_latency_std",
            "throughput_mean",
            "throughput_std",
            "avg_load_mean",
            "avg_load_std",
            "deadline_violations_mean",
            "pending_tasks_mean",
        ]
        available_columns = [
            col for col in summary_columns if col in result.summary_df.columns
        ]
        print(
            result.summary_df[available_columns].to_string(
                index=False,
                float_format=lambda value: f"{value:.3f}",
            )
        )

    if result.winners_df.empty:
        print("Winners table is empty.")
    else:
        print("Winners by scenario:")
        winner_columns = [
            "scenario",
            "algorithm",
            "composite_score",
            "avg_latency_mean",
            "throughput_mean",
            "pending_tasks_mean",
            "deadline_violations_mean",
        ]
        available_columns = [col for col in winner_columns if col in result.winners_df.columns]
        print(
            result.winners_df[available_columns].to_string(
                index=False,
                float_format=lambda value: f"{value:.3f}",
            )
        )

    for key, path in result.output_paths.items():
        print(f"{key}: {path}")


def _print_publication_result(name: str, seeds: list[int], result: StudyResult) -> None:
    """Print publication-study summary and hypothesis table."""
    print(f"Experiment '{name}' publication study")
    print(f"Seeds: {len(seeds)} ({min(seeds)}..{max(seeds)})")
    print(f"Output dir: {result.output_dir}")

    if result.summary.empty:
        print("No publication results were produced.")
    else:
        print("Top summary rows (sorted by avg_latency_mean):")
        top = result.summary.sort_values("avg_latency_mean").head(15)
        columns = [
            "study_id",
            "scenario",
            "method",
            "node_count",
            "task_count",
            "n_runs",
            "avg_latency_mean",
            "throughput_mean",
            "load_imbalance_mean",
            "sla_violations_mean",
        ]
        available = [col for col in columns if col in top.columns]
        print(top[available].to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    if result.hypothesis_df.empty:
        print("Hypothesis table is empty.")
    else:
        print("Hypotheses H1-H5:")
        print(
            result.hypothesis_df.to_string(
                index=False,
                float_format=lambda value: f"{value:.3f}" if isinstance(value, float) else str(value),
            )
        )

    for key, path in result.output_paths.items():
        print(f"{key}: {path}")


def _configure_logging(config: ExperimentConfig) -> Path:
    """Configure console/file logging and return log file path."""
    level_name = str(config.observability.log_level).strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    log_dir = Path(config.observability.output_dir) / config.name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "run.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    return log_path


def _slug(value: str) -> str:
    """Normalize free-form labels into filesystem-friendly token."""
    return str(value).strip().lower().replace("_", "-").replace(" ", "-")


if __name__ == "__main__":
    main()
