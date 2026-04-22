from __future__ import annotations

import argparse

from project.core.config import load_config
from project.experiments.controller import Experiment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run experimental testbed simulation.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to experiment config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    experiment = Experiment(config=config)
    final_state = experiment.run()
    print(f"Experiment '{config.name}' completed.")
    print(f"Nodes: {len(config.nodes)}, initial tasks: {len(config.initial_tasks)}")
    print(f"Simulation time: {final_state.current_time}")
    print(f"Completed tasks: {final_state.completed_tasks}")
    print(f"Pending tasks: {final_state.pending_tasks}")
    print(f"Queue size: {final_state.queue_lengths.get('global', 0)}")
    print(f"State updates: {len(final_state.history)}")
    print(f"Final node loads: {final_state.node_loads}")


if __name__ == "__main__":
    main()
