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
from project.experiments.chapter10 import Chapter10Result, run_chapter10_experiment
from project.experiments.paper_bundle import PaperBundleResult, run_paper_bundle
from project.experiments.common import slug, with_algorithm
from project.experiments.dispatch import (
    MODE_FINISH_MESSAGES,
    ModeHandler,
    dispatch_mode,
    resolve_mode,
)
from project.experiments.mode_advanced import (
    run_batch_mode,
    run_intelligence_ab_mode,
    run_llm_ab_mode,
    run_publication_mode,
    run_replay_manifest_mode,
    run_repro_check_mode,
)
from project.experiments.mode_single_compare import run_comparison_mode, run_single_mode
from project.experiments.publication import StudyResult
from project.experiments.runner import BatchRunResult, BatchRunSpec
from project.experiments.scalability import (
    ScalabilitySweepResult,
    ScalabilitySweepSpec,
    run_scalability_sweep,
)

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
        "paper-bundle": _handle_paper_bundle_mode,
        "chapter10-study": _handle_chapter10_mode,
        "carbon-study": _handle_carbon_study_mode,
        "publication-study": _handle_publication_mode,
        "scalability-profile": _handle_scalability_profile_mode,
        "replay-manifest": _handle_replay_manifest_mode,
        "ab-llm": _handle_ab_llm_mode,
        "ab-intelligence": _handle_ab_intelligence_mode,
        "compare": _handle_compare_mode,
        "batch": _handle_batch_mode,
        "repro-check": _handle_repro_check_mode,
        "single": _handle_single_mode,
    }


def _handle_paper_bundle_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute paper-bundle mode."""
    chapter10_seeds = _parse_study_seeds(args.chapter10_seeds) if args.chapter10_seeds else None
    chapter10_quick: bool | None = True if bool(args.chapter10_quick) else None
    result = run_paper_bundle(
        config,
        seeds=chapter10_seeds,
        quick=chapter10_quick,
        save_plots=not bool(args.no_plots),
        bundle_name=str(args.paper_bundle_name or "paper_bundle"),
        strict=True,
        cli_args=cli_args,
    )
    _print_paper_bundle_result(config.name, result)


def _handle_chapter10_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute chapter10-study mode."""
    chapter10_seeds = _parse_study_seeds(args.chapter10_seeds) if args.chapter10_seeds else None
    chapter10_quick: bool | None = True if bool(args.chapter10_quick) else None
    result = run_chapter10_experiment(
        config,
        seeds=chapter10_seeds,
        quick=chapter10_quick,
        save_plots=not bool(args.no_plots),
        cli_args=cli_args,
    )
    _print_chapter10_result(config.name, result)


def _handle_publication_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute publication-study mode."""
    seeds = _parse_study_seeds(args.study_seeds)
    result = run_publication_mode(
        config,
        seeds=seeds,
        quick=bool(args.study_quick),
        save_plots=not bool(args.no_plots),
        cli_args=cli_args,
    )
    _print_publication_result(config.name, seeds, result)


def _handle_carbon_study_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute dedicated carbon-study mode over selected publication studies."""
    seeds = (
        _parse_study_seeds(args.carbon_seeds)
        if args.carbon_seeds
        else list(config.carbon_study.seeds)
    )
    quick = bool(args.carbon_quick) or bool(config.carbon_study.quick)
    save_plots = bool((not bool(args.no_plots)) and config.carbon_study.save_plots)
    result = run_publication_mode(
        config,
        seeds=seeds,
        quick=quick,
        save_plots=save_plots,
        cli_args=cli_args,
        mode="carbon-study",
        output_dir_name="carbon-study",
        include_study_ids=list(config.carbon_study.study_ids),
    )
    _print_carbon_study_result(config.name, seeds, result)


def _handle_scalability_profile_mode(
    config: ExperimentConfig, args: Namespace, cli_args: list[str]
) -> None:
    """Execute scalability profiling sweep mode."""
    node_counts = _parse_positive_int_csv(
        raw=args.scalability_nodes,
        fallback=[10, 50, 100, 500],
    )
    task_counts = _parse_positive_int_csv(
        raw=args.scalability_tasks,
        fallback=[100, 500, 1000, 5000],
    )
    algorithms = _parse_compare_algorithms(args.scalability_algorithms)
    if not algorithms:
        algorithms = list(config.optimization.compare_algorithms)
    spec = ScalabilitySweepSpec(
        node_counts=node_counts,
        task_counts=task_counts,
        algorithms=algorithms,
        repeats=max(1, int(args.scalability_runs)),
        topology=str(args.scalability_topology).strip().lower(),
        scenario=slug(config.scenario),
        strict_algorithm_comparison=not bool(args.scalability_keep_adaptive),
    )
    result = run_scalability_sweep(config=config, spec=spec, cli_args=cli_args)
    _print_scalability_result(config.name, spec, result)


def _handle_replay_manifest_mode(_config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute deterministic replay mode using source run manifest."""
    run_replay_manifest_mode(
        manifest_path=str(args.replay_manifest),
        runs=max(2, int(args.replay_runs)),
        cli_args=cli_args,
    )


def _handle_ab_llm_mode(config: ExperimentConfig, _args: Namespace, cli_args: list[str]) -> None:
    """Execute A/B LLM mode."""
    run_llm_ab_mode(config, cli_args)


def _handle_ab_intelligence_mode(
    config: ExperimentConfig,
    _args: Namespace,
    cli_args: list[str],
) -> None:
    """Execute A/B intelligence mode."""
    run_intelligence_ab_mode(config, cli_args)


def _handle_compare_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute algorithm comparison mode."""
    algorithms = _parse_compare_algorithms(args.compare_algorithms)
    if not algorithms:
        algorithms = config.optimization.compare_algorithms
    run_comparison_mode(config, algorithms, cli_args)


def _handle_batch_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute batch matrix mode."""
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
    result = run_batch_mode(config, spec=spec, cli_args=cli_args)
    _print_batch_result(config.name, spec, result)


def _handle_repro_check_mode(config: ExperimentConfig, args: Namespace, cli_args: list[str]) -> None:
    """Execute reproducibility check mode."""
    run_repro_check_mode(config, max(2, int(args.repro_runs)), cli_args)


def _handle_single_mode(config: ExperimentConfig, _args: Namespace, cli_args: list[str]) -> None:
    """Execute single run mode."""
    final_state, artifacts = run_single_mode(config, cli_args)
    _print_single_result(config.name, final_state, artifacts)


def _apply_runtime_overrides(config: ExperimentConfig, args: Namespace) -> ExperimentConfig:
    """Apply CLI overrides to loaded experiment configuration."""
    if args.algorithm:
        config = with_algorithm(config, args.algorithm)
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
        name = slug(item)
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


def _parse_positive_int_csv(raw: str | None, fallback: list[int]) -> list[int]:
    """Parse comma-separated positive integers preserving order/uniqueness."""
    if not raw:
        return list(fallback)
    parsed: list[int] = []
    for item in str(raw).split(","):
        token = item.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError:
            continue
        if value < 1:
            continue
        if value not in parsed:
            parsed.append(value)
    return parsed or list(fallback)


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
    print(f"Energy (MWh): {final_state.energy_consumed_mwh:.6f}")
    print(f"CO2 total (lb): {final_state.co2_total_lb:.3f}")
    print(f"CO2e total (lb): {final_state.co2e_total_lb:.3f}")
    print(f"CO2 per completed task (lb): {final_state.co2_per_completed_task_lb:.6f}")
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
            "co2_total_lb_mean",
            "co2_total_lb_std",
            "energy_consumed_mwh_mean",
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


def _print_carbon_study_result(name: str, seeds: list[int], result: StudyResult) -> None:
    """Print carbon-study summary with CO2-oriented columns."""
    print(f"Experiment '{name}' carbon study")
    print(f"Seeds: {len(seeds)} ({min(seeds)}..{max(seeds)})")
    print(f"Output dir: {result.output_dir}")

    if result.summary.empty:
        print("No carbon-study results were produced.")
    else:
        print("Carbon summary rows (sorted by co2_per_completed_task_lb_mean):")
        top = result.summary.sort_values("co2_per_completed_task_lb_mean").head(15)
        columns = [
            "study_id",
            "scenario",
            "method",
            "node_count",
            "task_count",
            "n_runs",
            "avg_latency_mean",
            "throughput_mean",
            "co2_total_lb_mean",
            "co2_per_completed_task_lb_mean",
        ]
        available = [col for col in columns if col in top.columns]
        print(top[available].to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    for key, path in result.output_paths.items():
        print(f"{key}: {path}")


def _print_scalability_result(
    name: str,
    spec: ScalabilitySweepSpec,
    result: ScalabilitySweepResult,
) -> None:
    """Print scalability sweep summary table and generated artifact paths."""
    print(f"Experiment '{name}' scalability profile")
    print(f"Scenario: {spec.scenario}")
    print(f"Topology: {spec.topology}")
    print(f"Nodes: {', '.join(str(value) for value in spec.node_counts)}")
    print(f"Tasks: {', '.join(str(value) for value in spec.task_counts)}")
    print(f"Algorithms: {', '.join(spec.algorithms)}")
    print(f"Repeats per point: {spec.repeats}")
    print(f"Strict algorithm comparison: {spec.strict_algorithm_comparison}")
    expected_runs = (
        len(spec.node_counts) * len(spec.task_counts) * len(spec.algorithms) * int(spec.repeats)
    )
    print(f"Total runs: {len(result.runs_df)} (expected {expected_runs})")

    if result.summary_df.empty:
        print("No scalability summary results were produced.")
    else:
        print("Scalability summary (mean/std):")
        summary_columns = [
            "node_count",
            "task_count",
            "algorithm",
            "runs",
            "runtime_seconds_mean",
            "runtime_seconds_std",
            "avg_latency_mean",
            "throughput_mean",
            "avg_load_mean",
            "pending_tasks_mean",
            "deadline_violations_mean",
        ]
        available_columns = [col for col in summary_columns if col in result.summary_df.columns]
        print(
            result.summary_df[available_columns].to_string(
                index=False,
                float_format=lambda value: f"{value:.3f}",
            )
        )

    for key, path in result.output_paths.items():
        print(f"{key}: {path}")


def _print_chapter10_result(name: str, result: Chapter10Result) -> None:
    """Print chapter10 artifact summary."""
    print(f"Experiment '{name}' chapter10 package")
    print(f"Output dir: {result.output_dir}")
    print(f"Summary rows: {len(result.summary)}")
    print(f"Hypotheses rows: {len(result.hypotheses)}")
    for key, path in result.output_paths.items():
        print(f"{key}: {path}")


def _print_paper_bundle_result(name: str, result: PaperBundleResult) -> None:
    """Print consolidated paper-bundle result summary."""
    print(f"Experiment '{name}' paper bundle")
    print(f"Chapter10 output dir: {result.chapter10_output_dir}")
    print(f"Bundle output dir: {result.output_dir}")
    print(f"Files included: {result.file_count}")
    print(f"Bundle manifest: {result.bundle_manifest_path}")
    print(f"Bundle zip: {result.bundle_zip_path}")


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


if __name__ == "__main__":
    main()
