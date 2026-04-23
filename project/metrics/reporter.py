from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

import pandas as pd

_MPL_DIR = Path(tempfile.gettempdir()) / f"mplconfig-{os.getpid()}"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from project.core.models import SystemState

LOGGER = logging.getLogger(__name__)


def summarize_state(state: SystemState) -> dict[str, float | int | str]:
    return {
        "scenario": state.scenario,
        "algorithm": state.selected_algorithm,
        "intelligence_enabled": state.intelligence_enabled,
        "llm_enabled": state.llm_enabled,
        "llm_source": state.llm_source,
        "llm_confidence": state.llm_confidence,
        "llm_algorithm_hint": state.llm_algorithm_hint or "",
        "llm_actions_applied": state.llm_actions_applied,
        "predicted_queue": state.predicted_queue,
        "predicted_avg_load": state.predicted_avg_load,
        "time": state.current_time,
        "completed_tasks": state.completed_tasks,
        "pending_tasks": state.pending_tasks,
        "generated_tasks": state.generated_tasks,
        "inactive_nodes": len(state.inactive_nodes),
        "deadline_violations": state.deadline_violations,
        "avg_latency": state.avg_latency,
        "throughput": state.throughput,
        "avg_load": state.avg_load,
        "mas_messages": state.mas_messages,
        "mas_assignments": state.mas_assignments,
    }


def persist_observability(
    state: SystemState,
    output_dir: str | Path,
    save_csv: bool = True,
    save_plots: bool = True,
    save_json: bool = True,
    plot_profile: str = "publication",
    plot_dpi: int = 300,
    plot_formats: list[str] | None = None,
    run_manifest: dict[str, Any] | None = None,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    artifact_paths: dict[str, str] = {}
    history_df = _build_history_dataframe(state)
    tasks_df = pd.DataFrame(state.completed_task_records)
    events_df = pd.DataFrame(state.scenario_events)
    summary_row = summarize_state(state)
    summary_df = pd.DataFrame([summary_row])

    if save_csv:
        history_path = out / "history.csv"
        tasks_path = out / "completed_tasks.csv"
        events_path = out / "scenario_events.csv"
        summary_path = out / "summary.csv"
        history_df.to_csv(history_path, index=False)
        tasks_df.to_csv(tasks_path, index=False)
        events_df.to_csv(events_path, index=False)
        summary_df.to_csv(summary_path, index=False)
        artifact_paths["history_csv"] = str(history_path)
        artifact_paths["tasks_csv"] = str(tasks_path)
        artifact_paths["events_csv"] = str(events_path)
        artifact_paths["summary_csv"] = str(summary_path)
        LOGGER.info("CSV metrics saved to %s", out)

    if save_json:
        summary_json = out / "summary.json"
        history_json = out / "history.json"
        tasks_json = out / "completed_tasks.json"
        events_json = out / "scenario_events.json"
        _write_json(summary_json, summary_row)
        _write_json(history_json, _dataframe_to_records(history_df))
        _write_json(tasks_json, _dataframe_to_records(tasks_df))
        _write_json(events_json, _dataframe_to_records(events_df))
        artifact_paths["summary_json"] = str(summary_json)
        artifact_paths["history_json"] = str(history_json)
        artifact_paths["tasks_json"] = str(tasks_json)
        artifact_paths["events_json"] = str(events_json)
        if run_manifest is not None:
            manifest_path = out / "run_manifest.json"
            _write_json(manifest_path, run_manifest)
            artifact_paths["run_manifest_json"] = str(manifest_path)
        LOGGER.info("JSON metrics saved to %s", out)

    if save_plots and not history_df.empty:
        formats = _normalize_plot_formats(plot_formats)
        style_params = _plot_style_params(plot_profile)
        with plt.rc_context(style_params):
            metrics_fig = _build_metrics_timeseries_figure(history_df)
            metric_plot_paths = _save_figure_formats(
                fig=metrics_fig,
                output_stem=out / "metrics_timeseries",
                formats=formats,
                dpi=plot_dpi,
            )
            loads_fig = _build_node_loads_figure(history_df)
            loads_plot_paths: dict[str, str] = {}
            if loads_fig is not None:
                loads_plot_paths = _save_figure_formats(
                    fig=loads_fig,
                    output_stem=out / "node_loads",
                    formats=formats,
                    dpi=plot_dpi,
                )

        artifact_paths.update({f"metrics_plot_{fmt}": path for fmt, path in metric_plot_paths.items()})
        artifact_paths.update({f"loads_plot_{fmt}": path for fmt, path in loads_plot_paths.items()})
        if "png" in metric_plot_paths:
            artifact_paths["metrics_plot"] = metric_plot_paths["png"]
        if "png" in loads_plot_paths:
            artifact_paths["loads_plot"] = loads_plot_paths["png"]
        LOGGER.info("Plots saved to %s", out)

    return artifact_paths


def persist_batch_observability(
    runs_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    winners_df: pd.DataFrame,
    output_dir: str | Path,
    save_csv: bool = True,
    save_plots: bool = True,
    save_json: bool = True,
    plot_profile: str = "publication",
    plot_dpi: int = 300,
    plot_formats: list[str] | None = None,
    batch_manifest: dict[str, Any] | None = None,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    artifact_paths: dict[str, str] = {}

    if save_csv:
        runs_csv = out / "batch_runs.csv"
        summary_csv = out / "batch_summary.csv"
        ranking_csv = out / "batch_ranking.csv"
        winners_csv = out / "batch_winners.csv"
        runs_df.to_csv(runs_csv, index=False)
        summary_df.to_csv(summary_csv, index=False)
        ranking_df.to_csv(ranking_csv, index=False)
        winners_df.to_csv(winners_csv, index=False)
        artifact_paths["runs_csv"] = str(runs_csv)
        artifact_paths["summary_csv"] = str(summary_csv)
        artifact_paths["ranking_csv"] = str(ranking_csv)
        artifact_paths["winners_csv"] = str(winners_csv)
        LOGGER.info("Batch CSV metrics saved to %s", out)

    if save_json:
        runs_json = out / "batch_runs.json"
        summary_json = out / "batch_summary.json"
        ranking_json = out / "batch_ranking.json"
        winners_json = out / "batch_winners.json"
        _write_json(runs_json, _dataframe_to_records(runs_df))
        _write_json(summary_json, _dataframe_to_records(summary_df))
        _write_json(ranking_json, _dataframe_to_records(ranking_df))
        _write_json(winners_json, _dataframe_to_records(winners_df))
        artifact_paths["runs_json"] = str(runs_json)
        artifact_paths["summary_json"] = str(summary_json)
        artifact_paths["ranking_json"] = str(ranking_json)
        artifact_paths["winners_json"] = str(winners_json)
        if batch_manifest is not None:
            manifest_json = out / "batch_manifest.json"
            _write_json(manifest_json, batch_manifest)
            artifact_paths["batch_manifest_json"] = str(manifest_json)
        LOGGER.info("Batch JSON metrics saved to %s", out)

    if save_plots and not summary_df.empty:
        formats = _normalize_plot_formats(plot_formats)
        style_params = _plot_style_params(plot_profile)
        with plt.rc_context(style_params):
            latency_fig = _build_batch_metric_figure(
                summary_df=summary_df,
                metric_mean="avg_latency_mean",
                metric_std="avg_latency_std",
                title="Batch Comparison: Latency",
                ylabel="Latency (lower is better)",
            )
            throughput_fig = _build_batch_metric_figure(
                summary_df=summary_df,
                metric_mean="throughput_mean",
                metric_std="throughput_std",
                title="Batch Comparison: Throughput",
                ylabel="Throughput (higher is better)",
            )
            load_fig = _build_batch_metric_figure(
                summary_df=summary_df,
                metric_mean="avg_load_mean",
                metric_std="avg_load_std",
                title="Batch Comparison: Average Load",
                ylabel="Load",
            )

            latency_paths = _save_figure_formats(
                fig=latency_fig,
                output_stem=out / "batch_metric_latency",
                formats=formats,
                dpi=plot_dpi,
            )
            throughput_paths = _save_figure_formats(
                fig=throughput_fig,
                output_stem=out / "batch_metric_throughput",
                formats=formats,
                dpi=plot_dpi,
            )
            load_paths = _save_figure_formats(
                fig=load_fig,
                output_stem=out / "batch_metric_load",
                formats=formats,
                dpi=plot_dpi,
            )

        artifact_paths.update(
            {f"batch_latency_plot_{fmt}": path for fmt, path in latency_paths.items()}
        )
        artifact_paths.update(
            {f"batch_throughput_plot_{fmt}": path for fmt, path in throughput_paths.items()}
        )
        artifact_paths.update(
            {f"batch_load_plot_{fmt}": path for fmt, path in load_paths.items()}
        )
        LOGGER.info("Batch plots saved to %s", out)

    return artifact_paths


def _build_history_dataframe(state: SystemState) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for entry in state.history:
        row = {k: v for k, v in entry.items() if k != "node_loads"}
        node_loads = entry.get("node_loads", {})
        if isinstance(node_loads, dict):
            for node_id, load in node_loads.items():
                row[f"load_{node_id}"] = load
        rows.append(row)
    return pd.DataFrame(rows)


def _build_metrics_timeseries_figure(df: pd.DataFrame):
    time = df["time"] if "time" in df else range(len(df))
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(time, _series_or_default(df, "avg_latency"), color="#1f77b4")
    axes[0].set_ylabel("Latency")
    axes[0].set_title("Average Task Latency")

    axes[1].plot(time, _series_or_default(df, "throughput"), color="#2ca02c")
    axes[1].set_ylabel("Throughput")
    axes[1].set_title("System Throughput")

    axes[2].plot(time, _series_or_default(df, "avg_load"), color="#d62728")
    axes[2].set_ylabel("Load")
    axes[2].set_xlabel("Time")
    axes[2].set_title("Average Node Load")

    for ax in axes:
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _build_node_loads_figure(df: pd.DataFrame):
    load_columns = [col for col in df.columns if col.startswith("load_")]
    if not load_columns:
        return None
    time = df["time"] if "time" in df else range(len(df))
    fig, ax = plt.subplots(figsize=(12, 5))
    for col in sorted(load_columns):
        label = col.replace("load_", "")
        ax.plot(time, df[col], label=label)

    ax.set_xlabel("Time")
    ax.set_ylabel("Load")
    ax.set_title("Node Load Timeline")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def _build_batch_metric_figure(
    summary_df: pd.DataFrame,
    metric_mean: str,
    metric_std: str,
    title: str,
    ylabel: str,
):
    ordered = summary_df.sort_values(["scenario", "algorithm"])
    scenarios = sorted(ordered["scenario"].astype(str).unique().tolist())
    algorithms = sorted(ordered["algorithm"].astype(str).unique().tolist())

    fig, ax = plt.subplots(figsize=(12, 6))
    for algorithm in algorithms:
        subset = ordered[ordered["algorithm"] == algorithm].set_index("scenario")
        values = [float(subset.loc[scenario, metric_mean]) for scenario in scenarios]
        if metric_std in subset.columns:
            errors = [float(subset.loc[scenario, metric_std]) for scenario in scenarios]
        else:
            errors = [0.0] * len(scenarios)
        ax.errorbar(
            scenarios,
            values,
            yerr=errors,
            marker="o",
            linewidth=2.0,
            capsize=4,
            label=algorithm,
        )

    ax.set_title(title)
    ax.set_xlabel("Scenario")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(title="Algorithm")
    fig.tight_layout()
    return fig


def _save_figure_formats(
    fig,
    output_stem: Path,
    formats: list[str],
    dpi: int,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for fmt in formats:
        path = output_stem.with_suffix(f".{fmt}")
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
        paths[fmt] = str(path)
    plt.close(fig)
    return paths


def _normalize_plot_formats(formats: list[str] | None) -> list[str]:
    allowed = {"png", "pdf", "svg"}
    selected = formats or ["png"]
    normalized: list[str] = []
    for item in selected:
        name = str(item).strip().lower()
        if name in allowed and name not in normalized:
            normalized.append(name)
    return normalized or ["png"]


def _plot_style_params(profile: str) -> dict[str, object]:
    if str(profile).strip().lower() != "publication":
        return {}
    return {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.fontsize": 10,
        "legend.frameon": False,
        "lines.linewidth": 2.0,
        "grid.linestyle": "--",
        "grid.alpha": 0.35,
    }


def _series_or_default(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df:
        return df[column]
    return pd.Series([0.0] * len(df))


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    safe_df = df.where(pd.notna(df), None)
    return json.loads(safe_df.to_json(orient="records"))
