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
    ExperimentConfig,
)
from project.experiments.controller import Experiment
from project.experiments.integrity import write_artifact_integrity_file
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
from project.experiments.publication_scenarios import (
    build_scenario_config,
    generate_tasks,
    suggest_horizon,
)
from project.experiments.publication_validation import (
    validate_carbon_summary_table,
    validate_hypotheses_table,
    validate_summary_statistics,
)
from project.evidence_claims import (
    build_report_claims,
    render_markdown_claims,
    write_claims_report,
)
from project.literature_evidence import (
    build_report_evidence,
    render_markdown_evidence,
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
    mode: str = "publication-study",
    output_dir_name: str = "publication",
    include_study_ids: list[str] | None = None,
    ready_method_keys: list[str] | None = None,
    study_method_overrides: dict[str, list[str]] | None = None,
) -> StudyResult:
    """Run full publication pipeline and export tables, report, and plots."""
    cli_args = list(cli_args or [])
    seeds = sorted({int(seed) for seed in seeds})
    if not seeds:
        raise ValueError("At least one seed is required for publication study.")

    output_dir = Path(base_config.observability.output_dir) / base_config.name / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    methods_df = pd.DataFrame([method_to_row(m) for m in METHOD_CATALOG])
    catalog_ready_methods = [m.key for m in METHOD_CATALOG if m.ready]
    ready_methods = _select_ready_methods(
        catalog_ready_methods,
        ready_method_keys=ready_method_keys,
    )
    unsupported_df = methods_df[methods_df["ready"] == False].copy()  # noqa: E712

    experiment_specs = build_study_specs(
        seeds=seeds,
        ready_methods=ready_methods,
        quick=quick,
        method_overrides_by_study=study_method_overrides,
    )
    normalized_study_ids: list[str] = []
    if include_study_ids:
        for item in include_study_ids:
            value = str(item).strip()
            if value and value not in normalized_study_ids:
                normalized_study_ids.append(value)
    if normalized_study_ids:
        experiment_specs = [spec for spec in experiment_specs if spec.study_id in normalized_study_ids]
    if not experiment_specs:
        raise ValueError("No study specifications selected for publication pipeline run.")

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
    carbon_summary = _build_carbon_summary(summary)
    carbon_validation = validate_carbon_summary_table(carbon_summary)
    if not carbon_validation.ok:
        message = "; ".join(carbon_validation.errors[:8])
        raise ValueError(f"Publication carbon summary validation failed: {message}")

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
    carbon_validation_path = output_dir / "carbon_summary_validation.json"
    _write_json(
        carbon_validation_path,
        {
            "ok": carbon_validation.ok,
            "row_count": carbon_validation.row_count,
            "errors": carbon_validation.errors,
        },
    )
    output_paths["carbon_summary_validation_json"] = str(carbon_validation_path)

    manifest_path = output_dir / "publication_manifest.json"
    manifest = build_run_manifest(
        config=base_config,
        mode=mode,
        cli_args=cli_args,
        extra={
            "quick_mode": quick,
            "seed_count": len(seeds),
            "seeds": seeds,
            "study_ids_filter": normalized_study_ids,
            "study_specs": [asdict(spec) for spec in experiment_specs],
            "ready_methods": ready_methods,
            "ready_method_keys_filter": list(ready_method_keys or []),
            "study_method_overrides": study_method_overrides or {},
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
    literature_gate_path = output_dir / "literature_evidence_gate.json"
    if literature_gate_path.exists():
        output_paths["literature_evidence_gate_json"] = str(literature_gate_path)
    claims_report_path = output_dir / "claims_report.json"
    if claims_report_path.exists():
        output_paths["claims_report_json"] = str(claims_report_path)
    output_paths["artifact_integrity_json"] = write_artifact_integrity_file(
        output_dir / "artifact_integrity.json",
        output_paths,
    )

    return StudyResult(
        output_dir=output_dir,
        raw_runs=raw_runs,
        summary=summary,
        hypothesis_df=hypothesis_df,
        methods_df=methods_df,
        output_paths=output_paths,
    )


def _select_ready_methods(
    catalog_ready_methods: list[str],
    *,
    ready_method_keys: list[str] | None,
) -> list[str]:
    """Apply an optional method whitelist while preserving catalog order."""
    if ready_method_keys is None:
        return list(catalog_ready_methods)

    allowed: set[str] = set()
    for item in ready_method_keys:
        value = str(item).strip()
        if value:
            allowed.add(value)
    return [method for method in catalog_ready_methods if method in allowed]


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
    tasks = generate_tasks(
        task_count=spec.task_count,
        task_type=spec.task_type,
        seed=seed,
        horizon=suggest_horizon(spec.node_count, spec.task_count),
    )
    scenario_cfg = build_scenario_config(
        scenario=spec.scenario,
        node_count=spec.node_count,
        task_count=spec.task_count,
        horizon=suggest_horizon(spec.node_count, spec.task_count),
        failure_node_id=f"node-{max(1, spec.node_count // 2)}",
    )

    return replace(
        base_config,
        name=base_config.name,
        scenario=spec.scenario,
        simulation=replace(
            base_config.simulation,
            seed=seed,
            time_horizon=suggest_horizon(spec.node_count, spec.task_count),
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
        "energy_consumed_mwh": float(state.energy_consumed_mwh),
        "co2_total_lb": float(state.co2_total_lb),
        "co2e_total_lb": float(state.co2e_total_lb),
        "co2_per_completed_task_lb": float(state.co2_per_completed_task_lb),
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
        "energy_consumed_mwh",
        "co2_total_lb",
        "co2e_total_lb",
        "co2_per_completed_task_lb",
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
    carbon_summary = _build_carbon_summary(summary)

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
    if not carbon_summary.empty:
        paths["carbon_summary_csv"] = output_dir / "carbon_summary.csv"
        paths["carbon_summary_json"] = output_dir / "carbon_summary.json"
    raw_runs.to_csv(paths["raw_runs_csv"], index=False)
    summary.to_csv(paths["summary_csv"], index=False)
    hypotheses.to_csv(paths["hypotheses_csv"], index=False)
    methods_df.to_csv(paths["methods_catalog_csv"], index=False)
    unsupported_df.to_csv(paths["unsupported_methods_csv"], index=False)
    if not carbon_summary.empty:
        carbon_summary.to_csv(paths["carbon_summary_csv"], index=False)

    _write_json(paths["raw_runs_json"], _records(raw_runs))
    _write_json(paths["summary_json"], _records(summary))
    _write_json(paths["hypotheses_json"], _records(hypotheses))
    _write_json(paths["methods_catalog_json"], _records(methods_df))
    if not carbon_summary.empty:
        _write_json(paths["carbon_summary_json"], _records(carbon_summary))
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


def _build_carbon_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Build carbon-focused aggregate table with deltas vs min-load baseline."""
    required = {
        "method",
        "method_label",
        "avg_latency_mean",
        "throughput_mean",
        "co2_total_lb_mean",
        "co2_per_completed_task_lb_mean",
    }
    if summary.empty or not required.issubset(set(summary.columns)):
        return pd.DataFrame()

    subset = summary
    if "study_id" in summary.columns:
        e6 = summary[summary["study_id"] == "E6_carbon_vs_performance"]
        if not e6.empty:
            subset = e6
    if subset.empty:
        return pd.DataFrame()

    grouped = (
        subset.groupby(["method", "method_label"], as_index=False)
        .agg(
            n_groups=("method", "count"),
            avg_latency_mean=("avg_latency_mean", "mean"),
            throughput_mean=("throughput_mean", "mean"),
            co2_total_lb_mean=("co2_total_lb_mean", "mean"),
            co2_per_completed_task_lb_mean=("co2_per_completed_task_lb_mean", "mean"),
        )
        .sort_values(["co2_per_completed_task_lb_mean", "avg_latency_mean"])
        .reset_index(drop=True)
    )
    if grouped.empty:
        return grouped

    baseline_source = grouped[grouped["method"] == "min-load"]
    baseline = baseline_source.iloc[0] if not baseline_source.empty else grouped.iloc[0]
    baseline_latency = float(baseline["avg_latency_mean"])
    baseline_throughput = float(baseline["throughput_mean"])
    baseline_co2_total = float(baseline["co2_total_lb_mean"])
    baseline_co2_task = float(baseline["co2_per_completed_task_lb_mean"])

    grouped["delta_latency_vs_min_load"] = grouped["avg_latency_mean"].astype(float) - baseline_latency
    grouped["delta_throughput_vs_min_load"] = grouped["throughput_mean"].astype(float) - baseline_throughput
    grouped["delta_co2_total_vs_min_load_lb"] = (
        grouped["co2_total_lb_mean"].astype(float) - baseline_co2_total
    )
    grouped["delta_co2_per_task_vs_min_load_lb"] = (
        grouped["co2_per_completed_task_lb_mean"].astype(float) - baseline_co2_task
    )
    grouped["co2_total_reduction_vs_min_load_pct"] = grouped["delta_co2_total_vs_min_load_lb"].apply(
        lambda value: _negative_delta_to_reduction_pct(float(value), baseline_co2_total)
    )
    grouped["co2_per_task_reduction_vs_min_load_pct"] = grouped[
        "delta_co2_per_task_vs_min_load_lb"
    ].apply(lambda value: _negative_delta_to_reduction_pct(float(value), baseline_co2_task))
    grouped.insert(0, "rank_co2", list(range(1, len(grouped) + 1)))
    grouped["baseline_method"] = "min-load"
    return grouped


def _negative_delta_to_reduction_pct(delta: float, baseline: float) -> float:
    """Convert negative delta to positive reduction percentage."""
    if baseline <= 0.0:
        return 0.0
    return max(0.0, (-delta / baseline) * 100.0)


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
    lines.append("### Carbon-Performance Interpretation")
    carbon_summary = _build_carbon_summary(summary)
    if carbon_summary.empty:
        lines.append("- Carbon interpretation is unavailable for this run.")
    else:
        best = carbon_summary.iloc[0]
        baseline_candidates = carbon_summary[carbon_summary["method"] == "min-load"]
        baseline = baseline_candidates.iloc[0] if not baseline_candidates.empty else carbon_summary.iloc[-1]
        lines.append(
            f"- Best CO2 per task: `{best['method']}` ({float(best['co2_per_completed_task_lb_mean']):.3f} lb/task)."
        )
        lines.append(
            (
                "- Delta vs baseline `min-load`: "
                f"CO2/task {float(best['delta_co2_per_task_vs_min_load_lb']):+.3f} lb, "
                f"latency {float(best['delta_latency_vs_min_load']):+.3f}, "
                f"throughput {float(best['delta_throughput_vs_min_load']):+.3f}."
            )
        )
        lines.append(
            f"- Baseline reference (`{baseline['method']}`) CO2/task: "
            f"{float(baseline['co2_per_completed_task_lb_mean']):.3f} lb/task."
        )
    lines.append("")
    lines.append("### Related Literature Evidence (Local RAG)")
    literature = build_report_evidence(
        summary_df=summary,
        hypotheses_df=hypotheses,
        top_k=5,
        min_score=0.03,
        min_sources=2,
    )
    evidence_payload = literature["evidence"]
    gate_payload = literature["gate"]
    if not evidence_payload.get("available", False):
        lines.append(
            "- Local evidence is unavailable for this run "
            f"(`{str(evidence_payload.get('reason', 'unknown'))}`)."
        )
    else:
        lines.append(f"- Query: `{str(literature.get('query', '')).strip()}`")
        lines.extend(render_markdown_evidence(evidence_payload.get("items", []), limit=5))
    if gate_payload.get("skipped", False):
        lines.append(
            "- Evidence quality gate: skipped "
            f"(`{str(evidence_payload.get('reason', 'unknown'))}`)."
        )
    elif gate_payload.get("ok", False):
        lines.append(
            "- Evidence quality gate: pass "
            f"({int(gate_payload.get('source_count', 0))} sources)."
        )
    else:
        lines.append("- Evidence quality gate: fail.")
        for error in list(gate_payload.get("errors", []))[:3]:
            lines.append(f"  - {error}")
    claims_payload = build_report_claims(
        summary_df=summary,
        hypotheses_df=hypotheses,
        evidence_payload=evidence_payload,
        min_sources_per_claim=2,
        min_score=0.03,
    )
    claims = claims_payload["claims"]
    claims_gate = claims_payload["gate"]
    lines.append("")
    lines.append("### Evidence-backed Claims")
    lines.extend(render_markdown_claims(claims, limit=8))
    if claims_gate.get("ok", False):
        lines.append(
            "- Claims quality gate: pass "
            f"({int(claims_gate.get('claim_count', 0))} claims)."
        )
    else:
        lines.append("- Claims quality gate: fail.")
        for error in list(claims_gate.get("errors", []))[:3]:
            lines.append(f"  - {error}")
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
    _write_json(output_dir / "literature_evidence_gate.json", gate_payload)
    write_claims_report(
        output_dir / "claims_report.json",
        claims=claims,
        gate=claims_gate,
        context={"report": "publication", "seed_count": seed_count, "quick_mode": quick_mode},
    )
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
