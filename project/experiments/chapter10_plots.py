"""Plot generation for Chapter 10 experiment narrative."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def persist_chapter10_plots(
    *,
    summary_df: pd.DataFrame,
    raw_runs_df: pd.DataFrame,
    output_dir: Path,
    dpi: int = 300,
    formats: tuple[str, ...] = ("png", "pdf", "svg"),
) -> dict[str, str]:
    """Render Chapter 10 plot set and return exported artifact paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, str] = {}
    if summary_df.empty and raw_runs_df.empty:
        return output_paths

    import matplotlib.pyplot as plt

    with plt.rc_context(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.alpha": 0.35,
            "grid.linestyle": "--",
            "legend.frameon": False,
        }
    ):
        output_paths.update(
            _plot_scalability_latency(
                summary_df=summary_df,
                output_stem=output_dir / "chapter10_scalability_latency",
                dpi=dpi,
                formats=formats,
            )
        )
        output_paths.update(
            _plot_scenario_throughput(
                raw_runs_df=raw_runs_df,
                output_stem=output_dir / "chapter10_scenario_throughput",
                dpi=dpi,
                formats=formats,
            )
        )
        output_paths.update(
            _plot_method_latency_boxplot(
                raw_runs_df=raw_runs_df,
                output_stem=output_dir / "chapter10_method_latency_boxplot",
                dpi=dpi,
                formats=formats,
            )
        )
    return output_paths


def _plot_scalability_latency(
    *,
    summary_df: pd.DataFrame,
    output_stem: Path,
    dpi: int,
    formats: tuple[str, ...],
) -> dict[str, str]:
    """Line plot: node count vs average latency per method."""
    required = {"node_count", "method", "avg_latency_mean"}
    if summary_df.empty or not required.issubset(set(summary_df.columns)):
        return {}
    subset = summary_df
    if "study_id" in subset.columns:
        e1 = subset[subset["study_id"] == "E1_scalability"]
        if not e1.empty:
            subset = e1

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6))
    for method, chunk in subset.groupby("method"):
        ordered = chunk.sort_values("node_count")
        ax.plot(
            ordered["node_count"].astype(int).tolist(),
            ordered["avg_latency_mean"].astype(float).tolist(),
            marker="o",
            linewidth=2.0,
            label=str(method),
        )
    ax.set_xlabel("Nodes")
    ax.set_ylabel("Average latency")
    ax.set_title("Chapter 10: Scalability latency profile")
    ax.grid(True, axis="y")
    ax.legend(title="Method")
    fig.tight_layout()
    paths = _save_figure(fig, output_stem, dpi=dpi, formats=formats)
    return {f"plot_scalability_latency_{ext}": path for ext, path in paths.items()}


def _plot_scenario_throughput(
    *,
    raw_runs_df: pd.DataFrame,
    output_stem: Path,
    dpi: int,
    formats: tuple[str, ...],
) -> dict[str, str]:
    """Bar plot: scenario throughput means."""
    required = {"scenario", "throughput"}
    if raw_runs_df.empty or not required.issubset(set(raw_runs_df.columns)):
        return {}

    grouped = (
        raw_runs_df.groupby("scenario", as_index=False)["throughput"]
        .mean()
        .sort_values("scenario")
        .reset_index(drop=True)
    )
    if grouped.empty:
        return {}

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(grouped["scenario"].tolist(), grouped["throughput"].astype(float).tolist())
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Throughput")
    ax.set_title("Chapter 10: Throughput by scenario")
    ax.grid(True, axis="y")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    paths = _save_figure(fig, output_stem, dpi=dpi, formats=formats)
    return {f"plot_scenario_throughput_{ext}": path for ext, path in paths.items()}


def _plot_method_latency_boxplot(
    *,
    raw_runs_df: pd.DataFrame,
    output_stem: Path,
    dpi: int,
    formats: tuple[str, ...],
) -> dict[str, str]:
    """Boxplot: latency distributions per method."""
    required = {"method", "avg_latency"}
    if raw_runs_df.empty or not required.issubset(set(raw_runs_df.columns)):
        return {}

    ordered_methods = (
        raw_runs_df.groupby("method", as_index=False)["avg_latency"]
        .mean()
        .sort_values("avg_latency")["method"]
        .tolist()
    )
    if not ordered_methods:
        return {}
    series = [
        raw_runs_df[raw_runs_df["method"] == method]["avg_latency"].astype(float).tolist()
        for method in ordered_methods
    ]

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot(series, labels=ordered_methods, showmeans=True)
    ax.set_xlabel("Method")
    ax.set_ylabel("Average latency")
    ax.set_title("Chapter 10: Latency distribution by method")
    ax.grid(True, axis="y")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    paths = _save_figure(fig, output_stem, dpi=dpi, formats=formats)
    return {f"plot_method_latency_boxplot_{ext}": path for ext, path in paths.items()}


def _save_figure(
    fig,
    output_stem: Path,
    *,
    dpi: int,
    formats: tuple[str, ...],
) -> dict[str, str]:
    """Save figure in selected formats and close figure handle."""
    output: dict[str, str] = {}
    for ext in formats:
        path = output_stem.with_suffix(f".{ext}")
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
        output[ext] = str(path)
    import matplotlib.pyplot as plt

    plt.close(fig)
    return output
