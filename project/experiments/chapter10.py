"""Chapter 10 experiment pipeline wrapper around publication study outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from project.core.config import ExperimentConfig
from project.experiments.chapter10_plots import persist_chapter10_plots
from project.experiments.chapter10_tables import (
    build_carbon_tradeoff_table,
    build_chapter10_tables,
    persist_chapter10_tables,
)
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.publication import run_publication_pipeline


@dataclass(slots=True)
class Chapter10Result:
    """Result object for chapter10 pipeline execution."""

    output_dir: Path
    summary: pd.DataFrame
    hypotheses: pd.DataFrame
    output_paths: dict[str, str]


def run_chapter10_experiment(
    base_config: ExperimentConfig,
    *,
    seeds: list[int] | None = None,
    quick: bool | None = None,
    save_plots: bool | None = None,
    cli_args: list[str] | None = None,
) -> Chapter10Result:
    """Execute Chapter 10 experimental report pipeline and persist artifacts."""
    cli_args = list(cli_args or [])
    effective_seeds = _resolve_seeds(seeds, base_config.chapter10.seeds)
    effective_quick = bool(base_config.chapter10.quick if quick is None else quick)
    effective_plots = bool(
        (base_config.chapter10.save_plots if save_plots is None else save_plots)
        and base_config.observability.save_plots
    )

    publication_result = run_publication_pipeline(
        base_config=base_config,
        seeds=effective_seeds,
        quick=effective_quick,
        save_plots=effective_plots,
        cli_args=cli_args,
    )
    chapter10_dir = Path(base_config.observability.output_dir) / base_config.name / "chapter10"
    chapter10_dir.mkdir(parents=True, exist_ok=True)

    tables = build_chapter10_tables(
        summary_df=publication_result.summary,
        raw_runs_df=publication_result.raw_runs,
        hypotheses_df=publication_result.hypothesis_df,
    )
    table_paths = persist_chapter10_tables(output_dir=chapter10_dir, tables=tables)
    plot_paths = (
        persist_chapter10_plots(
            summary_df=publication_result.summary,
            raw_runs_df=publication_result.raw_runs,
            output_dir=chapter10_dir,
            dpi=base_config.observability.plot_dpi,
            formats=tuple(base_config.observability.plot_formats),
        )
        if effective_plots
        else {}
    )
    report_path = _write_chapter10_report(
        output_dir=chapter10_dir,
        summary=publication_result.summary,
        hypotheses=publication_result.hypothesis_df,
        seeds=effective_seeds,
        quick=effective_quick,
    )

    output_paths: dict[str, str] = {}
    output_paths.update(table_paths)
    output_paths.update(plot_paths)
    output_paths["chapter10_report_md"] = str(report_path)
    for key, path in publication_result.output_paths.items():
        output_paths[f"publication_{key}"] = str(path)

    manifest_path = chapter10_dir / "chapter10_manifest.json"
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=base_config,
            mode="chapter10-study",
            cli_args=cli_args,
            extra={
                "seeds": effective_seeds,
                "seed_count": len(effective_seeds),
                "quick": effective_quick,
                "save_plots": effective_plots,
                "publication_output_dir": str(publication_result.output_dir),
                "chapter10_output_dir": str(chapter10_dir),
                "output_files": output_paths,
            },
        ),
    )
    output_paths["chapter10_manifest_json"] = str(manifest_path)
    output_paths["chapter10_artifact_integrity_json"] = write_artifact_integrity_file(
        chapter10_dir / "chapter10_artifact_integrity.json",
        output_paths,
    )

    return Chapter10Result(
        output_dir=chapter10_dir,
        summary=publication_result.summary,
        hypotheses=publication_result.hypothesis_df,
        output_paths=output_paths,
    )


def _write_chapter10_report(
    *,
    output_dir: Path,
    summary: pd.DataFrame,
    hypotheses: pd.DataFrame,
    seeds: list[int],
    quick: bool,
) -> Path:
    """Persist compact Chapter 10 markdown report from generated artifacts."""
    path = output_dir / "chapter10_report.md"
    lines: list[str] = []
    lines.append("# Chapter 10 Experimental Package")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Seeds: {len(seeds)} ({min(seeds)}..{max(seeds)})")
    lines.append(f"- Quick mode: {quick}")
    lines.append("- Source pipeline: `project.experiments.publication.run_publication_pipeline`")
    lines.append("")
    lines.append("## Summary")
    if summary.empty:
        lines.append("- No summary rows.")
    else:
        top = summary.sort_values("avg_latency_mean").head(12)
        lines.append(_render_markdown_table(top))
    lines.append("")
    lines.append("## Carbon Interpretation")
    carbon = build_carbon_tradeoff_table(summary)
    if carbon.empty:
        lines.append("- Carbon trade-off rows are unavailable for this run.")
    else:
        top_carbon = carbon.head(8)
        lines.append(_render_markdown_table(top_carbon))
    lines.append("")
    lines.append("## Hypotheses")
    if hypotheses.empty:
        lines.append("- No hypothesis rows.")
    else:
        lines.append(_render_markdown_table(hypotheses))
    lines.append("")
    lines.append("## Notes")
    lines.append("- Tables and plots in this folder are normalized for Chapter 10 text.")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _render_markdown_table(df: pd.DataFrame) -> str:
    """Render DataFrame as markdown table with fallback string rendering."""
    try:
        return df.to_markdown(index=False)
    except (ImportError, ModuleNotFoundError):
        return df.to_string(index=False)


def _resolve_seeds(requested: list[int] | None, fallback: list[int]) -> list[int]:
    """Resolve deterministic seed list from request + config fallback."""
    raw = requested if requested is not None else fallback
    normalized: list[int] = []
    for item in list(raw):
        value = int(item)
        if value not in normalized:
            normalized.append(value)
    return normalized or [42]
