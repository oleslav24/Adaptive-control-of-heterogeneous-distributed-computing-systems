"""One-command paper bundle generation (chapter10 + archive package)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from project.core.config import ExperimentConfig
from project.experiments.chapter10 import Chapter10Result, run_chapter10_experiment
from project.experiments.release_bundle import (
    build_bundle_manifest,
    collect_bundle_files,
    write_bundle,
)


@dataclass(slots=True)
class PaperBundleResult:
    """Result of paper bundle generation."""

    output_dir: Path
    chapter10_output_dir: Path
    bundle_manifest_path: str
    bundle_zip_path: str
    include_paths: list[str]
    file_count: int


def run_paper_bundle(
    base_config: ExperimentConfig,
    *,
    seeds: list[int] | None = None,
    quick: bool | None = None,
    save_plots: bool | None = None,
    bundle_name: str = "paper_bundle",
    strict: bool = True,
    cli_args: list[str] | None = None,
) -> PaperBundleResult:
    """Generate chapter10 artifacts and package them into one ZIP bundle."""
    _ = cli_args
    chapter10_result: Chapter10Result = run_chapter10_experiment(
        base_config,
        seeds=seeds,
        quick=quick,
        save_plots=save_plots,
        cli_args=list(cli_args or []),
    )
    output_dir = Path(base_config.observability.output_dir) / base_config.name / "paper_bundle"
    publication_dir = Path(base_config.observability.output_dir) / base_config.name / "publication"
    chapter10_dir = chapter10_result.output_dir

    includes: list[str] = [
        "config.yaml",
        "docs/reproducibility.md",
        "docs/experimental_pipeline.md",
        "docs/chapter10_experiment.md",
        "docs/publication_docs_package.md",
        str(publication_dir),
        str(chapter10_dir),
    ]
    files, errors = collect_bundle_files(includes, strict=strict)
    if errors:
        message = "; ".join(errors)
        raise ValueError(f"Paper bundle collection failed: {message}")
    if not files:
        raise ValueError("Paper bundle collection produced zero files.")

    normalized_name = str(bundle_name).strip() or "paper_bundle"
    manifest = build_bundle_manifest(
        files=files,
        output_dir=output_dir,
        bundle_name=normalized_name,
    )
    manifest_path, zip_path = write_bundle(
        files=files,
        manifest=manifest,
        output_dir=output_dir,
        bundle_name=normalized_name,
    )
    return PaperBundleResult(
        output_dir=output_dir,
        chapter10_output_dir=chapter10_dir,
        bundle_manifest_path=manifest_path,
        bundle_zip_path=zip_path,
        include_paths=includes,
        file_count=len(files),
    )
