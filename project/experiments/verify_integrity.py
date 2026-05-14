"""CLI helper for artifact integrity verification."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from project.experiments.integrity import verify_artifact_integrity_file


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for integrity verification command."""
    parser = argparse.ArgumentParser(
        description="Verify artifact integrity JSON report against filesystem outputs.",
    )
    parser.add_argument(
        "--integrity-file",
        required=True,
        help="Path to artifact_integrity.json file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Verify integrity file and return process exit code."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    target = Path(str(args.integrity_file))
    ok, errors = verify_artifact_integrity_file(target)
    if ok:
        print(f"Integrity check passed: {target}")
        return 0

    print(f"Integrity check failed: {target}")
    for item in errors:
        print(f"- {item}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
