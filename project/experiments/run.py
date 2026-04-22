from __future__ import annotations

import argparse
from dataclasses import replace

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig, load_config
from project.core.models import SystemState
from project.experiments.controller import Experiment


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.algorithm:
        config = _with_algorithm(config, args.algorithm)

    if args.compare:
        algorithms = _parse_compare_algorithms(args.compare_algorithms)
        if not algorithms:
            algorithms = config.optimization.compare_algorithms
        _run_comparison(config, algorithms)
        return

    final_state = Experiment(config=config).run()
    _print_single_result(config.name, final_state)


def _run_comparison(config: ExperimentConfig, algorithms: list[str]) -> None:
    print(f"Experiment '{config.name}' comparison")
    print("algorithm | completed | pending | deadline_violations | mas_assignments | mas_messages")
    print("-" * 86)
    for algorithm in algorithms:
        scenario_config = _with_algorithm(config, algorithm)
        state = Experiment(config=scenario_config).run()
        print(
            f"{state.selected_algorithm} | {state.completed_tasks} | {state.pending_tasks} | "
            f"{state.deadline_violations} | {state.mas_assignments} | {state.mas_messages}"
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


def _print_single_result(name: str, final_state: SystemState) -> None:
    print(f"Experiment '{name}' completed.")
    print(f"Algorithm: {final_state.selected_algorithm}")
    print(f"Simulation time: {final_state.current_time}")
    print(f"Completed tasks: {final_state.completed_tasks}")
    print(f"Pending tasks: {final_state.pending_tasks}")
    print(f"Queue size: {final_state.queue_lengths.get('global', 0)}")
    print(f"Deadline violations: {final_state.deadline_violations}")
    print(f"MAS assignments: {final_state.mas_assignments}")
    print(f"MAS messages: {final_state.mas_messages}")
    print(f"State updates: {len(final_state.history)}")
    print(f"Final node loads: {final_state.node_loads}")


if __name__ == "__main__":
    main()
