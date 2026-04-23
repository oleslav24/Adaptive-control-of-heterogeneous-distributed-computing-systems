from __future__ import annotations

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
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    artifact_paths: dict[str, str] = {}
    history_df = _build_history_dataframe(state)
    tasks_df = pd.DataFrame(state.completed_task_records)
    events_df = pd.DataFrame(state.scenario_events)
    summary_df = pd.DataFrame([summarize_state(state)])

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

    if save_plots and not history_df.empty:
        metrics_plot_path = out / "metrics_timeseries.png"
        loads_plot_path = out / "node_loads.png"
        _plot_metrics_timeseries(history_df, metrics_plot_path)
        _plot_node_loads(history_df, loads_plot_path)
        artifact_paths["metrics_plot"] = str(metrics_plot_path)
        artifact_paths["loads_plot"] = str(loads_plot_path)
        LOGGER.info("Plots saved to %s", out)

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


def _plot_metrics_timeseries(df: pd.DataFrame, output_path: Path) -> None:
    time = df["time"] if "time" in df else range(len(df))
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(time, _series_or_default(df, "avg_latency"), color="#1f77b4")
    axes[0].set_ylabel("Latency")
    axes[0].set_title("Average Task Latency")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(time, _series_or_default(df, "throughput"), color="#2ca02c")
    axes[1].set_ylabel("Throughput")
    axes[1].set_title("System Throughput")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(time, _series_or_default(df, "avg_load"), color="#d62728")
    axes[2].set_ylabel("Load")
    axes[2].set_xlabel("Time")
    axes[2].set_title("Average Node Load")
    axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_node_loads(df: pd.DataFrame, output_path: Path) -> None:
    load_columns = [col for col in df.columns if col.startswith("load_")]
    if not load_columns:
        return
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
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _series_or_default(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df:
        return df[column]
    return pd.Series([0.0] * len(df))
