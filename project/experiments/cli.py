"""CLI parser schema for experiment run entrypoint."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser for experiment execution modes."""
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
        "--scenario",
        default=None,
        help="Scenario: static, dynamic-load, peak-load, node-failures, heterogeneous-tasks, mixed.",
    )
    parser.add_argument(
        "--disable-intelligence",
        action="store_true",
        help="Disable prediction/ML/ZNN layer for this run.",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM agent for this run.",
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        help="Override LLM provider: auto, openai, mock.",
    )
    parser.add_argument(
        "--ab-llm",
        action="store_true",
        help="Run A/B comparison: baseline algorithms vs LLM-guided control.",
    )
    parser.add_argument(
        "--ab-intelligence",
        action="store_true",
        help="Run A/B comparison: without intelligence vs with intelligence.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run comparison for algorithms from config optimization.compare_algorithms.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch matrix: scenarios x algorithms x repeats.",
    )
    parser.add_argument(
        "--batch-scenarios",
        default=None,
        help="Comma-separated list of scenarios for batch run.",
    )
    parser.add_argument(
        "--batch-algorithms",
        default=None,
        help="Comma-separated list of algorithms for batch run.",
    )
    parser.add_argument(
        "--batch-runs",
        type=int,
        default=3,
        help="Number of repeats per scenario/algorithm in batch run.",
    )
    parser.add_argument(
        "--batch-save-runs",
        action="store_true",
        help="Persist full observability artifacts for each batch run.",
    )
    parser.add_argument(
        "--batch-keep-adaptive",
        action="store_true",
        help="Keep adaptive intelligence and LLM behavior in batch mode.",
    )
    parser.add_argument(
        "--compare-algorithms",
        default=None,
        help="Comma-separated list of algorithms for comparison.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory for logs, CSV, JSON, and plots.",
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
    parser.add_argument(
        "--repro-check",
        action="store_true",
        help="Run the same configuration multiple times and verify reproducibility.",
    )
    parser.add_argument(
        "--repro-runs",
        type=int,
        default=3,
        help="Number of repeated runs for --repro-check.",
    )
    parser.add_argument(
        "--publication-study",
        action="store_true",
        help="Run publication pipeline (E1-E5, H1-H5, stats, plots, report).",
    )
    parser.add_argument(
        "--study-seeds",
        default="42-71",
        help="Seeds for publication study: comma list (42,43,44) or range (42-71).",
    )
    parser.add_argument(
        "--study-quick",
        action="store_true",
        help="Run reduced publication pipeline for quick verification.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for experiment execution modes."""
    return build_parser().parse_args(list(argv) if argv is not None else None)

