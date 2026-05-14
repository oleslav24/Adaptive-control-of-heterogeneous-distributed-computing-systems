"""Mode resolution and dispatch helpers for experiments CLI entrypoint."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable, Mapping

from project.core.config import ExperimentConfig


ModeHandler = Callable[[ExperimentConfig, Namespace, list[str]], None]

MODE_FINISH_MESSAGES: dict[str, str] = {
    "publication-study": "Publication study finished",
    "ab-llm": "A/B LLM run finished",
    "ab-intelligence": "A/B intelligence run finished",
    "compare": "Comparison run finished",
    "batch": "Batch run finished",
    "repro-check": "Reproducibility check finished",
    "single": "Single run finished",
}


def resolve_mode(args: Namespace) -> str:
    """Resolve selected run mode from parsed CLI arguments."""
    if args.publication_study:
        return "publication-study"
    if args.ab_llm:
        return "ab-llm"
    if args.ab_intelligence:
        return "ab-intelligence"
    if args.compare:
        return "compare"
    if args.batch:
        return "batch"
    if args.repro_check:
        return "repro-check"
    return "single"


def dispatch_mode(
    *,
    mode: str,
    handlers: Mapping[str, ModeHandler],
    config: ExperimentConfig,
    args: Namespace,
    cli_args: list[str],
) -> None:
    """Execute handler for a resolved run mode."""
    handler = handlers.get(mode)
    if handler is None:
        raise ValueError(f"Unsupported mode: {mode}")
    handler(config, args, cli_args)

