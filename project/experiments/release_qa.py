"""Release candidate QA harness across CLI/Web/Repro/Publication flows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Sequence


REQUIRED_FLOWS = ("cli", "web", "repro", "publication")


@dataclass(slots=True)
class QACommand:
    """One QA command spec."""

    key: str
    flow: str
    command: list[str]
    timeout_seconds: int


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for release QA harness."""
    parser = argparse.ArgumentParser(
        description="Run release candidate QA checks and write JSON report.",
    )
    parser.add_argument(
        "--output",
        default="docs/baselines/release_qa_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for command invocations.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when any flow fails.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Working directory for QA commands.",
    )
    return parser


def build_default_commands(python_executable: str) -> list[QACommand]:
    """Build default QA command list for release candidate checks."""
    py = str(python_executable).strip() or sys.executable
    return [
        QACommand(
            key="web_integration_pytests",
            flow="web",
            command=[py, "-m", "pytest", "-q", "tests/test_web_app_integration.py"],
            timeout_seconds=180,
        ),
        QACommand(
            key="cli_dispatch_pytests",
            flow="cli",
            command=[
                py,
                "-m",
                "pytest",
                "-q",
                "tests/test_experiments_cli.py",
                "tests/test_experiments_run_handlers.py",
            ],
            timeout_seconds=180,
        ),
        QACommand(
            key="rc_single_run",
            flow="cli",
            command=[
                py,
                "-B",
                "-m",
                "project.experiments.run",
                "--config",
                "configs/release_profiles/rc_single.yaml",
                "--no-plots",
            ],
            timeout_seconds=240,
        ),
        QACommand(
            key="rc_repro_check",
            flow="repro",
            command=[
                py,
                "-B",
                "-m",
                "project.experiments.run",
                "--config",
                "configs/release_profiles/rc_single.yaml",
                "--repro-check",
                "--repro-runs",
                "5",
                "--no-plots",
            ],
            timeout_seconds=300,
        ),
        QACommand(
            key="rc_batch_run",
            flow="cli",
            command=[
                py,
                "-B",
                "-m",
                "project.experiments.run",
                "--config",
                "configs/release_profiles/rc_batch_strict.yaml",
                "--batch",
                "--batch-runs",
                "2",
                "--no-plots",
            ],
            timeout_seconds=300,
        ),
        QACommand(
            key="rc_publication_quick",
            flow="publication",
            command=[
                py,
                "-B",
                "-m",
                "project.experiments.run",
                "--config",
                "configs/release_profiles/rc_publication.yaml",
                "--publication-study",
                "--study-quick",
                "--study-seeds",
                "42,43",
                "--no-plots",
            ],
            timeout_seconds=300,
        ),
    ]


def run_release_qa(
    *,
    commands: list[QACommand],
    workspace_root: str | Path,
) -> dict[str, Any]:
    """Run QA commands and return report payload."""
    cwd = Path(workspace_root)
    started = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    for spec in commands:
        outcome = _execute_command(spec, cwd=cwd)
        results.append(outcome)

    flows: dict[str, dict[str, Any]] = {}
    for flow in REQUIRED_FLOWS:
        flow_items = [item for item in results if str(item["flow"]) == flow]
        flows[flow] = {
            "passed": bool(flow_items) and all(bool(item["passed"]) for item in flow_items),
            "checks": [str(item["key"]) for item in flow_items],
        }

    overall_passed = all(bool(item["passed"]) for item in results) and all(
        bool(item["passed"]) for item in flows.values()
    )
    return {
        "qa_schema": "adaptive-testbed.release-qa",
        "qa_schema_version": "1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_utc": started,
        "workspace_root": str(cwd.resolve()),
        "overall_passed": overall_passed,
        "required_flows": list(REQUIRED_FLOWS),
        "flows": flows,
        "checks": results,
    }


def write_release_qa_report(path: str | Path, payload: dict[str, Any]) -> str:
    """Persist QA payload as JSON report file."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return str(out)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for release QA harness."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    commands = build_default_commands(str(args.python))
    report = run_release_qa(
        commands=commands,
        workspace_root=args.workspace_root,
    )
    output_path = write_release_qa_report(args.output, report)
    print(f"Release QA report: {output_path}")
    print(f"Release QA overall: {'PASSED' if report['overall_passed'] else 'FAILED'}")
    if bool(args.strict) and not bool(report["overall_passed"]):
        return 2
    return 0


def _execute_command(spec: QACommand, *, cwd: Path) -> dict[str, Any]:
    """Run one QA command and return normalized result payload."""
    started = time.perf_counter()
    completed = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(  # noqa: S603
            spec.command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=max(1, int(spec.timeout_seconds)),
            check=False,
        )
        duration = time.perf_counter() - started
        stdout_tail = _tail_lines(proc.stdout, limit=30)
        stderr_tail = _tail_lines(proc.stderr, limit=30)
        return {
            "key": spec.key,
            "flow": spec.flow,
            "command": list(spec.command),
            "timeout_seconds": int(spec.timeout_seconds),
            "return_code": int(proc.returncode),
            "passed": proc.returncode == 0,
            "duration_seconds": round(duration, 6),
            "completed_at_utc": completed,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - started
        return {
            "key": spec.key,
            "flow": spec.flow,
            "command": list(spec.command),
            "timeout_seconds": int(spec.timeout_seconds),
            "return_code": -9,
            "passed": False,
            "duration_seconds": round(duration, 6),
            "completed_at_utc": completed,
            "stdout_tail": _tail_lines(str(exc.stdout or ""), limit=30),
            "stderr_tail": _tail_lines(str(exc.stderr or ""), limit=30),
            "error": f"Command timed out after {spec.timeout_seconds}s",
        }


def _tail_lines(text: str, *, limit: int) -> list[str]:
    """Return last non-empty lines from multiline text blob."""
    lines = [line.rstrip() for line in str(text).splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return lines[-limit:]


if __name__ == "__main__":
    raise SystemExit(main())
