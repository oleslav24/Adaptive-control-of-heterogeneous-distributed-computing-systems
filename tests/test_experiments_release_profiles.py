"""Tests for release profile freeze/lock helpers."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from project.experiments.release_profiles import (
    build_release_profile_lock,
    main,
)


def test_build_release_profile_lock_success_for_required_profiles() -> None:
    """Lock builder should parse all required profiles and return no errors."""
    root = _make_profile_dir("release-profiles-ok")
    _write_profile(root / "rc_single.yaml", provider="mock", llm_enabled=False)
    _write_profile(root / "rc_batch_strict.yaml", provider="mock", llm_enabled=False)
    _write_profile(root / "rc_publication.yaml", provider="mock", llm_enabled=True)

    lock, errors = build_release_profile_lock(root)
    assert errors == []
    assert lock["lock_schema"] == "adaptive-testbed.release-profile-lock"
    assert len(lock["profiles"]) == 3


def test_build_release_profile_lock_rejects_auto_provider() -> None:
    """Auto provider should be rejected for deterministic release lock."""
    root = _make_profile_dir("release-profiles-auto-provider")
    _write_profile(root / "rc_single.yaml", provider="auto", llm_enabled=True)
    _write_profile(root / "rc_batch_strict.yaml", provider="mock", llm_enabled=False)
    _write_profile(root / "rc_publication.yaml", provider="mock", llm_enabled=True)

    _lock, errors = build_release_profile_lock(root)
    assert any("llm.provider must be explicit" in item for item in errors)


def test_main_writes_lock_file() -> None:
    """CLI main should write lock file and return success for valid profiles."""
    root = _make_profile_dir("release-profiles-main")
    _write_profile(root / "rc_single.yaml", provider="mock", llm_enabled=False)
    _write_profile(root / "rc_batch_strict.yaml", provider="mock", llm_enabled=False)
    _write_profile(root / "rc_publication.yaml", provider="mock", llm_enabled=True)
    output = root / "release_profile_lock.json"

    code = main(["--profiles-dir", str(root), "--output", str(output)])
    assert code == 0
    assert output.exists()
    with output.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["lock_schema_version"] == "1"
    assert len(payload["profiles"]) == 3


def _make_profile_dir(suffix: str) -> Path:
    """Create temporary profile directory under workspace outputs."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_profile(path: Path, *, provider: str, llm_enabled: bool) -> None:
    """Write minimal valid release profile YAML for tests."""
    path.write_text(
        "\n".join(
            [
                "name: release-test",
                "scenario: static",
                "",
                "simulation:",
                "  time_horizon: 4",
                "  seed: 42",
                "",
                "optimization:",
                "  algorithm: min-load",
                "  compare_algorithms:",
                "    - round-robin",
                "    - min-load",
                "    - greedy",
                "",
                "intelligence:",
                "  enabled: false",
                "  adaptive_algorithm: false",
                "",
                "llm:",
                f"  enabled: {'true' if llm_enabled else 'false'}",
                f"  provider: {provider}",
                "",
                "observability:",
                "  output_dir: outputs/release_candidate",
                "  save_csv: true",
                "  save_json: true",
                "  save_plots: false",
                "",
                "nodes: []",
                "network_edges: []",
                "initial_tasks: []",
            ]
        ),
        encoding="utf-8",
    )
