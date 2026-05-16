"""Tabular artifacts for Chapter 10 experimental report outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def build_chapter10_tables(
    *,
    summary_df: pd.DataFrame,
    raw_runs_df: pd.DataFrame,
    hypotheses_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build normalized Chapter 10 tables from publication pipeline outputs."""
    return {
        "method_ranking": build_method_ranking_table(summary_df),
        "scenario_overview": build_scenario_overview_table(raw_runs_df),
        "hypotheses": build_hypotheses_table(hypotheses_df),
    }


def build_method_ranking_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate method-level ranking metrics for chapter narrative."""
    if summary_df.empty:
        return pd.DataFrame()
    required = {"method", "avg_latency_mean", "throughput_mean", "load_imbalance_mean"}
    if not required.issubset(set(summary_df.columns)):
        return pd.DataFrame()

    grouped = (
        summary_df.groupby("method", as_index=False)
        .agg(
            avg_latency_mean=("avg_latency_mean", "mean"),
            throughput_mean=("throughput_mean", "mean"),
            load_imbalance_mean=("load_imbalance_mean", "mean"),
            n_rows=("method", "count"),
        )
        .sort_values(["avg_latency_mean", "load_imbalance_mean", "throughput_mean"])
        .reset_index(drop=True)
    )
    grouped.insert(0, "rank", list(range(1, len(grouped) + 1)))
    return grouped


def build_scenario_overview_table(raw_runs_df: pd.DataFrame) -> pd.DataFrame:
    """Build scenario-level aggregate table with latency/throughput/SLA stats."""
    if raw_runs_df.empty:
        return pd.DataFrame()
    required = {"scenario", "avg_latency", "throughput", "sla_violations", "load_imbalance"}
    if not required.issubset(set(raw_runs_df.columns)):
        return pd.DataFrame()

    table = (
        raw_runs_df.groupby("scenario", as_index=False)
        .agg(
            runs=("scenario", "count"),
            avg_latency_mean=("avg_latency", "mean"),
            throughput_mean=("throughput", "mean"),
            sla_violations_mean=("sla_violations", "mean"),
            load_imbalance_mean=("load_imbalance", "mean"),
        )
        .sort_values("scenario")
        .reset_index(drop=True)
    )
    return table


def build_hypotheses_table(hypotheses_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize hypotheses table and keep deterministic ordering H1..H5."""
    if hypotheses_df.empty:
        return pd.DataFrame()
    table = hypotheses_df.copy()
    if "hypothesis" in table.columns:
        table = table.sort_values("hypothesis").reset_index(drop=True)
    return table


def persist_chapter10_tables(
    *,
    output_dir: Path,
    tables: dict[str, pd.DataFrame],
) -> dict[str, str]:
    """Persist chapter tables as CSV/JSON and return output path mapping."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, str] = {}
    for key, table in tables.items():
        csv_path = output_dir / f"{key}.csv"
        json_path = output_dir / f"{key}.json"
        table.to_csv(csv_path, index=False)
        _write_json(json_path, _records(table))
        output_paths[f"{key}_csv"] = str(csv_path)
        output_paths[f"{key}_json"] = str(json_path)
    return output_paths


def _write_json(path: Path, payload: Any) -> None:
    """Write deterministic JSON payload."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame into JSON-safe records."""
    if df.empty:
        return []
    safe = df.where(pd.notna(df), None)
    return json.loads(safe.to_json(orient="records"))
