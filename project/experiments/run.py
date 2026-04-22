from __future__ import annotations

import argparse
from dataclasses import replace
import logging
from pathlib import Path

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig, load_config
from project.core.models import SystemState
from project.experiments.controller import Experiment
from project.metrics import persist_observability, summarize_state

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run experimental testbed simulation.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to experiment config file.",
    )
    parser.add_argument(
        "--algorithm",
        default=None,
        help="Scheduling algorithm: round-robin, min-load, greedy.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run comparison for algorithms from config optimization.compare_algorithms.",
    )
    parser.add_argument(
        "--compare-algorithms",
        default=None,
        help="Comma-separated list of algorithms for comparison.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory for logs, CSV, and plots.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Disable CSV export for this run.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Disable plot export for this run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _apply_runtime_overrides(load_config(args.config), args)
    log_path = _configure_logging(config)
    LOGGER.info("Run started: experiment=%s", config.name)

    if args.compare:
        algorithms = _parse_compare_algorithms(args.compare_algorithms)
        if not algorithms:
            algorithms = config.optimization.compare_algorithms
        _run_comparison(config, algorithms)
        LOGGER.info("Comparison run finished. Log: %s", log_path)
        return

    final_state = Experiment(config=config).run()
    artifacts = _persist_run_artifacts(config, final_state)
    _print_single_result(config.name, final_state, artifacts)
    LOGGER.info("Single run finished. Log: %s", log_path)


def _run_comparison(config: ExperimentConfig, algorithms: list[str]) -> None:
    print(f"Experiment '{config.name}' comparison")
    print(
        "algorithm | completed | pending | deadline_violations | latency | throughput | avg_load"
    )
    print("-" * 94)

    rows: list[dict[str, object]] = []
    for algorithm in algorithms:
        scenario_config = _with_algorithm(config, algorithm)
        state = Experiment(config=scenario_config).run()
        rows.append(summarize_state(state))
        _persist_run_artifacts(scenario_config, state)
        print(
            f"{state.selected_algorithm} | {state.completed_tasks} | {state.pending_tasks} | "
            f"{state.deadline_violations} | {state.avg_latency:.3f} | "
            f"{state.throughput:.3f} | {state.avg_load:.3f}"
        )

    comparison_df = pd.DataFrame(rows)
    comparison_dir = Path(config.observability.output_dir) / config.name
    comparison_dir.mkdir(parents=True, exist_ok=True)
    comparison_csv = comparison_dir / "comparison.csv"
    comparison_df.to_csv(comparison_csv, index=False)
    print(f"Comparison CSV: {comparison_csv}")


def _apply_runtime_overrides(config: ExperimentConfig, args: argparse.Namespace) -> ExperimentConfig:
    if args.algorithm:
        config = _with_algorithm(config, args.algorithm)

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


def _persist_run_artifacts(config: ExperimentConfig, state: SystemState) -> dict[str, str]:
    output_dir = (
        Path(config.observability.output_dir)
        / config.name
        / state.selected_algorithm
    )
    return persist_observability(
        state=state,
        output_dir=output_dir,
        save_csv=config.observability.save_csv,
        save_plots=config.observability.save_plots,
    )


def _with_algorithm(config: ExperimentConfig, algorithm: str) -> ExperimentConfig:
    optimization = replace(config.optimization, algorithm=normalize_algorithm(algorithm))
    return replace(config, optimization=optimization)


def _parse_compare_algorithms(raw: str | None) -> list[str]:
    if not raw:
        return []
    parsed: list[str] = []
    for item in raw.split(","):
        name = normalize_algorithm(item)
        if name not in parsed:
            parsed.append(name)
    return parsed


def _print_single_result(name: str, final_state: SystemState, artifacts: dict[str, str]) -> None:
    print(f"Experiment '{name}' completed.")
    print(f"Algorithm: {final_state.selected_algorithm}")
    print(f"Simulation time: {final_state.current_time}")
    print(f"Completed tasks: {final_state.completed_tasks}")
    print(f"Pending tasks: {final_state.pending_tasks}")
    print(f"Queue size: {final_state.queue_lengths.get('global', 0)}")
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


def _configure_logging(config: ExperimentConfig) -> Path:
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

