"""Performance budget gate for scalability profiling in CI/local runs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig, load_config
from project.experiments.scalability import (
    ScalabilitySweepSpec,
    run_scalability_sweep,
)


@dataclass(slots=True)
class PerformanceBudgetSpec:
    """Threshold contract for scalability sweep quality/performance."""

    node_counts: list[int]
    task_counts: list[int]
    algorithms: list[str]
    repeats: int
    topology: str
    scenario: str
    strict_algorithm_comparison: bool
    max_runtime_seconds: float
    min_throughput: float
    max_pending_tasks: int | None = None


@dataclass(slots=True)
class PerformanceBudgetResult:
    """Scalability budget check output."""

    passed: bool
    violations: list[str]
    report_path: str
    output_paths: dict[str, str]


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for scalability performance budget checks."""
    parser = argparse.ArgumentParser(
        description="Run scalability profiling and enforce performance budgets.",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to experiment config.")
    parser.add_argument("--nodes", default="10,50", help="Node counts for sweep.")
    parser.add_argument("--tasks", default="100,500", help="Task counts for sweep.")
    parser.add_argument(
        "--algorithms",
        default="round-robin,min-load,greedy",
        help="Algorithms for sweep.",
    )
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per sweep point.")
    parser.add_argument(
        "--topology",
        default="ring",
        choices=["ring", "mesh", "star"],
        help="Generated network topology.",
    )
    parser.add_argument(
        "--scenario",
        default="static",
        help="Scenario label for profile runs.",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=1.0,
        help="Maximum allowed runtime_seconds_mean for each sweep point.",
    )
    parser.add_argument(
        "--min-throughput",
        type=float,
        default=0.05,
        help="Minimum allowed throughput_mean for each sweep point.",
    )
    parser.add_argument(
        "--max-pending-tasks",
        type=int,
        default=None,
        help="Optional maximum allowed pending_tasks_mean for each sweep point.",
    )
    parser.add_argument(
        "--keep-adaptive",
        action="store_true",
        help="Keep intelligence/LLM enabled during budget checks.",
    )
    return parser


def run_performance_budget(
    config: ExperimentConfig,
    spec: PerformanceBudgetSpec,
    cli_args: list[str] | None = None,
) -> PerformanceBudgetResult:
    """Run sweep and evaluate configured performance budgets."""
    sweep_result = run_scalability_sweep(
        config=config,
        spec=ScalabilitySweepSpec(
            node_counts=list(spec.node_counts),
            task_counts=list(spec.task_counts),
            algorithms=list(spec.algorithms),
            repeats=max(1, int(spec.repeats)),
            topology=spec.topology,
            scenario=spec.scenario,
            strict_algorithm_comparison=spec.strict_algorithm_comparison,
        ),
        cli_args=list(cli_args or []),
    )
    violations = evaluate_performance_budget(sweep_result.summary_df, spec)
    report_path = _write_budget_report(
        config=config,
        spec=spec,
        summary_df=sweep_result.summary_df,
        violations=violations,
        output_paths=sweep_result.output_paths,
    )
    return PerformanceBudgetResult(
        passed=len(violations) == 0,
        violations=violations,
        report_path=report_path,
        output_paths=sweep_result.output_paths,
    )


def evaluate_performance_budget(
    summary_df: pd.DataFrame,
    spec: PerformanceBudgetSpec,
) -> list[str]:
    """Validate summary table against runtime/throughput/pending budgets."""
    violations: list[str] = []
    if summary_df.empty:
        return ["Scalability summary is empty."]

    required = {"node_count", "task_count", "algorithm"}
    if not required.issubset(set(summary_df.columns)):
        return ["Scalability summary missing required key columns."]

    for _, row in summary_df.iterrows():
        point = (
            f"nodes={int(row['node_count'])}, tasks={int(row['task_count'])}, "
            f"algorithm={row['algorithm']}"
        )
        runtime = _safe_float(row.get("runtime_seconds_mean"), fallback=0.0)
        if runtime > spec.max_runtime_seconds:
            violations.append(
                f"{point}: runtime_seconds_mean={runtime:.6f} exceeds {spec.max_runtime_seconds:.6f}"
            )

        throughput = _safe_float(row.get("throughput_mean"), fallback=0.0)
        if throughput < spec.min_throughput:
            violations.append(
                f"{point}: throughput_mean={throughput:.6f} below {spec.min_throughput:.6f}"
            )

        if spec.max_pending_tasks is not None:
            pending = _safe_float(row.get("pending_tasks_mean"), fallback=0.0)
            if pending > float(spec.max_pending_tasks):
                violations.append(
                    f"{point}: pending_tasks_mean={pending:.3f} exceeds {float(spec.max_pending_tasks):.3f}"
                )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for performance budget gate."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    base_config = load_config(args.config)
    optimized_config = replace(
        base_config,
        scenario=_normalize_scenario(args.scenario),
        observability=replace(
            base_config.observability,
            save_plots=False,
        ),
    )
    spec = PerformanceBudgetSpec(
        node_counts=_parse_positive_int_csv(args.nodes, fallback=[10, 50]),
        task_counts=_parse_positive_int_csv(args.tasks, fallback=[100, 500]),
        algorithms=_parse_algorithms(args.algorithms, fallback=base_config.optimization.compare_algorithms),
        repeats=max(1, int(args.repeats)),
        topology=str(args.topology).strip().lower(),
        scenario=_normalize_scenario(args.scenario),
        strict_algorithm_comparison=not bool(args.keep_adaptive),
        max_runtime_seconds=max(0.001, float(args.max_runtime_seconds)),
        min_throughput=max(0.0, float(args.min_throughput)),
        max_pending_tasks=(
            int(args.max_pending_tasks)
            if args.max_pending_tasks is not None and int(args.max_pending_tasks) >= 0
            else None
        ),
    )
    result = run_performance_budget(
        config=optimized_config,
        spec=spec,
        cli_args=list(argv or []),
    )
    print(f"Performance budget report: {result.report_path}")
    if result.passed:
        print("Performance budget: PASSED")
        return 0

    print("Performance budget: FAILED")
    for item in result.violations:
        print(f"- {item}")
    return 2


def _write_budget_report(
    *,
    config: ExperimentConfig,
    spec: PerformanceBudgetSpec,
    summary_df: pd.DataFrame,
    violations: list[str],
    output_paths: dict[str, str],
) -> str:
    """Persist budget evaluation report as JSON."""
    out_dir = Path(config.observability.output_dir) / config.name / "scalability-budget"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "performance_budget_report.json"
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": len(violations) == 0,
        "violations": list(violations),
        "spec": {
            "node_counts": list(spec.node_counts),
            "task_counts": list(spec.task_counts),
            "algorithms": list(spec.algorithms),
            "repeats": int(spec.repeats),
            "topology": spec.topology,
            "scenario": spec.scenario,
            "strict_algorithm_comparison": spec.strict_algorithm_comparison,
            "max_runtime_seconds": spec.max_runtime_seconds,
            "min_throughput": spec.min_throughput,
            "max_pending_tasks": spec.max_pending_tasks,
        },
        "summary_rows": len(summary_df),
        "summary_head": json.loads(summary_df.head(20).to_json(orient="records")),
        "scalability_artifacts": dict(output_paths),
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return str(report_path)


def _parse_positive_int_csv(raw: str, fallback: list[int]) -> list[int]:
    """Parse comma-separated positive integers with uniqueness."""
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


def _parse_algorithms(raw: str, fallback: list[str]) -> list[str]:
    """Parse algorithm list with canonical normalization and uniqueness."""
    parsed: list[str] = []
    source = str(raw).split(",") if raw else list(fallback)
    for item in source:
        name = normalize_algorithm(item)
        if name not in parsed:
            parsed.append(name)
    return parsed or list(fallback)


def _normalize_scenario(value: str) -> str:
    """Normalize scenario name into canonical slug."""
    return str(value).strip().lower().replace("_", "-").replace(" ", "-")


def _safe_float(value: object, fallback: float) -> float:
    """Best-effort float conversion with fallback."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float(fallback)


if __name__ == "__main__":
    raise SystemExit(main())
