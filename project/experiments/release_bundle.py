"""Release bundle builder for publication appendix reproducibility package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence
import zipfile


DEFAULT_INCLUDES = [
    "configs/release_profiles",
    "docs/release_candidate_checklist.md",
    "docs/reproducibility.md",
    "docs/experimental_pipeline.md",
    "docs/codebase_modules.md",
    "docs/baselines/release_profile_lock.json",
    "docs/baselines/smoke_baseline.json",
    "docs/baselines/scalability_baseline.json",
    "docs/baselines/scalability_baseline_report.md",
    "outputs/release_candidate/release-rc-single",
    "outputs/release_candidate/release-rc-batch-strict/batch",
    "outputs/release_candidate/release-rc-publication/publication",
]


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for release bundle creation."""
    parser = argparse.ArgumentParser(
        description="Create reproducibility release bundle (manifest + zip).",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/release_candidate/bundle",
        help="Directory for generated bundle manifest and zip.",
    )
    parser.add_argument(
        "--bundle-name",
        default="publication_appendix_bundle",
        help="Bundle base name (without extension).",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional file or directory to include (can be repeated).",
    )
    parser.add_argument(
        "--no-default-includes",
        action="store_true",
        help="Disable default release include set.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when any requested include path is missing.",
    )
    return parser


def collect_bundle_files(
    include_paths: list[str | Path],
    *,
    strict: bool = False,
) -> tuple[list[Path], list[str]]:
    """Resolve include roots to a stable sorted file list."""
    files: list[Path] = []
    errors: list[str] = []
    for raw in include_paths:
        path = Path(raw)
        if not path.exists():
            if strict:
                errors.append(f"Missing include path: {path}")
            continue
        if path.is_file():
            files.append(path)
            continue
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file():
                files.append(candidate)
    unique = sorted({file.resolve() for file in files})
    return unique, errors


def build_bundle_manifest(
    *,
    files: list[Path],
    output_dir: Path,
    bundle_name: str,
) -> dict[str, Any]:
    """Build deterministic manifest payload for release bundle."""
    total_size = 0
    artifacts: list[dict[str, Any]] = []
    for path in files:
        size = int(path.stat().st_size)
        total_size += size
        artifacts.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "size_bytes": size,
            }
        )
    return {
        "bundle_schema": "adaptive-testbed.release-bundle",
        "bundle_schema_version": "1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle_name,
        "output_dir": str(output_dir),
        "file_count": len(artifacts),
        "total_size_bytes": total_size,
        "artifacts": artifacts,
    }


def write_bundle(
    *,
    files: list[Path],
    manifest: dict[str, Any],
    output_dir: Path,
    bundle_name: str,
) -> tuple[str, str]:
    """Persist manifest JSON and ZIP archive, return both paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{bundle_name}_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    zip_path = output_dir / f"{bundle_name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest_path, arcname=manifest_path.name)
        for path in files:
            arcname = _safe_arcname(path)
            archive.write(path, arcname=arcname)
    return str(manifest_path), str(zip_path)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for release bundle generation."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    includes: list[str | Path] = []
    if not bool(args.no_default_includes):
        includes.extend(DEFAULT_INCLUDES)
    includes.extend(list(args.include or []))
    files, errors = collect_bundle_files(includes, strict=bool(args.strict))
    if errors:
        print("Release bundle collection failed:")
        for item in errors:
            print(f"- {item}")
        return 2
    if not files:
        print("No files resolved for release bundle.")
        return 2

    output_dir = Path(str(args.output_dir))
    bundle_name = str(args.bundle_name).strip() or "publication_appendix_bundle"
    manifest = build_bundle_manifest(files=files, output_dir=output_dir, bundle_name=bundle_name)
    manifest_path, zip_path = write_bundle(
        files=files,
        manifest=manifest,
        output_dir=output_dir,
        bundle_name=bundle_name,
    )
    print(f"Release bundle manifest: {manifest_path}")
    print(f"Release bundle zip: {zip_path}")
    return 0


def _sha256(path: Path) -> str:
    """Compute SHA-256 checksum for file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_arcname(path: Path) -> str:
    """Build stable zip entry name for absolute/relative path."""
    raw = str(path).replace("\\", "/")
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    return raw.lstrip("/")


if __name__ == "__main__":
    raise SystemExit(main())
