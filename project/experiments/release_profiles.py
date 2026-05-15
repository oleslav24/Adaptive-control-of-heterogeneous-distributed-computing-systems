"""Release profile freeze/lock helpers for Sprint 18 release candidate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from project.core.config import ExperimentConfig, load_config

LOCK_SCHEMA = "adaptive-testbed.release-profile-lock"
LOCK_SCHEMA_VERSION = "1"
DEFAULT_REQUIRED_PROFILES = [
    "rc_single.yaml",
    "rc_batch_strict.yaml",
    "rc_publication.yaml",
]


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for release profile locking command."""
    parser = argparse.ArgumentParser(
        description="Validate frozen release profiles and persist lock metadata.",
    )
    parser.add_argument(
        "--profiles-dir",
        default="configs/release_profiles",
        help="Directory containing frozen release profile YAML files.",
    )
    parser.add_argument(
        "--output",
        default="docs/baselines/release_profile_lock.json",
        help="Output path for lock metadata JSON.",
    )
    parser.add_argument(
        "--allow-openai-llm",
        action="store_true",
        help="Allow enabled LLM profiles with provider=openai.",
    )
    return parser


def build_release_profile_lock(
    profiles_dir: str | Path,
    *,
    required_profiles: list[str] | None = None,
    allow_openai_llm: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Build release profile lock payload and collect validation errors."""
    root = Path(profiles_dir)
    required = list(required_profiles or DEFAULT_REQUIRED_PROFILES)
    errors: list[str] = []
    records: list[dict[str, Any]] = []

    if not root.exists():
        return {}, [f"Profiles directory not found: {root}"]

    present = sorted(path.name for path in root.glob("*.yaml"))
    for required_name in required:
        if required_name not in present:
            errors.append(f"Missing required release profile: {required_name}")

    for name in present:
        path = root / name
        try:
            config = load_config(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to parse '{name}': {exc}")
            continue
        errors.extend(_validate_release_config(name, config, allow_openai_llm=allow_openai_llm))
        records.append(_build_profile_record(path, config))

    lock = {
        "lock_schema": LOCK_SCHEMA,
        "lock_schema_version": LOCK_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "profiles_dir": str(root),
        "required_profiles": required,
        "profiles": sorted(records, key=lambda item: str(item["profile"])),
    }
    return lock, errors


def write_release_profile_lock(path: str | Path, payload: dict[str, Any]) -> str:
    """Persist lock payload to JSON and return output path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return str(target)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for release profile locking."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    lock, errors = build_release_profile_lock(
        args.profiles_dir,
        allow_openai_llm=bool(args.allow_openai_llm),
    )
    if errors:
        print("Release profile validation failed:")
        for item in errors:
            print(f"- {item}")
        return 2

    output = write_release_profile_lock(args.output, lock)
    print(f"Release profile lock written: {output}")
    return 0


def _build_profile_record(path: Path, config: ExperimentConfig) -> dict[str, Any]:
    """Build one lock record from parsed profile config."""
    return {
        "profile": path.name,
        "sha256": _sha256(path),
        "experiment_name": config.name,
        "scenario": config.scenario,
        "seed": config.simulation.seed,
        "time_horizon": config.simulation.time_horizon,
        "algorithm": config.optimization.algorithm,
        "compare_algorithms": list(config.optimization.compare_algorithms),
        "intelligence_enabled": config.intelligence.enabled,
        "llm_enabled": config.llm.enabled,
        "llm_provider": config.llm.provider,
        "output_dir": config.observability.output_dir,
        "node_count": len(config.nodes),
        "task_count": len(config.initial_tasks),
    }


def _validate_release_config(
    profile_name: str,
    config: ExperimentConfig,
    *,
    allow_openai_llm: bool,
) -> list[str]:
    """Validate reproducibility constraints for one release profile."""
    errors: list[str] = []
    if config.simulation.seed < 0:
        errors.append(f"{profile_name}: simulation.seed must be non-negative.")
    if not str(config.observability.output_dir).strip():
        errors.append(f"{profile_name}: observability.output_dir must be non-empty.")
    if "release_candidate" not in str(config.observability.output_dir):
        errors.append(
            f"{profile_name}: output_dir should include 'release_candidate' for release isolation."
        )

    provider = str(config.llm.provider).strip().lower()
    if provider == "auto":
        errors.append(f"{profile_name}: llm.provider must be explicit (mock/openai), not auto.")
    if config.llm.enabled and provider == "openai" and not allow_openai_llm:
        errors.append(
            f"{profile_name}: llm.enabled with provider=openai is blocked for deterministic release lock."
        )
    return errors


def _sha256(path: Path) -> str:
    """Compute SHA-256 for file path."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
