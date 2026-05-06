"""Lightweight mutation baseline harness for Sprint 11 quality gates."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


@dataclass(frozen=True)
class MutationCase:
    """Text-based mutation case bound to a target test command."""

    case_id: str
    target_file: str
    search: str
    replacement: str
    test_cmd: list[str]
    occurrence: int = 1


MUTATION_CASES: list[MutationCase] = [
    MutationCase(
        case_id="SCHED_01",
        target_file="project/algorithms/schedulers.py",
        search='if not candidates:\n        return None, rr_cursor',
        replacement='if candidates:\n        return None, rr_cursor',
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_algorithms_schedulers.py",
        ],
    ),
    MutationCase(
        case_id="SCHED_02",
        target_file="project/algorithms/schedulers.py",
        search='if algorithm == "round-robin":',
        replacement='if algorithm != "round-robin":',
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_algorithms_schedulers.py",
        ],
    ),
    MutationCase(
        case_id="SCHED_03",
        target_file="project/algorithms/schedulers.py",
        search='if algorithm == "greedy":',
        replacement='if algorithm != "greedy":',
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_algorithms_schedulers.py",
        ],
    ),
    MutationCase(
        case_id="SCHED_04",
        target_file="project/algorithms/schedulers.py",
        search="if node is not None:",
        replacement="if node is None:",
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_algorithms_schedulers.py",
        ],
    ),
    MutationCase(
        case_id="NODE_01",
        target_file="project/core/models.py",
        search="return min(1.0, self.used_cpu / self.cpu)",
        replacement="return max(1.0, self.used_cpu / self.cpu)",
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_core_models.py",
        ],
    ),
    MutationCase(
        case_id="NODE_02",
        target_file="project/core/models.py",
        search="if not self.is_active:\n            return False",
        replacement="if not self.is_active:\n            return True",
        test_cmd=[
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "tests/test_core_models.py",
        ],
    ),
]


def main() -> None:
    """Run mutation baseline suite and persist JSON report."""
    parser = ArgumentParser(description="Run lightweight mutation baseline suite.")
    parser.add_argument(
        "--output",
        default="docs/baselines/mutation_baseline.json",
        help="Path to JSON report output.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="Timeout for each mutation trial command.",
    )
    parser.add_argument(
        "--fail-on-survivors",
        action="store_true",
        help="Return non-zero exit code if any survivor is found.",
    )
    args = parser.parse_args()

    workspace = Path.cwd()
    report = run_mutation_baseline(
        workspace=workspace,
        cases=MUTATION_CASES,
        timeout_seconds=max(30, int(args.timeout_seconds)),
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    totals = report["summary"]
    print(f"Mutation baseline saved: {output}")
    print(
        "Cases: {total} | Killed: {killed} | Survived: {survived} | "
        "Errors: {errors} | Score: {score:.3f}".format(
            total=totals["total_cases"],
            killed=totals["killed"],
            survived=totals["survived"],
            errors=totals["errors"],
            score=totals["mutation_score"],
        )
    )
    if args.fail_on_survivors and totals["survived"] > 0:
        raise SystemExit(1)


def run_mutation_baseline(
    *,
    workspace: Path,
    cases: list[MutationCase],
    timeout_seconds: int,
) -> dict[str, Any]:
    """Execute configured mutation cases and collect summary metrics."""
    results: list[dict[str, Any]] = []
    for case in cases:
        result = _run_case(workspace=workspace, case=case, timeout_seconds=timeout_seconds)
        results.append(result)

    killed = sum(1 for row in results if row["status"] == "KILLED")
    survived = sum(1 for row in results if row["status"] == "SURVIVED")
    errors = sum(1 for row in results if row["status"] == "ERROR")
    tested = killed + survived
    mutation_score = float(killed) / float(tested) if tested else 0.0

    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite": "sprint11-lightweight-mutation-baseline",
        "summary": {
            "total_cases": len(results),
            "killed": killed,
            "survived": survived,
            "errors": errors,
            "mutation_score": mutation_score,
        },
        "cases": results,
    }


def _run_case(
    *,
    workspace: Path,
    case: MutationCase,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Apply one text mutation, run tests, and restore original source."""
    target = workspace / case.target_file
    if not target.exists():
        return {
            "case_id": case.case_id,
            "status": "ERROR",
            "reason": f"Target file not found: {target}",
        }

    original = target.read_text(encoding="utf-8")
    mutated = _replace_nth(
        text=original,
        old=case.search,
        new=case.replacement,
        occurrence=case.occurrence,
    )
    if mutated is None:
        return {
            "case_id": case.case_id,
            "status": "ERROR",
            "reason": "Mutation pattern was not found in target source.",
        }

    started = time.perf_counter()
    completed: subprocess.CompletedProcess[str] | None = None
    timeout_hit = False
    try:
        target.write_text(mutated, encoding="utf-8")
        completed = subprocess.run(
            case.test_cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        timeout_hit = True
    finally:
        target.write_text(original, encoding="utf-8")

    elapsed_seconds = time.perf_counter() - started
    if timeout_hit:
        return {
            "case_id": case.case_id,
            "target_file": case.target_file,
            "status": "ERROR",
            "reason": f"Timeout after {timeout_seconds}s.",
            "duration_seconds": elapsed_seconds,
        }

    assert completed is not None
    status = _status_from_return_code(completed.returncode)
    return {
        "case_id": case.case_id,
        "target_file": case.target_file,
        "status": status,
        "return_code": completed.returncode,
        "duration_seconds": elapsed_seconds,
        "test_cmd": case.test_cmd,
        "stdout_tail": _tail(completed.stdout, 20),
        "stderr_tail": _tail(completed.stderr, 20),
    }


def _replace_nth(text: str, old: str, new: str, occurrence: int) -> str | None:
    """Replace N-th occurrence of text fragment, return None if not found."""
    if occurrence < 1:
        return None
    start = -1
    index = -1
    for _ in range(occurrence):
        index = text.find(old, start + 1)
        if index < 0:
            return None
        start = index
    return text[:index] + new + text[index + len(old) :]


def _status_from_return_code(return_code: int) -> str:
    """Map pytest return code to mutation verdict."""
    if return_code == 0:
        return "SURVIVED"
    if return_code == 1:
        return "KILLED"
    return "ERROR"


def _tail(text: str, max_lines: int) -> str:
    """Return last N lines of process output to keep JSON compact."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


if __name__ == "__main__":
    main()
