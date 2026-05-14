"""Tests for artifact integrity verification CLI helper."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from project.experiments.integrity import write_artifact_integrity_file
from project.experiments.verify_integrity import main


def _workspace_test_output_dir(suffix: str) -> Path:
    """Create unique writable output directory inside workspace."""
    target = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_verify_integrity_cli_success(capsys) -> None:
    """CLI should return zero when integrity report is valid."""
    out_dir = _workspace_test_output_dir("verify-integrity-ok")
    artifact = out_dir / "artifact.txt"
    artifact.write_text("stable\n", encoding="utf-8")
    integrity_path = out_dir / "artifact_integrity.json"
    write_artifact_integrity_file(integrity_path, {"artifact": str(artifact)})

    code = main(["--integrity-file", str(integrity_path)])
    captured = capsys.readouterr()
    assert code == 0
    assert "passed" in captured.out.lower()


def test_verify_integrity_cli_failure(capsys) -> None:
    """CLI should return non-zero when artifact is tampered."""
    out_dir = _workspace_test_output_dir("verify-integrity-fail")
    artifact = out_dir / "artifact.txt"
    artifact.write_text("stable\n", encoding="utf-8")
    integrity_path = out_dir / "artifact_integrity.json"
    write_artifact_integrity_file(integrity_path, {"artifact": str(artifact)})
    artifact.write_text("tampered\n", encoding="utf-8")

    code = main(["--integrity-file", str(integrity_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "failed" in captured.out.lower()
