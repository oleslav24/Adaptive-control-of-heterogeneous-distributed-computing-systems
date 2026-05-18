"""Tests for chapter10 + release bundle orchestration helper."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from project.core.config import ExperimentConfig, load_config
from project.experiments.chapter10 import Chapter10Result
from project.experiments.paper_bundle import run_paper_bundle


def _config(output_root: Path) -> ExperimentConfig:
    """Load base config and redirect outputs into test temp directory."""
    config = load_config("config.yaml")
    observability = replace(config.observability, output_dir=str(output_root))
    return replace(config, name="paper-bundle-test", observability=observability)


def _chapter10_result(output_dir: Path) -> Chapter10Result:
    """Build minimal chapter10 result object for stubbing."""
    return Chapter10Result(
        output_dir=output_dir,
        summary=pd.DataFrame(),
        hypotheses=pd.DataFrame(),
        output_paths={},
    )


def test_run_paper_bundle_packages_chapter10_outputs(monkeypatch) -> None:
    """Paper bundle should execute chapter10 and forward files into bundle writer."""
    output_root = _workspace_dir("paper-bundle-happy")
    config = _config(output_root)
    chapter10_dir = output_root / config.name / "chapter10"
    chapter10_dir.mkdir(parents=True, exist_ok=True)
    collected_file = output_root / "artifact.txt"
    collected_file.write_text("artifact", encoding="utf-8")

    calls: dict[str, object] = {}

    def _fake_run_chapter10_experiment(
        _config: ExperimentConfig,
        *,
        seeds: list[int] | None,
        quick: bool | None,
        save_plots: bool | None,
        cli_args: list[str] | None,
    ) -> Chapter10Result:
        calls["chapter10_seeds"] = seeds
        calls["chapter10_quick"] = quick
        calls["chapter10_save_plots"] = save_plots
        calls["chapter10_cli_args"] = list(cli_args or [])
        return _chapter10_result(chapter10_dir)

    def _fake_collect_bundle_files(includes, *, strict: bool):
        calls["includes"] = [str(item) for item in includes]
        calls["strict"] = strict
        return [collected_file], []

    def _fake_build_bundle_manifest(*, files, output_dir: Path, bundle_name: str):
        calls["manifest_files"] = [str(item) for item in files]
        calls["manifest_output_dir"] = str(output_dir)
        calls["manifest_bundle_name"] = bundle_name
        return {"bundle_name": bundle_name, "file_count": len(files)}

    def _fake_write_bundle(*, files, manifest, output_dir: Path, bundle_name: str):
        calls["write_files"] = [str(item) for item in files]
        calls["write_manifest"] = dict(manifest)
        calls["write_output_dir"] = str(output_dir)
        calls["write_bundle_name"] = bundle_name
        return (
            str(output_dir / f"{bundle_name}_manifest.json"),
            str(output_dir / f"{bundle_name}.zip"),
        )

    monkeypatch.setattr(
        "project.experiments.paper_bundle.run_chapter10_experiment",
        _fake_run_chapter10_experiment,
    )
    monkeypatch.setattr(
        "project.experiments.paper_bundle.collect_bundle_files",
        _fake_collect_bundle_files,
    )
    monkeypatch.setattr(
        "project.experiments.paper_bundle.build_bundle_manifest",
        _fake_build_bundle_manifest,
    )
    monkeypatch.setattr(
        "project.experiments.paper_bundle.write_bundle",
        _fake_write_bundle,
    )

    result = run_paper_bundle(
        config,
        seeds=[42, 43],
        quick=True,
        save_plots=False,
        bundle_name="ase_bundle_v1",
        strict=True,
        cli_args=["--paper-bundle"],
    )

    assert calls["chapter10_seeds"] == [42, 43]
    assert calls["chapter10_quick"] is True
    assert calls["chapter10_save_plots"] is False
    assert calls["chapter10_cli_args"] == ["--paper-bundle"]
    assert calls["strict"] is True
    includes = calls["includes"]
    assert str(chapter10_dir) in includes
    assert str(output_root / config.name / "publication") in includes
    assert calls["manifest_bundle_name"] == "ase_bundle_v1"
    assert calls["write_bundle_name"] == "ase_bundle_v1"
    assert result.file_count == 1
    assert result.chapter10_output_dir == chapter10_dir
    assert result.bundle_manifest_path.endswith("ase_bundle_v1_manifest.json")
    assert result.bundle_zip_path.endswith("ase_bundle_v1.zip")


def test_run_paper_bundle_fails_when_bundle_collection_reports_errors(
    monkeypatch,
) -> None:
    """Collection errors should fail fast in strict paper-bundle mode."""
    output_root = _workspace_dir("paper-bundle-errors")
    config = _config(output_root)
    chapter10_dir = output_root / config.name / "chapter10"
    chapter10_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "project.experiments.paper_bundle.run_chapter10_experiment",
        lambda *_args, **_kwargs: _chapter10_result(chapter10_dir),
    )
    monkeypatch.setattr(
        "project.experiments.paper_bundle.collect_bundle_files",
        lambda *_args, **_kwargs: ([], ["Missing include path: docs/missing.md"]),
    )

    with pytest.raises(ValueError, match="Paper bundle collection failed"):
        run_paper_bundle(config, bundle_name="ase_bundle_v1")


def _workspace_dir(suffix: str) -> Path:
    """Create unique test workspace directory under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
