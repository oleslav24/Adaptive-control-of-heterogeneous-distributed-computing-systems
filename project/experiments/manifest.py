from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import platform
from pathlib import Path
import subprocess
from typing import Any

from project.core.config import ExperimentConfig


def build_run_manifest(
    config: ExperimentConfig,
    mode: str,
    cli_args: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return str(target)


def _git_short_commit() -> str:
    result = _run_git(["rev-parse", "--short", "HEAD"])
    if result is None:
        return "unknown"
    return result


def _git_is_dirty() -> bool:
    result = _run_git(["status", "--porcelain"])
    if result is None:
        return False
    return bool(result.strip())


def _run_git(args: list[str]) -> str | None:
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
