"""Command builder for web form to experiments CLI."""

from __future__ import annotations

import sys
from typing import Mapping

from project.web.i18n import ALGORITHM_OPTIONS, MODE_OPTIONS, SCENARIO_OPTIONS


def _first(mapping: Mapping[str, list[str]], key: str, default: str = "") -> str:
    """Read first value from parsed query/form mapping."""
    values = mapping.get(key, [])
    if not values:
        return default
    return values[0]


def _collect_multi_values(
    mapping: Mapping[str, list[str]],
    key: str,
    *,
    allowed: set[str] | None = None,
) -> list[str]:
    """Collect unique multi-select values (checkboxes or comma-separated fallback)."""
    raw_values = list(mapping.get(key, []))
    if not raw_values:
        fallback = _first(mapping, key, "").strip()
        if fallback:
            raw_values = [fallback]

    selected: list[str] = []
    for raw in raw_values:
        parts = str(raw).split(",")
        for part in parts:
            value = part.strip()
            if not value:
                continue
            if allowed is not None and value not in allowed:
                continue
            if value not in selected:
                selected.append(value)
    return selected


def _is_checked(form: Mapping[str, list[str]], name: str) -> bool:
    """Interpret checkbox field as boolean."""
    value = _first(form, name, "")
    return value.lower() in {"on", "1", "true", "yes"}


def _safe_int(text: str, fallback: int, minimum: int | None = None) -> int:
    """Parse integer with fallback and optional minimum."""
    try:
        value = int(text.strip())
    except Exception:  # noqa: BLE001
        value = fallback
    if minimum is not None:
        value = max(minimum, value)
    return value


def build_run_command(
    form: Mapping[str, list[str]],
    *,
    default_config: str = "config.yaml",
    python_executable: str | None = None,
) -> list[str]:
    """Build CLI command from web form fields."""
    config = _first(form, "config", default_config).strip() or default_config
    mode = _first(form, "mode", "single").strip().lower()
    mode = mode if mode in MODE_OPTIONS else "single"

    command: list[str] = [
        python_executable or sys.executable,
        "-m",
        "project.experiments.run",
        "--config",
        config,
    ]

    algorithm = _first(form, "algorithm", "").strip()
    if algorithm:
        command.extend(["--algorithm", algorithm])

    scenario = _first(form, "scenario", "").strip()
    if scenario:
        command.extend(["--scenario", scenario])

    llm_provider = _first(form, "llm_provider", "").strip()
    if llm_provider:
        command.extend(["--llm-provider", llm_provider])

    output_dir = _first(form, "output_dir", "").strip()
    if output_dir:
        command.extend(["--output-dir", output_dir])

    log_level = _first(form, "log_level", "").strip()
    if log_level:
        command.extend(["--log-level", log_level])

    if _is_checked(form, "disable_intelligence"):
        command.append("--disable-intelligence")
    if _is_checked(form, "disable_llm"):
        command.append("--disable-llm")
    if _is_checked(form, "no_plots"):
        command.append("--no-plots")
    if _is_checked(form, "no_csv"):
        command.append("--no-csv")

    if mode == "compare":
        command.append("--compare")
        compare_algorithms = _collect_multi_values(
            form,
            "compare_algorithms",
            allowed={name for name in ALGORITHM_OPTIONS if name},
        )
        if compare_algorithms:
            command.extend(["--compare-algorithms", ",".join(compare_algorithms)])

    elif mode == "batch":
        command.append("--batch")
        batch_scenarios = _collect_multi_values(
            form,
            "batch_scenarios",
            allowed={name for name in SCENARIO_OPTIONS if name},
        )
        if batch_scenarios:
            command.extend(["--batch-scenarios", ",".join(batch_scenarios)])
        batch_algorithms = _collect_multi_values(
            form,
            "batch_algorithms",
            allowed={name for name in ALGORITHM_OPTIONS if name},
        )
        if batch_algorithms:
            command.extend(["--batch-algorithms", ",".join(batch_algorithms)])
        batch_runs = _safe_int(_first(form, "batch_runs", "3"), fallback=3, minimum=1)
        command.extend(["--batch-runs", str(batch_runs)])
        if _is_checked(form, "batch_save_runs"):
            command.append("--batch-save-runs")
        if _is_checked(form, "batch_keep_adaptive"):
            command.append("--batch-keep-adaptive")

    elif mode == "publication":
        command.append("--publication-study")
        if _is_checked(form, "study_quick"):
            command.append("--study-quick")
        study_seeds = _first(form, "study_seeds", "42-71").strip()
        if study_seeds:
            command.extend(["--study-seeds", study_seeds])

    elif mode == "carbon-study":
        command.append("--carbon-study")
        if _is_checked(form, "study_quick"):
            command.append("--carbon-quick")
        study_seeds = _first(form, "study_seeds", "42-71").strip()
        if study_seeds:
            command.extend(["--carbon-seeds", study_seeds])

    elif mode == "chapter10":
        command.append("--chapter10")
        if _is_checked(form, "study_quick"):
            command.append("--chapter10-quick")
        study_seeds = _first(form, "study_seeds", "42-71").strip()
        if study_seeds:
            command.extend(["--chapter10-seeds", study_seeds])

    elif mode == "paper-bundle":
        command.append("--paper-bundle")
        if _is_checked(form, "study_quick"):
            command.append("--chapter10-quick")
        study_seeds = _first(form, "study_seeds", "42-71").strip()
        if study_seeds:
            command.extend(["--chapter10-seeds", study_seeds])
        bundle_name = _first(form, "paper_bundle_name", "paper_bundle").strip()
        if bundle_name:
            command.extend(["--paper-bundle-name", bundle_name])

    elif mode == "ab-intelligence":
        command.append("--ab-intelligence")

    elif mode == "ab-llm":
        command.append("--ab-llm")

    elif mode == "repro-check":
        command.append("--repro-check")
        repro_runs = _safe_int(_first(form, "repro_runs", "3"), fallback=3, minimum=2)
        command.extend(["--repro-runs", str(repro_runs)])

    return command
