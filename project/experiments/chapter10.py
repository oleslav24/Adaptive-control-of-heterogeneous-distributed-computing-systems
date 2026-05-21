"""Chapter 10 experiment pipeline wrapper around publication study outputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
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
from project.evidence_claims import (
    build_report_claims,
    render_markdown_claims,
    write_claims_report,
)
from project.literature_evidence import build_report_evidence, render_markdown_evidence


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
    chapter10_lit_gate = chapter10_dir / "chapter10_literature_evidence_gate.json"
    if chapter10_lit_gate.exists():
        output_paths["chapter10_literature_evidence_gate_json"] = str(chapter10_lit_gate)
    chapter10_claims = chapter10_dir / "claims_report.json"
    if chapter10_claims.exists():
        output_paths["chapter10_claims_report_json"] = str(chapter10_claims)
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
    lines.append("## Related Literature Evidence (Local RAG)")
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
    lines.append("## Evidence-backed Claims")
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
    lines.append("## Notes")
    lines.append("- Tables and plots in this folder are normalized for Chapter 10 text.")
    path.write_text("\n".join(lines), encoding="utf-8")
    (output_dir / "chapter10_literature_evidence_gate.json").write_text(
        json.dumps(gate_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_claims_report(
        output_dir / "claims_report.json",
        claims=claims,
        gate=claims_gate,
        context={"report": "chapter10", "seed_count": len(seeds), "quick": quick},
    )
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
