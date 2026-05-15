"""Scalability baseline report generator for docs/baselines artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for scalability baseline report generation."""
    parser = argparse.ArgumentParser(
        description="Generate scalability baseline JSON and markdown report from summary CSV.",
    )
    parser.add_argument(
        "--summary-csv",
        required=True,
        help="Path to scalability_summary.csv produced by scalability-profile mode.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/baselines/scalability_baseline.json",
        help="Path to output scalability baseline JSON file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/baselines/scalability_baseline_report.md",
        help="Path to output markdown report file.",
    )
    parser.add_argument(
        "--schema-version",
        default="sprint17-scalability-baseline-v1",
        help="Schema version marker for generated baseline file.",
    )
    parser.add_argument("--scenario", default="static", help="Scenario label for baseline sweep.")
    parser.add_argument("--topology", default="ring", help="Topology label for baseline sweep.")
    parser.add_argument("--nodes", default="10,50", help="Node counts used in baseline sweep.")
    parser.add_argument("--tasks", default="100,500", help="Task counts used in baseline sweep.")
    parser.add_argument(
        "--algorithms",
        default="round-robin,min-load,greedy",
        help="Algorithms used in baseline sweep.",
    )
    return parser


def generate_scalability_baseline(
    summary_df: pd.DataFrame,
    *,
    schema_version: str,
    scenario: str,
    topology: str,
    node_counts: list[int],
    task_counts: list[int],
    algorithms: list[str],
    source_summary_csv: str,
) -> dict[str, Any]:
    """Build normalized scalability baseline payload from summary table."""
    rows = _normalize_summary_rows(summary_df)
    winners = _compute_winners(rows)
    return {
        "schema_version": schema_version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_summary_csv": source_summary_csv,
        "spec": {
            "scenario": scenario,
            "topology": topology,
            "node_counts": list(node_counts),
            "task_counts": list(task_counts),
            "algorithms": list(algorithms),
        },
        "notes": {
            "runtime_seconds_mean_machine_dependent": True,
            "latency_throughput_pending_deadline_deterministic_given_seed": True,
        },
        "rows": rows,
        "winners_by_point": winners,
    }


def render_scalability_markdown(baseline: dict[str, Any]) -> str:
    """Render markdown report from generated baseline payload."""
    spec = baseline.get("spec", {})
    rows = baseline.get("rows", [])
    winners = baseline.get("winners_by_point", [])
    lines: list[str] = []
    lines.append("# Scalability Baseline Report")
    lines.append("")
    lines.append(f"Generated at (UTC): {baseline.get('created_at_utc', 'n/a')}")
    lines.append(f"Schema version: `{baseline.get('schema_version', 'n/a')}`")
    lines.append("")
    lines.append("## Sweep Specification")
    lines.append("")
    lines.append(f"- Scenario: `{spec.get('scenario', 'n/a')}`")
    lines.append(f"- Topology: `{spec.get('topology', 'n/a')}`")
    lines.append(f"- Nodes: `{spec.get('node_counts', [])}`")
    lines.append(f"- Tasks: `{spec.get('task_counts', [])}`")
    lines.append(f"- Algorithms: `{spec.get('algorithms', [])}`")
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append(
        "| nodes | tasks | algorithm | runtime_s | avg_latency | throughput | avg_load | pending | deadline_violations |"
    )
    lines.append("|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {int(row['node_count'])} | {int(row['task_count'])} | {row['algorithm']} | "
            f"{row['runtime_seconds_mean']:.6f} | {row['avg_latency_mean']:.3f} | "
            f"{row['throughput_mean']:.3f} | {row['avg_load_mean']:.3f} | "
            f"{row['pending_tasks_mean']:.3f} | {row['deadline_violations_mean']:.3f} |"
        )
    lines.append("")
    lines.append("## Winners By Scale Point")
    lines.append("")
    lines.append("| nodes | tasks | winner | score |")
    lines.append("|---:|---:|---|---:|")
    for item in winners:
        lines.append(
            f"| {int(item['node_count'])} | {int(item['task_count'])} | "
            f"{item['algorithm']} | {item['score']:.3f} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `runtime_seconds_mean` is machine-dependent and used as a relative baseline.")
    lines.append("- Quality metrics are deterministic for fixed seeds/spec.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for scalability baseline report generation."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    summary_csv = Path(str(args.summary_csv))
    if not summary_csv.exists():
        print(f"Summary CSV not found: {summary_csv}")
        return 2
    summary_df = pd.read_csv(summary_csv)
    baseline = generate_scalability_baseline(
        summary_df,
        schema_version=str(args.schema_version),
        scenario=str(args.scenario),
        topology=str(args.topology),
        node_counts=_parse_positive_int_csv(str(args.nodes), fallback=[10, 50]),
        task_counts=_parse_positive_int_csv(str(args.tasks), fallback=[100, 500]),
        algorithms=_parse_string_csv(str(args.algorithms)),
        source_summary_csv=str(summary_csv),
    )
    output_json = Path(str(args.output_json))
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, sort_keys=True)

    output_md = Path(str(args.output_md))
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_scalability_markdown(baseline), encoding="utf-8")
    print(f"Scalability baseline JSON: {output_json}")
    print(f"Scalability baseline report: {output_md}")
    return 0


def _normalize_summary_rows(summary_df: pd.DataFrame) -> list[dict[str, float | str | int]]:
    """Extract canonical row objects from summary dataframe."""
    if summary_df.empty:
        return []
    rows: list[dict[str, float | str | int]] = []
    ordered = summary_df.sort_values(
        ["node_count", "task_count", "algorithm"],
        ascending=[True, True, True],
    )
    for _, row in ordered.iterrows():
        rows.append(
            {
                "node_count": int(row["node_count"]),
                "task_count": int(row["task_count"]),
                "algorithm": str(row["algorithm"]),
                "runtime_seconds_mean": _safe_float(row.get("runtime_seconds_mean"), 0.0),
                "avg_latency_mean": _safe_float(row.get("avg_latency_mean"), 0.0),
                "throughput_mean": _safe_float(row.get("throughput_mean"), 0.0),
                "avg_load_mean": _safe_float(row.get("avg_load_mean"), 0.0),
                "pending_tasks_mean": _safe_float(row.get("pending_tasks_mean"), 0.0),
                "deadline_violations_mean": _safe_float(
                    row.get("deadline_violations_mean"), 0.0
                ),
            }
        )
    return rows


def _compute_winners(rows: list[dict[str, float | str | int]]) -> list[dict[str, float | str | int]]:
    """Compute one winner per (node_count, task_count) scale point."""
    grouped: dict[tuple[int, int], list[dict[str, float | str | int]]] = {}
    for row in rows:
        key = (int(row["node_count"]), int(row["task_count"]))
        grouped.setdefault(key, []).append(row)

    winners: list[dict[str, float | str | int]] = []
    for (node_count, task_count), items in sorted(grouped.items()):
        winner = min(
            items,
            key=lambda item: (
                _safe_float(item.get("avg_latency_mean"), 0.0),
                -_safe_float(item.get("throughput_mean"), 0.0),
                _safe_float(item.get("pending_tasks_mean"), 0.0),
                _safe_float(item.get("deadline_violations_mean"), 0.0),
            ),
        )
        score = (
            _safe_float(winner.get("avg_latency_mean"), 0.0)
            - _safe_float(winner.get("throughput_mean"), 0.0) * 0.1
            + _safe_float(winner.get("pending_tasks_mean"), 0.0) * 0.01
            + _safe_float(winner.get("deadline_violations_mean"), 0.0) * 0.25
        )
        winners.append(
            {
                "node_count": node_count,
                "task_count": task_count,
                "algorithm": str(winner["algorithm"]),
                "score": float(score),
            }
        )
    return winners


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


def _parse_string_csv(raw: str) -> list[str]:
    """Parse comma-separated strings preserving order and uniqueness."""
    parsed: list[str] = []
    for item in str(raw).split(","):
        token = item.strip()
        if token and token not in parsed:
            parsed.append(token)
    return parsed


def _safe_float(value: object, fallback: float) -> float:
    """Best-effort float conversion."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float(fallback)


if __name__ == "__main__":
    raise SystemExit(main())
