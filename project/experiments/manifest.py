"""Run-manifest helpers for reproducibility metadata."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import platform
from pathlib import Path
import subprocess
from typing import Any, Mapping

from project.core.config import ExperimentConfig


def build_run_manifest(
    config: ExperimentConfig,
    mode: str,
    cli_args: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build reproducibility manifest for a run/batch/publication execution."""
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": str(mode),
        "cli_args": list(cli_args),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_short_commit(),
        "git_dirty": _git_is_dirty(),
        "dependencies": _collect_dependency_versions(),
        "config": asdict(config),
        "extra": extra or {},
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> str:
    """Persist manifest as formatted JSON and return target path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return str(target)


def validate_run_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Validate required run-manifest schema and return list of errors."""
    errors: list[str] = []
    required_root_keys = [
        "created_at_utc",
        "mode",
        "cli_args",
        "python_version",
        "platform",
        "git_commit",
        "git_dirty",
        "dependencies",
        "config",
        "extra",
    ]
    for key in required_root_keys:
        if key not in manifest:
            errors.append(f"Missing required key: '{key}'.")

    mode = manifest.get("mode")
    if not isinstance(mode, str) or not mode.strip():
        errors.append("Field 'mode' must be a non-empty string.")

    cli_args = manifest.get("cli_args")
    if not isinstance(cli_args, list) or not all(
        isinstance(item, str) for item in cli_args
    ):
        errors.append("Field 'cli_args' must be a list[str].")

    git_dirty = manifest.get("git_dirty")
    if not isinstance(git_dirty, bool):
        errors.append("Field 'git_dirty' must be a boolean.")

    config = manifest.get("config")
    if not isinstance(config, dict):
        errors.append("Field 'config' must be an object.")

    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict):
        errors.append("Field 'dependencies' must be an object.")
    else:
        required_deps = ["numpy", "pandas", "matplotlib", "networkx", "pyyaml"]
        for dep in required_deps:
            value = dependencies.get(dep)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Dependency '{dep}' is missing or has invalid version value."
                )
    return errors


def validate_run_manifest_file(path: str | Path) -> tuple[bool, list[str]]:
    """Load and validate manifest JSON file."""
    target = Path(path)
    if not target.exists():
        return False, [f"Manifest file not found: {target}"]
    try:
        with target.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Failed to read manifest JSON: {exc}"]
    if not isinstance(payload, dict):
        return False, ["Manifest root must be a JSON object."]
    errors = validate_run_manifest(payload)
    return (len(errors) == 0), errors


def _git_short_commit() -> str:
    """Return short git commit hash or placeholder when unavailable."""
    result = _run_git(["rev-parse", "--short", "HEAD"])
    if result is None:
        return "unknown"
    return result


def _git_is_dirty() -> bool:
    """Return True when working tree has uncommitted changes."""
    result = _run_git(["status", "--porcelain"])
    if result is None:
        return False
    return bool(result.strip())


def _run_git(args: list[str]) -> str | None:
    """Run git command and return stdout on success."""
    try:
        completed = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _collect_dependency_versions() -> dict[str, str]:
    """Collect versions of core runtime dependencies."""
    package_map = {
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "networkx": "networkx",
        "pyyaml": "PyYAML",
    }
    versions: dict[str, str] = {}
    for key, pkg_name in package_map.items():
        try:
            versions[key] = version(pkg_name)
        except PackageNotFoundError:
            versions[key] = "not-installed"
    return versions
