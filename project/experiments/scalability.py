"""Scalability profiling harness for nodes/tasks sweep experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import random
import time

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig
from project.core.models import NetworkEdge, Node, Task
from project.experiments.controller import Experiment
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest, write_manifest
from project.metrics import summarize_state


DEFAULT_SWEEP_NODES = [10, 50, 100, 500]
DEFAULT_SWEEP_TASKS = [100, 500, 1000, 5000]
DEFAULT_TOPOLOGY = "ring"


@dataclass(slots=True)
class ScalabilitySweepSpec:
    """Input specification for scalability profiling sweep."""

    node_counts: list[int]
    task_counts: list[int]
    algorithms: list[str]
    repeats: int = 1
    topology: str = DEFAULT_TOPOLOGY
    scenario: str = "static"
    strict_algorithm_comparison: bool = True


@dataclass(slots=True)
class ScalabilitySweepResult:
    """Tabular outputs and artifact paths for one scalability sweep."""

    runs_df: pd.DataFrame
    summary_df: pd.DataFrame
    output_paths: dict[str, str]


def run_scalability_sweep(
    config: ExperimentConfig,
    spec: ScalabilitySweepSpec,
    cli_args: list[str] | None = None,
) -> ScalabilitySweepResult:
    """Execute sweep across node/task scales and aggregate runtime/quality metrics."""
    node_counts = _normalize_positive_ints(spec.node_counts, fallback=DEFAULT_SWEEP_NODES)
    task_counts = _normalize_positive_ints(spec.task_counts, fallback=DEFAULT_SWEEP_TASKS)
    algorithms = _normalize_algorithms(spec.algorithms, fallback=[config.optimization.algorithm])
    repeats = max(1, int(spec.repeats))
    topology = _normalize_topology(spec.topology)
    scenario = _normalize_scenario_name(spec.scenario)
    cli_args = list(cli_args or [])

    rows: list[dict[str, object]] = []
    for node_count in node_counts:
        nodes = _build_nodes(node_count)
        edges = _build_network_edges(nodes, topology=topology)
        for task_count in task_counts:
            for repeat_idx in range(repeats):
                run_seed = _derive_run_seed(
                    base_seed=config.simulation.seed,
                    node_count=node_count,
                    task_count=task_count,
                    repeat_idx=repeat_idx,
                )
                tasks = _build_tasks(
                    task_count=task_count,
                    time_horizon=config.simulation.time_horizon,
                    seed=run_seed,
                )
                for algorithm in algorithms:
                    run_config = replace(
                        config,
                        scenario=scenario,
                        simulation=replace(config.simulation, seed=run_seed),
                        optimization=replace(config.optimization, algorithm=algorithm),
                        nodes=list(nodes),
                        network_edges=list(edges),
                        initial_tasks=list(tasks),
                    )
                    if spec.strict_algorithm_comparison:
                        run_config = replace(
                            run_config,
                            intelligence=replace(
                                run_config.intelligence,
                                enabled=False,
                                adaptive_algorithm=False,
                            ),
                            llm=replace(run_config.llm, enabled=False),
                        )

                    started_at = time.perf_counter()
                    state = Experiment(config=run_config).run()
                    elapsed = time.perf_counter() - started_at
                    rows.append(
                        {
                            "node_count": node_count,
                            "task_count": task_count,
                            "repeat": repeat_idx + 1,
                            "seed": run_seed,
                            "topology": topology,
                            "configured_scenario": scenario,
                            "configured_algorithm": algorithm,
                            "runtime_seconds": elapsed,
                            **summarize_state(state),
                        }
                    )

    runs_df = pd.DataFrame(rows)
    summary_df = _build_scalability_summary(runs_df)
    output_paths = _persist_scalability_outputs(
        config=config,
        spec=ScalabilitySweepSpec(
            node_counts=node_counts,
            task_counts=task_counts,
            algorithms=algorithms,
            repeats=repeats,
            topology=topology,
            scenario=scenario,
            strict_algorithm_comparison=bool(spec.strict_algorithm_comparison),
        ),
        runs_df=runs_df,
        summary_df=summary_df,
        cli_args=cli_args,
    )
    return ScalabilitySweepResult(
        runs_df=runs_df,
        summary_df=summary_df,
        output_paths=output_paths,
    )


def _normalize_positive_ints(values: list[int], fallback: list[int]) -> list[int]:
    """Normalize positive integer list while preserving order and uniqueness."""
    normalized: list[int] = []
    for raw in values:
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            continue
        if parsed < 1:
            continue
        if parsed not in normalized:
            normalized.append(parsed)
    return normalized or list(fallback)


def _normalize_algorithms(values: list[str], fallback: list[str]) -> list[str]:
    """Normalize algorithm names while preserving order and uniqueness."""
    normalized: list[str] = []
    for raw in values or fallback:
        name = normalize_algorithm(raw)
        if name not in normalized:
            normalized.append(name)
    return normalized


def _normalize_topology(name: str) -> str:
    """Normalize supported topology value."""
    normalized = str(name).strip().lower()
    if normalized in {"ring", "mesh", "star"}:
        return normalized
    return DEFAULT_TOPOLOGY


def _normalize_scenario_name(name: str) -> str:
    """Normalize scenario label into canonical slug."""
    return str(name).strip().lower().replace("_", "-").replace(" ", "-")


def _derive_run_seed(
    *,
    base_seed: int,
    node_count: int,
    task_count: int,
    repeat_idx: int,
) -> int:
    """Build deterministic seed unique for one sweep point."""
    return int(base_seed + node_count * 1_000_000 + task_count * 1_000 + repeat_idx)


def _build_nodes(node_count: int) -> list[Node]:
    """Generate heterogeneous node set for requested cluster size."""
    cpu_tiers = [8.0, 12.0, 16.0, 24.0]
    memory_tiers = [16.0, 24.0, 32.0, 64.0]
    nodes: list[Node] = []
    for idx in range(node_count):
        tier = idx % len(cpu_tiers)
        nodes.append(
            Node(
                id=f"node-{idx + 1:04d}",
                cpu=cpu_tiers[tier],
                memory=memory_tiers[tier],
                gpu=1.0 if (idx % 5 == 0) else 0.0,
            )
        )
    return nodes


def _build_network_edges(nodes: list[Node], *, topology: str) -> list[NetworkEdge]:
    """Generate directed network edge set for one topology."""
    if len(nodes) <= 1:
        return []
    node_ids = [node.id for node in nodes]
    edges: list[NetworkEdge] = []
    if topology == "mesh":
        for source in node_ids:
            for target in node_ids:
                if source == target:
                    continue
                edges.append(
                    NetworkEdge(source=source, target=target, bandwidth=1000.0, latency=4.0)
                )
        return edges
    if topology == "star":
        center = node_ids[0]
        for node_id in node_ids[1:]:
            edges.append(
                NetworkEdge(source=center, target=node_id, bandwidth=1200.0, latency=3.0)
            )
            edges.append(
                NetworkEdge(source=node_id, target=center, bandwidth=1200.0, latency=3.0)
            )
        return edges

    for idx, source in enumerate(node_ids):
        target = node_ids[(idx + 1) % len(node_ids)]
        edges.append(NetworkEdge(source=source, target=target, bandwidth=900.0, latency=5.0))
        edges.append(NetworkEdge(source=target, target=source, bandwidth=900.0, latency=5.0))
    return edges


def _build_tasks(task_count: int, time_horizon: int, seed: int) -> list[Task]:
    """Generate deterministic synthetic workload for one scale point."""
    rng = random.Random(seed)
    horizon = max(1, int(time_horizon))
    tasks: list[Task] = []
    for idx in range(task_count):
        arrival_time = rng.randint(0, max(0, horizon - 1))
        duration = rng.randint(1, 6)
        cpu_required = round(rng.uniform(1.0, 6.0), 3)
        memory_required = round(rng.uniform(2.0, 14.0), 3)
        data_size = round(rng.uniform(32.0, 1024.0), 3)
        deadline = float(arrival_time + duration + rng.randint(2, 10))
        tasks.append(
            Task(
                id=f"task-{idx + 1:06d}",
                cpu_required=cpu_required,
                memory_required=memory_required,
                data_size=data_size,
                deadline=deadline,
                arrival_time=arrival_time,
                duration=duration,
            )
        )
    return tasks


def _build_scalability_summary(runs_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-run outputs for each (nodes,tasks,algorithm) point."""
    if runs_df.empty:
        return pd.DataFrame()

    metric_columns = [
        "runtime_seconds",
        "completed_tasks",
        "pending_tasks",
        "deadline_violations",
        "avg_latency",
        "throughput",
        "avg_load",
    ]
    grouped = runs_df.groupby(
        ["node_count", "task_count", "algorithm"], as_index=False
    )[metric_columns].agg(["mean", "std"])
    grouped.columns = [
        f"{col}_{stat}" if stat else col for col, stat in grouped.columns.to_flat_index()
    ]
    grouped = grouped.rename(
        columns={
            "node_count_": "node_count",
            "task_count_": "task_count",
            "algorithm_": "algorithm",
        }
    )
    counts = (
        runs_df.groupby(["node_count", "task_count", "algorithm"], as_index=False)
        .size()
        .rename(columns={"size": "runs"})
    )
    summary = grouped.merge(counts, on=["node_count", "task_count", "algorithm"], how="left")
    std_columns = [col for col in summary.columns if col.endswith("_std")]
    if std_columns:
        summary[std_columns] = summary[std_columns].fillna(0.0)
    return summary.sort_values(
        ["node_count", "task_count", "runtime_seconds_mean", "algorithm"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)


def _persist_scalability_outputs(
    *,
    config: ExperimentConfig,
    spec: ScalabilitySweepSpec,
    runs_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    cli_args: list[str],
) -> dict[str, str]:
    """Persist scalability run tables/manifests and return artifact map."""
    out_dir = Path(config.observability.output_dir) / config.name / "scalability-profile"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths: dict[str, str] = {}

    if config.observability.save_csv:
        runs_csv = out_dir / "scalability_runs.csv"
        runs_df.to_csv(runs_csv, index=False)
        artifact_paths["scalability_runs_csv"] = str(runs_csv)

        summary_csv = out_dir / "scalability_summary.csv"
        summary_df.to_csv(summary_csv, index=False)
        artifact_paths["scalability_summary_csv"] = str(summary_csv)

    if config.observability.save_json:
        runs_json = out_dir / "scalability_runs.json"
        _write_json(runs_json, runs_df.to_dict(orient="records"))
        artifact_paths["scalability_runs_json"] = str(runs_json)

        summary_json = out_dir / "scalability_summary.json"
        _write_json(summary_json, summary_df.to_dict(orient="records"))
        artifact_paths["scalability_summary_json"] = str(summary_json)

        spec_json = out_dir / "scalability_spec.json"
        _write_json(
            spec_json,
            {
                "node_counts": list(spec.node_counts),
                "task_counts": list(spec.task_counts),
                "algorithms": list(spec.algorithms),
                "repeats": int(spec.repeats),
                "topology": spec.topology,
                "scenario": spec.scenario,
                "strict_algorithm_comparison": spec.strict_algorithm_comparison,
            },
        )
        artifact_paths["scalability_spec_json"] = str(spec_json)

    manifest = build_run_manifest(
        config=config,
        mode="scalability-profile",
        cli_args=cli_args,
        extra={
            "node_counts": list(spec.node_counts),
            "task_counts": list(spec.task_counts),
            "algorithms": list(spec.algorithms),
            "repeats": int(spec.repeats),
            "topology": spec.topology,
            "scenario": spec.scenario,
            "strict_algorithm_comparison": spec.strict_algorithm_comparison,
            "total_runs": int(len(runs_df)),
            "summary_rows": int(len(summary_df)),
        },
    )
    manifest_path = write_manifest(out_dir / "scalability_manifest.json", manifest)
    artifact_paths["scalability_manifest_json"] = manifest_path

    if artifact_paths:
        integrity_path = write_artifact_integrity_file(
            out_dir / "artifact_integrity.json",
            artifact_paths,
        )
        artifact_paths["artifact_integrity_json"] = integrity_path
    return artifact_paths


def _write_json(path: Path, payload: object) -> None:
    """Write JSON payload to file using deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
