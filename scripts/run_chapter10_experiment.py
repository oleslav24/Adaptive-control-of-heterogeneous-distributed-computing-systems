"""Convenience wrapper for Chapter 10 experiment mode."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """Execute chapter10 mode using project CLI entrypoint."""
    command = [
        sys.executable,
        "-m",
        "project.experiments.run",
        "--config",
        "config.yaml",
        "--chapter10",
    ]
    command.extend(list(sys.argv[1:]))
    completed = subprocess.run(command, check=False)  # noqa: S603
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
