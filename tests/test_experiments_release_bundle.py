"""Tests for release bundle manifest and ZIP builder."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
import zipfile

from project.experiments.release_bundle import (
    DEFAULT_INCLUDES,
    build_bundle_manifest,
    collect_bundle_files,
    main,
    write_bundle,
)


def test_collect_bundle_files_from_directory() -> None:
    """Collector should recursively include files from provided directories."""
    root = _workspace_dir("release-bundle-collect")
    nested = root / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (root / "a.txt").write_text("a", encoding="utf-8")
    (nested / "b.txt").write_text("b", encoding="utf-8")

    files, errors = collect_bundle_files([root], strict=True)
    assert errors == []
    assert len(files) == 2


def test_write_bundle_persists_manifest_and_zip() -> None:
    """Writer should create both JSON manifest and ZIP archive entries."""
    root = _workspace_dir("release-bundle-write")
    f1 = root / "one.txt"
    f2 = root / "two.txt"
    f1.write_text("one", encoding="utf-8")
    f2.write_text("two", encoding="utf-8")
    files = [f1, f2]

    output_dir = root / "bundle"
    manifest = build_bundle_manifest(
        files=files,
        output_dir=output_dir,
        bundle_name="test_bundle",
    )
    manifest_path, zip_path = write_bundle(
        files=files,
        manifest=manifest,
        output_dir=output_dir,
        bundle_name="test_bundle",
    )
    assert Path(manifest_path).exists()
    assert Path(zip_path).exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["file_count"] == 2
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
    assert "test_bundle_manifest.json" in names
    assert any(name.endswith("one.txt") for name in names)
    assert any(name.endswith("two.txt") for name in names)


def test_main_returns_error_for_missing_strict_include() -> None:
    """CLI should fail in strict mode when include path is missing."""
    code = main(
        [
            "--no-default-includes",
            "--strict",
            "--include",
            "missing/path/for/release-bundle",
        ]
    )
    assert code == 2


def test_default_bundle_includes_publication_docs_package() -> None:
    """Default include set should ship final publication docs package."""
    assert "docs/publication_docs_package.md" in DEFAULT_INCLUDES


def _workspace_dir(suffix: str) -> Path:
    """Create unique test workspace directory under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
