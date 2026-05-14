"""Artifact integrity helpers for reproducibility verification."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

INTEGRITY_SCHEMA = "adaptive-testbed.artifact-integrity"
INTEGRITY_SCHEMA_VERSION = "1"
INTEGRITY_HASH_ALGORITHM = "sha256"


def compute_file_sha256(path: str | Path) -> str:
    """Compute SHA-256 hash for one file path."""
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_integrity_payload(
    artifact_paths: Mapping[str, str | Path],
) -> dict[str, Any]:
    """Build deterministic integrity payload for produced artifact set."""
    artifacts: dict[str, dict[str, Any]] = {}
    for key in sorted(artifact_paths.keys()):
        label = str(key).strip()
        if not label:
            continue
        raw_path = artifact_paths[key]
        target = Path(raw_path)
        if not target.exists():
            raise FileNotFoundError(f"Artifact path does not exist: {target}")
        stat = target.stat()
        artifacts[label] = {
            "path": str(target),
            "size_bytes": int(stat.st_size),
            "sha256": compute_file_sha256(target),
        }
    return {
        "integrity_schema": INTEGRITY_SCHEMA,
        "integrity_schema_version": INTEGRITY_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": INTEGRITY_HASH_ALGORITHM,
        "artifacts": artifacts,
    }


def write_artifact_integrity_file(
    path: str | Path,
    artifact_paths: Mapping[str, str | Path],
) -> str:
    """Persist artifact integrity payload as JSON and return path."""
    target = Path(path)
    payload = build_artifact_integrity_payload(artifact_paths)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return str(target)


def validate_artifact_integrity_payload(payload: Mapping[str, Any]) -> list[str]:
    """Validate integrity payload schema and field types."""
    errors: list[str] = []
    required_root_keys = [
        "integrity_schema",
        "integrity_schema_version",
        "created_at_utc",
        "algorithm",
        "artifacts",
    ]
    for key in required_root_keys:
        if key not in payload:
            errors.append(f"Missing required key: '{key}'.")

    schema = payload.get("integrity_schema")
    if schema != INTEGRITY_SCHEMA:
        errors.append(
            f"Field 'integrity_schema' must be '{INTEGRITY_SCHEMA}', got '{schema}'."
        )

    schema_version = payload.get("integrity_schema_version")
    if schema_version != INTEGRITY_SCHEMA_VERSION:
        errors.append(
            "Field 'integrity_schema_version' must match supported "
            f"version '{INTEGRITY_SCHEMA_VERSION}'."
        )

    created_at = payload.get("created_at_utc")
    if not isinstance(created_at, str):
        errors.append("Field 'created_at_utc' must be an ISO-8601 string.")
    else:
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("Field 'created_at_utc' must be a valid ISO-8601 datetime.")

    algorithm = payload.get("algorithm")
    if algorithm != INTEGRITY_HASH_ALGORITHM:
        errors.append(
            f"Field 'algorithm' must be '{INTEGRITY_HASH_ALGORITHM}', got '{algorithm}'."
        )

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("Field 'artifacts' must be an object.")
        return errors

    for key, item in artifacts.items():
        if not isinstance(key, str) or not key.strip():
            errors.append("Artifact label must be a non-empty string.")
            continue
        if not isinstance(item, dict):
            errors.append(f"Artifact '{key}' payload must be an object.")
            continue
        path = item.get("path")
        size_bytes = item.get("size_bytes")
        sha256 = item.get("sha256")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"Artifact '{key}' has invalid 'path'.")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            errors.append(f"Artifact '{key}' has invalid 'size_bytes'.")
        if not isinstance(sha256, str) or len(sha256) != 64:
            errors.append(f"Artifact '{key}' has invalid 'sha256'.")
        elif any(ch not in "0123456789abcdef" for ch in sha256.lower()):
            errors.append(f"Artifact '{key}' has non-hex 'sha256'.")
    return errors


def verify_artifact_integrity_payload(payload: Mapping[str, Any]) -> list[str]:
    """Verify artifact hashes/sizes against current filesystem state."""
    errors = validate_artifact_integrity_payload(payload)
    if errors:
        return errors

    artifacts = payload.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return ["Field 'artifacts' must be an object."]

    verification_errors: list[str] = []
    for key, item in artifacts.items():
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        expected_size = item.get("size_bytes")
        expected_hash = item.get("sha256")
        if not isinstance(path, str):
            continue
        target = Path(path)
        if not target.exists():
            verification_errors.append(
                f"Artifact '{key}' file not found: {target}"
            )
            continue
        if isinstance(expected_size, int):
            actual_size = int(target.stat().st_size)
            if actual_size != expected_size:
                verification_errors.append(
                    f"Artifact '{key}' size mismatch: expected {expected_size}, got {actual_size}."
                )
        if isinstance(expected_hash, str):
            actual_hash = compute_file_sha256(target)
            if actual_hash != expected_hash:
                verification_errors.append(
                    f"Artifact '{key}' sha256 mismatch: expected {expected_hash}, got {actual_hash}."
                )
    return verification_errors


def verify_artifact_integrity_file(path: str | Path) -> tuple[bool, list[str]]:
    """Load integrity payload file and verify current artifact set."""
    target = Path(path)
    if not target.exists():
        return False, [f"Integrity file not found: {target}"]
    try:
        with target.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Failed to read integrity JSON: {exc}"]
    if not isinstance(payload, dict):
        return False, ["Integrity root must be a JSON object."]
    errors = verify_artifact_integrity_payload(payload)
    return (len(errors) == 0), errors
