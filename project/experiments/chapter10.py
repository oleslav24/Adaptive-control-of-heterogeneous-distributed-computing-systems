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
from project.experiments.control_health import (
    build_control_health_assessment,
    write_control_health_artifacts,
)
from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.manifest import build_run_manifest, write_manifest
from project.experiments.quality_gate import (
    QualityGateAssessment,
    build_quality_gate_assessment,
    check_claims_gate_artifact,
    check_file_exists,
    check_integrity_artifact,
    check_json_ok_artifact,
    check_manifest_artifact,
    render_quality_gate_failure,
    write_quality_gate_file,
)
from project.experiments.publication import (
    render_hypothesis_significance,
    render_hypothesis_support,
    run_publication_pipeline,
)
from project.evidence_claims import (
    build_report_claims,
    render_markdown_claims,
    write_claims_report,
)
from project.literature_evidence import build_report_evidence, render_markdown_evidence

REQUIRED_CHAPTER10_ARTIFACT_KEYS = (
    "method_ranking_csv",
    "method_ranking_json",
    "scenario_overview_csv",
    "scenario_overview_json",
    "carbon_tradeoff_csv",
    "carbon_tradeoff_json",
    "hypotheses_csv",
    "hypotheses_json",
    "chapter10_report_md",
    "chapter10_literature_evidence_gate_json",
    "chapter10_claims_report_json",
    "chapter10_control_health_json",
    "chapter10_control_health_md",
    "chapter10_manifest_json",
    "chapter10_artifact_integrity_json",
    "publication_publication_manifest_json",
    "publication_artifact_integrity_json",
)


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
        publication_output_dir=publication_result.output_dir,
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
    output_paths["chapter10_manifest_json"] = str(manifest_path)
    validation_path = chapter10_dir / "chapter10_package_validation.json"
    output_paths["chapter10_package_validation_json"] = str(validation_path)

    # Persist control-health appendix first so validation/integrity include these artifacts.
    output_paths.update(
        write_control_health_artifacts(
            chapter10_dir,
            build_control_health_assessment(output_paths, mode="chapter10-study"),
        )
    )
    integrity_path = chapter10_dir / "chapter10_artifact_integrity.json"
    output_paths["chapter10_artifact_integrity_json"] = str(integrity_path)
    package_validation = validate_chapter10_package(output_paths)
    _write_chapter10_package_validation(
        validation_path=validation_path,
        validation_payload=package_validation,
    )
    _write_chapter10_manifest(
        manifest_path=manifest_path,
        config=base_config,
        cli_args=cli_args,
        seeds=effective_seeds,
        quick=effective_quick,
        save_plots=effective_plots,
        publication_output_dir=publication_result.output_dir,
        chapter10_dir=chapter10_dir,
        output_paths=output_paths,
    )
    output_paths["chapter10_artifact_integrity_json"] = write_artifact_integrity_file(
        integrity_path,
        _integrity_inputs(output_paths),
    )
    package_validation = validate_chapter10_package(output_paths)
    _write_chapter10_package_validation(
        validation_path=validation_path,
        validation_payload=package_validation,
    )
    quality_gate_path = chapter10_dir / "quality_gate.json"
    output_paths["chapter10_quality_gate_json"] = str(quality_gate_path)
    _write_chapter10_manifest(
        manifest_path=manifest_path,
        config=base_config,
        cli_args=cli_args,
        seeds=effective_seeds,
        quick=effective_quick,
        save_plots=effective_plots,
        publication_output_dir=publication_result.output_dir,
        chapter10_dir=chapter10_dir,
        output_paths=output_paths,
    )
    output_paths["chapter10_artifact_integrity_json"] = write_artifact_integrity_file(
        integrity_path,
        _integrity_inputs(output_paths),
    )
    quality_gate = _build_chapter10_quality_gate(output_paths=output_paths)
    output_paths["chapter10_quality_gate_json"] = write_quality_gate_file(
        quality_gate_path,
        quality_gate,
    )
    if not quality_gate.ok:
        failure = render_quality_gate_failure(quality_gate)
        raise ValueError(f"Chapter10 quality gate failed: {failure}")

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
    publication_output_dir: Path,
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
        lines.append("### Hypothesis Support Status")
        lines.extend(render_hypothesis_support(hypotheses))
        lines.append("")
        lines.append("### Statistical Significance Snapshot")
        lines.extend(render_hypothesis_significance(hypotheses))
        lines.append("")
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
    lines.append("## Reproducibility Links")
    lines.append("- Run manifest: `chapter10_manifest.json`.")
    lines.append("- Artifact integrity: `chapter10_artifact_integrity.json`.")
    lines.append("- Package validation: `chapter10_package_validation.json`.")
    lines.append("- Unified quality gate: `quality_gate.json`.")
    lines.append("- Operational control-health appendix: `chapter10_control_health.{json,md}`.")
    lines.append(
        "- Source publication package: "
        f"`{_display_path(publication_output_dir)}`."
    )
    lines.append("- Source publication manifest: `../publication/publication_manifest.json`.")
    lines.append("- Monograph alignment matrix: `docs/monograph_alignment.md`.")
    lines.append("")
    lines.append("## Monograph Alignment")
    lines.append(
        _render_markdown_table(
            pd.DataFrame(
                [
                    {
                        "Monograph section": "Chapter 2-3",
                        "Code/artifact": "formal model, scenario overview",
                        "Usage": "system model, topology, workload parameters",
                    },
                    {
                        "Monograph section": "Chapter 4-5",
                        "Code/artifact": "method_ranking.csv/json",
                        "Usage": "MAS and algorithm comparison evidence",
                    },
                    {
                        "Monograph section": "Chapter 6",
                        "Code/artifact": "scenario_overview.csv/json",
                        "Usage": "metrics and observability evidence",
                    },
                    {
                        "Monograph section": "Chapter 7-8",
                        "Code/artifact": "hypotheses.csv/json, claims_report.json",
                        "Usage": "ML/ZNN and LLM hypothesis status",
                    },
                    {
                        "Monograph section": "Chapter 10",
                        "Code/artifact": "chapter10_manifest.json, integrity JSON",
                        "Usage": "reproducible experimental package",
                    },
                ]
            )
        )
    )
    lines.append("")
    lines.append("## Threats to Validity")
    lines.append("- External validity: synthetic workloads may not reproduce production traces.")
    lines.append("- Internal validity: quick mode uses a reduced seed set and should not be overclaimed.")
    lines.append("- Construct validity: H1-H5 are interpreted from current metric deltas only.")
    lines.append("- LLM validity: reproducible runs use mock LLM policy unless another provider is configured.")
    lines.append("- Carbon validity: carbon-aware E6 results are an extension and should be interpreted separately from H1-H5.")
    lines.append("- Method coverage validity: placeholder families (`transport`, `abc`) are treated as future work unless implemented.")
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


def validate_chapter10_package(output_paths: dict[str, str]) -> dict[str, Any]:
    """Validate that the Chapter 10 package exposes the expected core artifacts."""
    missing_keys: list[str] = []
    missing_files: list[str] = []
    for key in REQUIRED_CHAPTER10_ARTIFACT_KEYS:
        path = str(output_paths.get(key, "")).strip()
        if not path:
            missing_keys.append(key)
            continue
        if not Path(path).exists():
            missing_files.append(path)
    return {
        "ok": not missing_keys and not missing_files,
        "required_keys": list(REQUIRED_CHAPTER10_ARTIFACT_KEYS),
        "missing_keys": missing_keys,
        "missing_files": missing_files,
        "artifact_count": len(output_paths),
    }


def _display_path(path: Path) -> str:
    """Render a stable local path string for markdown reports."""
    return str(path).replace("\\", "/")


def _write_chapter10_manifest(
    *,
    manifest_path: Path,
    config: ExperimentConfig,
    cli_args: list[str],
    seeds: list[int],
    quick: bool,
    save_plots: bool,
    publication_output_dir: Path,
    chapter10_dir: Path,
    output_paths: dict[str, str],
) -> None:
    """Write chapter10 run manifest for the current output path set."""
    write_manifest(
        manifest_path,
        build_run_manifest(
            config=config,
            mode="chapter10-study",
            cli_args=cli_args,
            extra={
                "seeds": list(seeds),
                "seed_count": len(seeds),
                "quick": bool(quick),
                "save_plots": bool(save_plots),
                "publication_output_dir": str(publication_output_dir),
                "chapter10_output_dir": str(chapter10_dir),
                "output_files": dict(output_paths),
            },
        ),
    )


def _write_chapter10_package_validation(
    *,
    validation_path: Path,
    validation_payload: dict[str, Any],
) -> None:
    """Persist chapter10 package validation JSON payload."""
    validation_path.write_text(
        json.dumps(validation_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _integrity_inputs(output_paths: dict[str, str]) -> dict[str, str]:
    """Drop integrity artifact key to prevent self-hash recursion."""
    return {
        key: path
        for key, path in output_paths.items()
        if key not in {"chapter10_artifact_integrity_json", "chapter10_quality_gate_json"}
    }


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


def _build_chapter10_quality_gate(
    *,
    output_paths: dict[str, str],
) -> QualityGateAssessment:
    """Build unified Chapter10 quality-gate assessment from output artifacts."""
    checks = [
        check_json_ok_artifact(
            gate_id="chapter10-package-validation",
            title="Chapter10 package validation",
            path=output_paths.get("chapter10_package_validation_json", ""),
            required=True,
        ),
        check_manifest_artifact(
            gate_id="chapter10-manifest",
            title="Chapter10 manifest schema",
            path=output_paths.get("chapter10_manifest_json", ""),
            required=True,
        ),
        check_integrity_artifact(
            gate_id="chapter10-integrity",
            title="Chapter10 artifact integrity",
            path=output_paths.get("chapter10_artifact_integrity_json", ""),
            required=True,
        ),
        check_json_ok_artifact(
            gate_id="publication-quality-gate",
            title="Publication quality-gate contract",
            path=output_paths.get("publication_quality_gate_json", ""),
            required=True,
        ),
        check_file_exists(
            gate_id="control-health-json",
            title="Operational control-health appendix (JSON)",
            path=output_paths.get("chapter10_control_health_json", ""),
            required=True,
        ),
        check_file_exists(
            gate_id="control-health-markdown",
            title="Operational control-health appendix (Markdown)",
            path=output_paths.get("chapter10_control_health_md", ""),
            required=True,
        ),
        check_json_ok_artifact(
            gate_id="literature-evidence-gate",
            title="Literature evidence gate",
            path=output_paths.get("chapter10_literature_evidence_gate_json", ""),
            required=False,
            allow_skipped=True,
        ),
        check_claims_gate_artifact(
            gate_id="claims-gate",
            title="Evidence-backed claims gate",
            path=output_paths.get("chapter10_claims_report_json", ""),
            required=False,
        ),
    ]
    return build_quality_gate_assessment(
        mode="chapter10-study",
        scope="chapter10_bundle",
        checks=checks,
        notes=[
            "Required checks are fail-fast for publication-ready bundles.",
            "Quality-gate status is operational and should be interpreted with hypothesis metrics.",
        ],
    )
