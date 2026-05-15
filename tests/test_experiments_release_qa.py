"""Tests for release QA harness command/report behavior."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from project.experiments import release_qa


def test_default_commands_cover_all_required_flows() -> None:
    """Default QA suite should include at least one check per required flow."""
    commands = release_qa.build_default_commands("python")
    seen = {item.flow for item in commands}
    for flow in release_qa.REQUIRED_FLOWS:
        assert flow in seen


def test_run_release_qa_marks_failed_flow_and_overall(monkeypatch) -> None:
    """Aggregator should fail overall report when one flow fails."""

    def _fake_execute(spec: release_qa.QACommand, *, cwd: Path) -> dict[str, object]:
        _ = cwd
        passed = spec.flow != "publication"
        return {
            "key": spec.key,
            "flow": spec.flow,
            "command": list(spec.command),
            "timeout_seconds": spec.timeout_seconds,
            "return_code": 0 if passed else 2,
            "passed": passed,
            "duration_seconds": 0.01,
            "completed_at_utc": "2026-01-01T00:00:00+00:00",
            "stdout_tail": [],
            "stderr_tail": [],
        }

    monkeypatch.setattr(release_qa, "_execute_command", _fake_execute)
    commands = [
        release_qa.QACommand("c1", "cli", ["python", "-V"], 5),
        release_qa.QACommand("c2", "web", ["python", "-V"], 5),
        release_qa.QACommand("c3", "repro", ["python", "-V"], 5),
        release_qa.QACommand("c4", "publication", ["python", "-V"], 5),
    ]
    payload = release_qa.run_release_qa(commands=commands, workspace_root=".")
    assert payload["overall_passed"] is False
    assert payload["flows"]["publication"]["passed"] is False
    assert payload["flows"]["cli"]["passed"] is True


def test_main_strict_returns_two_when_report_failed(
    monkeypatch,
) -> None:
    """Strict mode should return 2 when report marks overall failure."""

    def _fake_commands(_python_executable: str) -> list[release_qa.QACommand]:
        return [release_qa.QACommand("sample", "cli", ["python", "-V"], 5)]

    def _fake_run_release_qa(
        *,
        commands: list[release_qa.QACommand],
        workspace_root: str | Path,
    ) -> dict[str, object]:
        _ = commands
        _ = workspace_root
        return {
            "qa_schema": "adaptive-testbed.release-qa",
            "qa_schema_version": "1",
            "created_at_utc": "2026-01-01T00:00:00+00:00",
            "started_at_utc": "2026-01-01T00:00:00+00:00",
            "workspace_root": str(Path(".").resolve()),
            "overall_passed": False,
            "required_flows": list(release_qa.REQUIRED_FLOWS),
            "flows": {
                flow: {"passed": flow == "cli", "checks": ["sample"]}
                for flow in release_qa.REQUIRED_FLOWS
            },
            "checks": [],
        }

    monkeypatch.setattr(release_qa, "build_default_commands", _fake_commands)
    monkeypatch.setattr(release_qa, "run_release_qa", _fake_run_release_qa)

    out_path = _workspace_dir("release-qa-main") / "qa-report.json"
    code = release_qa.main(["--strict", "--output", str(out_path)])
    assert code == 2
    assert out_path.exists()


def _workspace_dir(suffix: str) -> Path:
    """Create unique test workspace under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
