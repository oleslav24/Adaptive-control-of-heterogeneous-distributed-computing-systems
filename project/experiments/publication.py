"""Publication-grade experiment pipeline (E1-E5, H1-H5, statistics, artifacts)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from project.core.config import (
    DynamicLoadConfig,
    ExperimentConfig,
    HeterogeneousTasksConfig,
    NodeFailureEventConfig,
    NodeFailuresConfig,
    PeakLoadConfig,
    ScenarioConfig,
)
from project.core.models import Task
from project.experiments.controller import Experiment
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.publication_catalog import (
    METHOD_CATALOG,
    NETWORK_PROFILES,
    MethodVariant,
    StudyRunSpec,
    build_study_specs,
    get_method_variant,
    method_to_row,
)
from project.experiments.publication_validation import (
    validate_hypotheses_table,
    validate_summary_statistics,
)
from project.simulation import init_system


@dataclass(slots=True)
class StudyResult:
    """Artifacts and tables produced by publication pipeline run."""

    output_dir: Path
    raw_runs: pd.DataFrame
    summary: pd.DataFrame
    hypothesis_df: pd.DataFrame
    methods_df: pd.DataFrame
    output_paths: dict[str, str]


def run_publication_pipeline(
    base_config: ExperimentConfig,
    *,
    seeds: list[int],
    quick: bool = False,
    save_plots: bool = True,
    cli_args: list[str] | None = None,
) -> StudyResult:
    """Run full publication pipeline and export tables, report, and plots."""
    cli_args = list(cli_args or [])
    seeds = sorted({int(seed) for seed in seeds})
    if not seeds:
        raise ValueError("At least one seed is required for publication study.")

    output_dir = Path(base_config.observability.output_dir) / base_config.name / "publication"
    output_dir.mkdir(parents=True, exist_ok=True)

    methods_df = pd.DataFrame([method_to_row(m) for m in METHOD_CATALOG])
    ready_methods = [m.key for m in METHOD_CATALOG if m.ready]
    unsupported_df = methods_df[methods_df["ready"] == False].copy()  # noqa: E712

    experiment_specs = build_study_specs(seeds=seeds, ready_methods=ready_methods, quick=quick)

    rows: list[dict[str, Any]] = []
    for spec in experiment_specs:
        for seed in spec.seeds:
            for method_key in spec.methods:
                variant = get_method_variant(method_key)
                run_cfg = _build_run_config(
                    base_config=base_config,
                    spec=spec,
                    variant=variant,
                    seed=seed,
                )
                final_state = Experiment(config=run_cfg).run()
                row = {
                    "study_id": spec.study_id,
                    "scenario": spec.scenario,
                    "node_count": spec.node_count,
                    "task_count": spec.task_count,
                    "task_type": spec.task_type,
                    "network_profile": spec.network_profile,
                    "topology": spec.topology,
                    "seed": seed,
                    "method": variant.key,
                    "method_label": variant.label,
                    "method_family": variant.family,
                    "algorithm": final_state.selected_algorithm,
                    **_derive_metrics(final_state),
                }
                rows.append(row)

    raw_runs = pd.DataFrame(rows)
    summary = _summarize_runs(raw_runs)
    validation = validate_summary_statistics(summary)
    if not validation.ok:
        message = "; ".join(validation.errors[:8])
        raise ValueError(f"Publication summary validation failed: {message}")
    hypothesis_df = _evaluate_hypotheses(raw_runs)
    hypothesis_validation = validate_hypotheses_table(hypothesis_df)
    if not hypothesis_validation.ok:
        message = "; ".join(hypothesis_validation.errors[:8])
        raise ValueError(f"Publication hypotheses validation failed: {message}")

    output_paths = _persist_publication_outputs(
        output_dir=output_dir,
        raw_runs=raw_runs,
        summary=summary,
        hypotheses=hypothesis_df,
        methods_df=methods_df,
        unsupported_df=unsupported_df,
        save_plots=save_plots,
    )
    validation_path = output_dir / "summary_validation.json"
    _write_json(
        validation_path,
        {
            "ok": validation.ok,
            "row_count": validation.row_count,
            "errors": validation.errors,
        },
    )
    output_paths["summary_validation_json"] = str(validation_path)
    hypothesis_validation_path = output_dir / "hypotheses_validation.json"
    _write_json(
        hypothesis_validation_path,
        {
            "ok": hypothesis_validation.ok,
            "row_count": hypothesis_validation.row_count,
            "errors": hypothesis_validation.errors,
        },
    )
    output_paths["hypotheses_validation_json"] = str(hypothesis_validation_path)

    manifest_path = output_dir / "publication_manifest.json"
    manifest = build_run_manifest(
        config=base_config,
        mode="publication-study",
        cli_args=cli_args,
        extra={
            "quick_mode": quick,
            "seed_count": len(seeds),
            "seeds": seeds,
            "study_specs": [asdict(spec) for spec in experiment_specs],
            "ready_methods": ready_methods,
            "unsupported_methods": unsupported_df["key"].tolist(),
            "output_files": output_paths,
        },
    )
    write_manifest(manifest_path, manifest)
    output_paths["publication_manifest_json"] = str(manifest_path)

    report_path = _write_publication_report(
        output_dir=output_dir,
        summary=summary,
        hypotheses=hypothesis_df,
        methods_df=methods_df,
        seed_count=len(seeds),
        quick_mode=quick,
    )
    output_paths["publication_report_md"] = str(report_path)

    return StudyResult(
        output_dir=output_dir,
        raw_runs=raw_runs,
        summary=summary,
        hypothesis_df=hypothesis_df,
        methods_df=methods_df,
        output_paths=output_paths,
    )


def _build_run_config(
    *,
    base_config: ExperimentConfig,
    spec: StudyRunSpec,
    variant: MethodVariant,
    seed: int,
) -> ExperimentConfig:
    """Derive run-specific config for one study/method/seed combination."""
    profile = NETWORK_PROFILES[spec.network_profile]
    initialized = init_system(
        spec.node_count,
        spec.topology,
        bandwidth=profile["bandwidth"],
        latency=profile["latency"],
    )
    tasks = _generate_tasks(
        task_count=spec.task_count,
        task_type=spec.task_type,
        seed=seed,
        horizon=_suggest_horizon(spec.node_count, spec.task_count),
    )
    scenario_cfg = _build_scenario_config(
        scenario=spec.scenario,
        node_count=spec.node_count,
        task_count=spec.task_count,
        horizon=_suggest_horizon(spec.node_count, spec.task_count),
        failure_node_id=f"node-{max(1, spec.node_count // 2)}",
    )

    return replace(
        base_config,
        name=base_config.name,
        scenario=spec.scenario,
        simulation=replace(
            base_config.simulation,
            seed=seed,
            time_horizon=_suggest_horizon(spec.node_count, spec.task_count),
        ),
        optimization=replace(base_config.optimization, algorithm=variant.algorithm),
        intelligence=replace(
            base_config.intelligence,
            enabled=variant.intelligence_enabled,
            adaptive_algorithm=variant.adaptive_algorithm,
            znn_gain=variant.znn_gain,
        ),
        llm=replace(
            base_config.llm,
            enabled=variant.llm_enabled,
            provider=variant.llm_provider,
        ),
        nodes=list(initialized.nodes.values()),
        network_edges=initialized.edges,
        initial_tasks=tasks,
        scenarios=scenario_cfg,
    )


def _generate_tasks(
    *,
    task_count: int,
    task_type: str,
    seed: int,
    horizon: int,
) -> list[Task]:
    """Generate synthetic workload with light/heavy/mixed task profiles."""
    rng = np.random.default_rng(int(seed))
    task_type = str(task_type).strip().lower()
    tasks: list[Task] = []

    for idx in range(task_count):
        if task_type == "light":
            cpu = float(rng.uniform(0.5, 2.5))
            mem = float(rng.uniform(1.0, 4.0))
            duration = int(rng.integers(1, 3))
            data_size = float(rng.uniform(32.0, 192.0))
            slack = int(rng.integers(2, 6))
        elif task_type == "heavy":
            cpu = float(rng.uniform(5.0, 12.0))
            mem = float(rng.uniform(8.0, 24.0))
            duration = int(rng.integers(3, 8))
            data_size = float(rng.uniform(256.0, 1536.0))
            slack = int(rng.integers(4, 10))
        else:
            heavy = bool(rng.random() < 0.35)
            if heavy:
                cpu = float(rng.uniform(4.0, 10.0))
                mem = float(rng.uniform(7.0, 20.0))
                duration = int(rng.integers(3, 7))
                data_size = float(rng.uniform(192.0, 1024.0))
                slack = int(rng.integers(3, 9))
            else:
                cpu = float(rng.uniform(0.8, 3.0))
                mem = float(rng.uniform(1.5, 6.0))
                duration = int(rng.integers(1, 4))
                data_size = float(rng.uniform(48.0, 320.0))
                slack = int(rng.integers(2, 7))

        arrival = int(rng.integers(0, max(1, horizon // 3)))
        deadline = float(arrival + duration + slack)
        tasks.append(
            Task(
                id=f"task-{idx + 1}",
                cpu_required=cpu,
                memory_required=mem,
                data_size=data_size,
                deadline=deadline,
                arrival_time=arrival,
                duration=duration,
            )
        )
    return tasks


def _build_scenario_config(
    *,
    scenario: str,
    node_count: int,
    task_count: int,
    horizon: int,
    failure_node_id: str,
) -> ScenarioConfig:
    """Build scenario config object for the requested study scenario."""
    load_rate = max(0.5, task_count / max(1.0, float(horizon)))
    dynamic = DynamicLoadConfig(
        enabled=scenario in {"dynamic-load", "peak-load", "node-failures", "heterogeneous-tasks"},
        base_rate=load_rate,
        amplitude=0.45,
        period=max(6, horizon // 8),
        max_new_tasks=max(4, int(node_count * 0.25)),
    )
    peak = PeakLoadConfig(
        enabled=scenario == "peak-load",
        start=max(2, horizon // 3),
        end=max(3, (2 * horizon) // 3),
        multiplier=2.8,
    )
    failures = NodeFailuresConfig(
        enabled=scenario == "node-failures",
        events=(
            [
                NodeFailureEventConfig(
                    node_id=failure_node_id,
                    time=max(2, horizon // 2),
                    duration=max(2, horizon // 10),
                )
            ]
            if scenario == "node-failures"
            else []
        ),
    )
    heterogeneous = HeterogeneousTasksConfig(enabled=scenario == "heterogeneous-tasks")
    return ScenarioConfig(
        dynamic_load=dynamic,
        peak_load=peak,
        node_failures=failures,
        heterogeneous_tasks=heterogeneous,
    )


def _suggest_horizon(node_count: int, task_count: int) -> int:
    """Estimate simulation horizon based on system scale."""
    estimate = int((task_count / max(1, node_count)) * 4) + 30
    return min(360, max(40, estimate))


def _derive_metrics(state) -> dict[str, float | int]:
    """Compute derived publication metrics from final simulation state."""
    latencies = [
        float(record["latency"])
        for record in state.completed_task_records
        if record.get("latency") is not None
    ]
    makespan = max(
        (
            int(record["finish_time"])
            for record in state.completed_task_records
            if record.get("finish_time") is not None
        ),
        default=state.current_time,
    )
    if state.node_loads:
        max_load = max(state.node_loads.values())
        min_load = min(state.node_loads.values())
    else:
        max_load = 0.0
        min_load = 0.0
    load_imbalance = float(max_load - min_load)
    adaptivity = _compute_adaptivity(state.history)
    stability_latency = _series_variance([float(item.get("avg_latency", 0.0)) for item in state.history])
    stability_throughput = _series_variance(
        [float(item.get("throughput", 0.0)) for item in state.history]
    )
    return {
        "completed_tasks": int(state.completed_tasks),
        "pending_tasks": int(state.pending_tasks),
        "makespan": float(makespan),
        "avg_latency": float(state.avg_latency),
        "latency_p95": float(np.percentile(latencies, 95)) if latencies else 0.0,
        "load_imbalance": load_imbalance,
        "sla_violations": int(state.deadline_violations),
        "throughput": float(state.throughput),
        "resource_utilization": float(state.avg_load),
        "adaptivity": float(adaptivity),
        "stability_latency_var": float(stability_latency),
        "stability_throughput_var": float(stability_throughput),
    }


def _compute_adaptivity(history: list[dict[str, object]]) -> float:
    """Estimate adaptivity as throughput delta over load delta."""
    if len(history) < 2:
        return 0.0
    loads = [float(item.get("avg_load", 0.0)) for item in history]
    perf = [float(item.get("throughput", 0.0)) for item in history]
    delta_load = max(loads) - min(loads)
    delta_perf = max(perf) - min(perf)
    if delta_load <= 1e-9:
        return 0.0
    return delta_perf / delta_load


def _series_variance(values: list[float]) -> float:
    """Return variance of a numeric series with small-sample handling."""
    if len(values) < 2:
        return 0.0
    return float(np.var(np.asarray(values, dtype=float)))


def _summarize_runs(raw_runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw run rows into mean/std/CI95 summary table."""
    if raw_runs.empty:
        return pd.DataFrame()

    metrics = [
        "makespan",
        "avg_latency",
        "latency_p95",
        "load_imbalance",
        "sla_violations",
        "throughput",
        "resource_utilization",
        "adaptivity",
        "stability_latency_var",
        "stability_throughput_var",
    ]
    grouped = raw_runs.groupby(
        ["study_id", "scenario", "method", "method_label", "method_family", "node_count", "task_count"],
        as_index=False,
    )

    rows: list[dict[str, Any]] = []
    for keys, chunk in grouped:
        (
            study_id,
            scenario,
            method,
            method_label,
            method_family,
            node_count,
            task_count,
        ) = keys
        row: dict[str, Any] = {
            "study_id": study_id,
            "scenario": scenario,
            "method": method,
            "method_label": method_label,
            "method_family": method_family,
            "node_count": int(node_count),
            "task_count": int(task_count),
            "n_runs": int(len(chunk)),
        }
        for metric in metrics:
            values = chunk[metric].astype(float).to_numpy()
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            ci = 1.96 * std / math.sqrt(len(values)) if len(values) > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci
            row[f"{metric}_ci95_low"] = mean - ci
            row[f"{metric}_ci95_high"] = mean + ci
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["study_id", "scenario", "node_count", "task_count", "method"]
    ).reset_index(drop=True)


def _evaluate_hypotheses(raw_runs: pd.DataFrame) -> pd.DataFrame:
    """Evaluate H1-H5 deltas from raw publication runs."""
    if raw_runs.empty:
        return pd.DataFrame()

    baseline = raw_runs[raw_runs["method"].isin(["round-robin", "min-load", "greedy"])]
    adaptive = raw_runs[raw_runs["method"].isin(["mas-hybrid", "mas-ml", "mas-znn", "mas-llm"])]
    mas = raw_runs[raw_runs["method"].isin(["mas-basic", "mas-hybrid", "mas-ml", "mas-znn", "mas-llm"])]

    rows: list[dict[str, Any]] = []

    h1_latency_delta = baseline["avg_latency"].mean() - adaptive["avg_latency"].mean()
    h1_imbalance_delta = baseline["load_imbalance"].mean() - adaptive["load_imbalance"].mean()
    rows.append(
        {
            "hypothesis": "H1",
            "title": "Adaptivity",
            "criterion": "Adaptive methods reduce latency and load imbalance.",
            "delta_latency": float(h1_latency_delta),
            "delta_load_imbalance": float(h1_imbalance_delta),
            "confirmed": bool(h1_latency_delta > 0 and h1_imbalance_delta > 0),
        }
    )

    robustness_baseline = baseline[baseline["scenario"] == "node-failures"]
    robustness_mas = mas[mas["scenario"] == "node-failures"]
    h2_throughput_delta = (
        robustness_mas["throughput"].mean() - robustness_baseline["throughput"].mean()
    )
    h2_stability_delta = (
        robustness_baseline["stability_latency_var"].mean()
        - robustness_mas["stability_latency_var"].mean()
    )
    rows.append(
        {
            "hypothesis": "H2",
            "title": "Multi-agent Architecture",
            "criterion": "MAS improves robustness and stability under failures.",
            "delta_throughput_failures": float(h2_throughput_delta),
            "delta_stability_failures": float(h2_stability_delta),
            "confirmed": bool(h2_throughput_delta > 0 and h2_stability_delta > 0),
        }
    )

    dynamic = raw_runs[
        (raw_runs["study_id"] == "E2_adaptivity")
        & (raw_runs["scenario"].isin(["dynamic-load", "peak-load"]))
    ]
    ml_znn = dynamic[dynamic["method"].isin(["mas-ml", "mas-znn"])]
    mas_basic = dynamic[dynamic["method"] == "mas-basic"]
    h3_latency_delta = mas_basic["avg_latency"].mean() - ml_znn["avg_latency"].mean()
    rows.append(
        {
            "hypothesis": "H3",
            "title": "Intelligent Methods (ML/ZNN)",
            "criterion": "ML/ZNN improve decisions under dynamic load.",
            "delta_latency_dynamic": float(h3_latency_delta),
            "confirmed": bool(h3_latency_delta > 0),
        }
    )

    e4_runs = raw_runs[raw_runs["study_id"] == "E4_hybrid_vs_classical"]
    e4_baseline = e4_runs[e4_runs["method"].isin(["round-robin", "min-load", "greedy"])]
    hybrid = e4_runs[e4_runs["method"] == "mas-hybrid"]
    key_cols = ["seed", "scenario", "node_count", "task_count"]
    best_baseline_latency = (
        e4_baseline.groupby(key_cols, as_index=False)["avg_latency"].min()
    )
    hybrid_latency = (
        hybrid.groupby(key_cols, as_index=False)["avg_latency"].mean()
    )
    merged_h4 = hybrid_latency.merge(
        best_baseline_latency,
        on=key_cols,
        suffixes=("_hybrid", "_baseline"),
    )
    h4_delta = (
        merged_h4["avg_latency_baseline"].mean() - merged_h4["avg_latency_hybrid"].mean()
        if not merged_h4.empty
        else 0.0
    )
    rows.append(
        {
            "hypothesis": "H4",
            "title": "Hybrid vs Single Methods",
            "criterion": "Hybrid method outperforms standalone baselines.",
            "delta_latency_hybrid_vs_best_baseline": float(h4_delta),
            "confirmed": bool(h4_delta > 0),
        }
    )

    e5_runs = raw_runs[raw_runs["study_id"] == "E5_llm_vs_algorithmic"]
    llm = e5_runs[e5_runs["method"] == "mas-llm"]
    algo = e5_runs[e5_runs["method"] == "mas-hybrid"]
    h5_adaptivity_delta = llm["adaptivity"].mean() - algo["adaptivity"].mean()
    h5_latency_delta = algo["avg_latency"].mean() - llm["avg_latency"].mean()
    rows.append(
        {
            "hypothesis": "H5",
            "title": "LLM Agent",
            "criterion": "LLM improves coordination and strategy flexibility.",
            "delta_adaptivity_llm_vs_algorithmic": float(h5_adaptivity_delta),
            "delta_latency_llm_vs_algorithmic": float(h5_latency_delta),
            "confirmed": bool(h5_adaptivity_delta > 0 or h5_latency_delta > 0),
        }
    )

    return pd.DataFrame(rows)


def _persist_publication_outputs(
    *,
    output_dir: Path,
    raw_runs: pd.DataFrame,
    summary: pd.DataFrame,
    hypotheses: pd.DataFrame,
    methods_df: pd.DataFrame,
    unsupported_df: pd.DataFrame,
    save_plots: bool,
) -> dict[str, str]:
    """Persist publication tables in CSV/JSON and optional plot artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, str] = {}

    paths = {
        "raw_runs_csv": output_dir / "raw_runs.csv",
        "summary_csv": output_dir / "summary.csv",
        "hypotheses_csv": output_dir / "hypotheses.csv",
        "methods_catalog_csv": output_dir / "methods_catalog.csv",
        "unsupported_methods_csv": output_dir / "unsupported_methods.csv",
        "raw_runs_json": output_dir / "raw_runs.json",
        "summary_json": output_dir / "summary.json",
        "hypotheses_json": output_dir / "hypotheses.json",
        "methods_catalog_json": output_dir / "methods_catalog.json",
    }
    raw_runs.to_csv(paths["raw_runs_csv"], index=False)
    summary.to_csv(paths["summary_csv"], index=False)
    hypotheses.to_csv(paths["hypotheses_csv"], index=False)
    methods_df.to_csv(paths["methods_catalog_csv"], index=False)
    unsupported_df.to_csv(paths["unsupported_methods_csv"], index=False)

    _write_json(paths["raw_runs_json"], _records(raw_runs))
    _write_json(paths["summary_json"], _records(summary))
    _write_json(paths["hypotheses_json"], _records(hypotheses))
    _write_json(paths["methods_catalog_json"], _records(methods_df))
    for key, path in paths.items():
        output_paths[key] = str(path)

    if save_plots and not raw_runs.empty:
        _save_publication_plots(output_dir=output_dir, raw_runs=raw_runs, summary=summary)
        for item in output_dir.glob("*.png"):
            output_paths[f"plot_{item.stem}_png"] = str(item)
        for item in output_dir.glob("*.pdf"):
            output_paths[f"plot_{item.stem}_pdf"] = str(item)
        for item in output_dir.glob("*.svg"):
            output_paths[f"plot_{item.stem}_svg"] = str(item)

    return output_paths


def _save_publication_plots(*, output_dir: Path, raw_runs: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Render publication plot set used in reports/manuscripts."""
    import matplotlib.pyplot as plt

    style = {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "grid.alpha": 0.35,
        "grid.linestyle": "--",
    }

    with plt.rc_context(style):
        _plot_scalability(summary=summary, output_dir=output_dir)
        _plot_boxplot(
            raw_runs=raw_runs[raw_runs["study_id"] == "E4_hybrid_vs_classical"],
            metric="avg_latency",
            title="E4 Hybrid vs Classical: Latency",
            output_stem=output_dir / "e4_hybrid_vs_classical_latency_boxplot",
        )
        _plot_boxplot(
            raw_runs=raw_runs[raw_runs["study_id"] == "E5_llm_vs_algorithmic"],
            metric="avg_latency",
            title="E5 LLM vs Algorithmic: Latency",
            output_stem=output_dir / "e5_llm_vs_algorithmic_latency_boxplot",
        )
        _plot_boxplot(
            raw_runs=raw_runs,
            metric="load_imbalance",
            title="Global Load Imbalance by Method",
            output_stem=output_dir / "global_load_imbalance_boxplot",
        )


def _plot_scalability(*, summary: pd.DataFrame, output_dir: Path) -> None:
    """Plot E1 scalability curve with confidence intervals."""
    import matplotlib.pyplot as plt

    subset = summary[summary["study_id"] == "E1_scalability"]
    if subset.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 6))
    for method, chunk in subset.groupby("method_label"):
        ordered = chunk.sort_values("node_count")
        ax.errorbar(
            ordered["node_count"].astype(int).tolist(),
            ordered["makespan_mean"].astype(float).tolist(),
            yerr=ordered["makespan_ci95"].astype(float).tolist(),
            marker="o",
            linewidth=2.0,
            capsize=4,
            label=method,
        )
    ax.set_xlabel("Number of Nodes")
    ax.set_ylabel("Makespan")
    ax.set_title("E1 Scalability: Makespan vs Node Count")
    ax.grid(True, axis="y")
    ax.legend(title="Method")
    fig.tight_layout()
    _save_figure(fig, output_dir / "e1_scalability_makespan")


def _plot_boxplot(
    *,
    raw_runs: pd.DataFrame,
    metric: str,
    title: str,
    output_stem: Path,
) -> None:
    """Render metric distribution boxplot grouped by method label."""
    import matplotlib.pyplot as plt

    if raw_runs.empty or metric not in raw_runs.columns:
        return
    ordered_labels = (
        raw_runs.groupby("method_label", as_index=False)[metric]
        .mean()
        .sort_values(metric)["method_label"]
        .tolist()
    )
    data = [raw_runs[raw_runs["method_label"] == label][metric].astype(float).tolist() for label in ordered_labels]
    if not data:
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot(data, labels=ordered_labels, showmeans=True)
    ax.set_title(title)
    ax.set_xlabel("Method")
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.grid(True, axis="y")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    _save_figure(fig, output_stem)


def _save_figure(fig, output_stem: Path) -> None:
    """Save figure in PNG/PDF/SVG formats and close it."""
    for ext in ("png", "pdf", "svg"):
        fig.savefig(output_stem.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)


def _write_publication_report(
    *,
    output_dir: Path,
    summary: pd.DataFrame,
    hypotheses: pd.DataFrame,
    methods_df: pd.DataFrame,
    seed_count: int,
    quick_mode: bool,
) -> Path:
    """Write markdown report with setup, top results, and hypothesis table."""
    report_path = output_dir / "publication_report.md"
    lines: list[str] = []
    lines.append("# Experimental Study Report")
    lines.append("")
    lines.append("## 1. Experimental Setup")
    lines.append(f"- Seed count: {seed_count}")
    lines.append(f"- Quick mode: {quick_mode}")
    lines.append("- Pipeline: init_system -> generate_tasks -> run_algorithm -> simulate -> collect_metrics -> repeat(seeds)")
    lines.append("")
    lines.append("## 2. Compared Methods")
    ready = methods_df[methods_df["ready"] == True]  # noqa: E712
    pending = methods_df[methods_df["ready"] == False]  # noqa: E712
    lines.append(f"- Ready methods: {len(ready)}")
    lines.append(f"- Placeholder methods: {len(pending)}")
    lines.append("")
    lines.append("## 3. Metrics")
    lines.append("- Primary: makespan, avg latency, load imbalance")
    lines.append("- Secondary: SLA violations, throughput, resource utilization")
    lines.append("- Advanced: adaptivity, stability variance")
    lines.append("")
    lines.append("## 4. Results")
    if summary.empty:
        lines.append("- No results.")
    else:
        top_rows = summary.sort_values("avg_latency_mean").head(10)
        lines.append(_render_table(top_rows))
    lines.append("")
    lines.append("## 5. Hypotheses")
    if hypotheses.empty:
        lines.append("- No hypothesis evaluation.")
    else:
        lines.append(_render_table(hypotheses))
    lines.append("")
    lines.append("## 6. Threats to Validity")
    lines.append("- External validity: synthetic workload generator may differ from production traces.")
    lines.append("- Internal validity: some method families are placeholders and not yet implemented.")
    lines.append("- Construct validity: adaptivity metric uses throughput/load deltas in current implementation.")
    lines.append("- Reproducibility: fixed seeds and run manifests are exported per experiment.")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-serializable record list."""
    if df.empty:
        return []
    safe_df = df.where(pd.notna(df), None)
    return json.loads(safe_df.to_json(orient="records"))


def _render_table(df: pd.DataFrame) -> str:
    """Render DataFrame as markdown table with plain-text fallback."""
    try:
        return df.to_markdown(index=False)
    except (ImportError, ModuleNotFoundError):
        return df.to_string(index=False)


def _write_json(path: Path, payload: Any) -> None:
    """Write payload as deterministic pretty JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
