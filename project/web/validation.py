"""Server-side validation helpers for web run requests."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Mapping

from project.web.i18n import ALGORITHM_OPTIONS, MODE_OPTIONS, SCENARIO_OPTIONS


_ALGORITHM_SET = {item for item in ALGORITHM_OPTIONS if item}
_SCENARIO_SET = {item for item in SCENARIO_OPTIONS if item}
_LOG_LEVEL_SET = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_LLM_PROVIDER_SET = {"auto", "openai", "mock"}
_BUNDLE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def validate_start_run_form(
    form: Mapping[str, list[str]],
    *,
    workspace_root: Path,
    default_config: str,
) -> list[str]:
    """Validate run form before command build/launch."""
    errors: list[str] = []
    mode = _first(form, "mode", "single").strip().lower()
    if mode not in MODE_OPTIONS:
        errors.append(f"Invalid mode: '{mode}'.")

    config_value = _first(form, "config", default_config).strip() or default_config
    config_path = _resolve_workspace_path(config_value, workspace_root)
    if config_path is None:
        errors.append("Config path must stay inside workspace.")
    else:
        if not config_path.exists():
            errors.append(f"Config file not found: '{config_value}'.")
        elif not config_path.is_file():
            errors.append(f"Config path is not a file: '{config_value}'.")

    algorithm = _first(form, "algorithm", "").strip()
    if algorithm and algorithm not in _ALGORITHM_SET:
        errors.append(f"Invalid algorithm: '{algorithm}'.")

    scenario = _first(form, "scenario", "").strip()
    if scenario and scenario not in _SCENARIO_SET:
        errors.append(f"Invalid scenario: '{scenario}'.")

    llm_provider = _first(form, "llm_provider", "").strip().lower()
    if llm_provider and llm_provider not in _LLM_PROVIDER_SET:
        errors.append(f"Invalid LLM provider: '{llm_provider}'.")

    log_level = _first(form, "log_level", "").strip().upper()
    if log_level and log_level not in _LOG_LEVEL_SET:
        errors.append(f"Invalid log level: '{log_level}'.")

    output_dir = _first(form, "output_dir", "").strip()
    if output_dir:
        output_path = _resolve_workspace_path(output_dir, workspace_root)
        if output_path is None:
            errors.append("Output directory must stay inside workspace.")

    timeout_raw = _first(form, "job_timeout_seconds", "").strip()
    if timeout_raw:
        timeout_value = _parse_int(timeout_raw)
        if timeout_value is None:
            errors.append("Job timeout must be an integer.")
        elif timeout_value < 10 or timeout_value > 86400:
            errors.append("Job timeout must be between 10 and 86400 seconds.")

    if mode == "compare":
        compare = _collect_multi(form, "compare_algorithms")
        bad = [item for item in compare if item not in _ALGORITHM_SET]
        if bad:
            errors.append(f"Invalid compare algorithms: {', '.join(bad)}.")

    if mode == "batch":
        batch_scenarios = _collect_multi(form, "batch_scenarios")
        bad_scenarios = [item for item in batch_scenarios if item not in _SCENARIO_SET]
        if bad_scenarios:
            errors.append(f"Invalid batch scenarios: {', '.join(bad_scenarios)}.")

        batch_algorithms = _collect_multi(form, "batch_algorithms")
        bad_algorithms = [item for item in batch_algorithms if item not in _ALGORITHM_SET]
        if bad_algorithms:
            errors.append(f"Invalid batch algorithms: {', '.join(bad_algorithms)}.")

        batch_runs = _parse_int(_first(form, "batch_runs", "3"))
        if batch_runs is None or batch_runs < 1 or batch_runs > 1000:
            errors.append("Batch runs must be between 1 and 1000.")

    if mode == "repro-check":
        repro_runs = _parse_int(_first(form, "repro_runs", "3"))
        if repro_runs is None or repro_runs < 2 or repro_runs > 1000:
            errors.append("Repro runs must be between 2 and 1000.")

    if mode in {"publication", "carbon-study", "chapter10", "paper-bundle"}:
        seeds = _first(form, "study_seeds", "42-71").strip()
        if seeds and not _is_valid_seed_expression(seeds):
            errors.append("Study seeds must be comma-list or numeric range.")
    if mode == "paper-bundle":
        bundle_name = _first(form, "paper_bundle_name", "paper_bundle").strip()
        if bundle_name and _BUNDLE_NAME_RE.fullmatch(bundle_name) is None:
            errors.append(
                "Paper bundle name may contain only letters, digits, dot, underscore, dash."
            )

    return errors


def _resolve_workspace_path(raw: str, workspace_root: Path) -> Path | None:
    """Resolve input path and ensure it stays under workspace root."""
    text = str(raw).strip()
    if not text:
        return None
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        resolved = candidate.resolve(strict=False)
        workspace = workspace_root.resolve(strict=False)
    except OSError:
        return None
    if not _is_relative_to(resolved, workspace):
        return None
    return resolved


def _is_relative_to(path: Path, base: Path) -> bool:
    """Backport-safe check for path containment."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _parse_int(raw: str) -> int | None:
    """Parse strict integer from text."""
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _first(mapping: Mapping[str, list[str]], key: str, default: str = "") -> str:
    """Read first item from parsed mapping."""
    values = mapping.get(key, [])
    if not values:
        return default
    return str(values[0])


def _collect_multi(mapping: Mapping[str, list[str]], key: str) -> list[str]:
    """Collect unique values from repeated form field."""
    seen: list[str] = []
    for raw in mapping.get(key, []):
        for part in str(raw).split(","):
            value = part.strip()
            if not value:
                continue
            if value not in seen:
                seen.append(value)
    return seen


def _is_valid_seed_expression(raw: str) -> bool:
    """Validate publication seeds expression without executing parsing."""
    text = str(raw).strip()
    if not text:
        return False
    if "-" in text and "," not in text:
        left, _, right = text.partition("-")
        return left.strip().isdigit() and right.strip().isdigit()
    parts = [item.strip() for item in text.split(",")]
    return all(part.isdigit() for part in parts if part) and any(parts)
