"""Sprint 10 smoke baseline runner and golden-regression checker."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from project.algorithms import normalize_algorithm
from project.core.config import ExperimentConfig, load_config
from project.core.models import SystemState
from project.experiments.controller import Experiment
from project.experiments.manifest import (
    build_run_manifest,
    validate_run_manifest_file,
)
from project.experiments.publication import run_publication_pipeline
from project.experiments.runner import BatchRunSpec, ExperimentRunner
from project.metrics import persist_observability, summarize_state

SMOKE_LEGACY_COMPARE_ALGORITHMS = ("round-robin", "min-load", "greedy")
SMOKE_LEGACY_PUBLICATION_METHODS = (
    "round-robin",
    "min-load",
    "greedy",
    "mas-basic",
    "mas-ml",
    "mas-znn",
    "mas-hybrid",
    "mas-llm",
)
SMOKE_LEGACY_PUBLICATION_STUDIES = (
    "E1_scalability",
    "E2_adaptivity",
    "E3_robustness",
    "E4_hybrid_vs_classical",
    "E5_llm_vs_algorithmic",
)
SMOKE_LEGACY_STUDY_METHODS = {
    "E1_scalability": ["round-robin", "min-load", "mas-hybrid", "mas-llm"],
}


def _build_parser() -> ArgumentParser:
    """Build CLI parser for smoke baseline workflow."""
    parser = ArgumentParser(
        description=(
            "Run Sprint-10 smoke baseline (single/compare/batch/publication) "
            "and compare fingerprints against golden file."
        )
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    parser.add_argument(
        "--golden",
        default="docs/baselines/smoke_baseline.json",
        help="Path to golden baseline JSON file.",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Write current smoke baseline to --golden.",
    )
    parser.add_argument(
        "--batch-scenarios",
        default="static,dynamic-load",
        help="Batch scenarios for smoke baseline.",
    )
    parser.add_argument(
        "--batch-algorithms",
        default="round-robin,min-load,greedy",
        help="Batch algorithms for smoke baseline.",
    )
    parser.add_argument(
        "--batch-runs",
        type=int,
        default=1,
        help="Batch repeats for smoke baseline.",
    )
    parser.add_argument(
        "--publication-seeds",
        default="42,43",
        help="Publication quick-seeds for smoke baseline.",
    )
    return parser


def main() -> None:
    """Run baseline pipeline and print pass/fail status."""
    args = _build_parser().parse_args()
    base_config = load_config(args.config)
    baseline = run_smoke_baseline(
        base_config=base_config,
        batch_scenarios=_parse_csv(args.batch_scenarios),
        batch_algorithms=_parse_csv(args.batch_algorithms),
        batch_runs=max(1, int(args.batch_runs)),
        publication_seeds=_parse_int_csv(args.publication_seeds, fallback=[42, 43]),
    )
    golden_path = Path(args.golden)
    if args.update_golden:
        _write_json(golden_path, baseline)
        print(f"Golden baseline updated: {golden_path}")
        print("Smoke baseline status: PASS")
        return

    if golden_path.exists():
        with golden_path.open("r", encoding="utf-8") as f:
            golden = json.load(f)
        comparison = compare_baseline_with_golden(baseline, golden)
        print(f"Golden file: {golden_path}")
        print(f"Baseline match: {comparison['ok']}")
        if comparison["mismatches"]:
            print("Mismatches:")
            for item in comparison["mismatches"]:
                print(f"- {item}")
        print(f"Smoke baseline status: {'PASS' if comparison['ok'] else 'FAIL'}")
        return

    print(f"Golden file not found: {golden_path}")
    print("Use --update-golden to create it from current baseline.")
    print("Smoke baseline status: PASS (no golden comparison)")


def run_smoke_baseline(
    *,
    base_config: ExperimentConfig,
    batch_scenarios: list[str],
    batch_algorithms: list[str],
    batch_runs: int,
    publication_seeds: list[int],
) -> dict[str, Any]:
    """Execute smoke matrix and return fingerprinted baseline snapshot."""
    config = _prepare_smoke_config(base_config)
    cases: list[dict[str, Any]] = []

    single_case = _run_single_case(config)
    cases.append(single_case)

    compare_case = _run_compare_case(config)
    cases.append(compare_case)

    batch_case = _run_batch_case(
        config=config,
        scenarios=batch_scenarios,
        algorithms=batch_algorithms,
        repeats=batch_runs,
    )
    cases.append(batch_case)

    publication_case = _run_publication_case(config, publication_seeds)
    cases.append(publication_case)

    baseline = {
        "schema_version": "sprint10-smoke-baseline-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_name": base_config.name,
        "smoke_config_name": config.name,
        "cases": cases,
    }
    baseline["fingerprints"] = {
        item["case"]: str(item["fingerprint"]) for item in baseline["cases"]
    }
    baseline["overall_ok"] = all(
        bool(item.get("manifest_validation", {}).get("ok", True))
        for item in baseline["cases"]
    )
    return baseline


def compare_baseline_with_golden(
    current: dict[str, Any],
    golden: dict[str, Any],
) -> dict[str, Any]:
    """Compare current baseline with golden snapshot by case fingerprints."""
    mismatches: list[str] = []
    current_fp = current.get("fingerprints", {})
    golden_fp = golden.get("fingerprints", {})
    if not isinstance(current_fp, dict) or not isinstance(golden_fp, dict):
        return {
            "ok": False,
            "mismatches": [
                "Malformed fingerprints section in current or golden baseline."
            ],
        }

    current_cases = set(current_fp.keys())
    golden_cases = set(golden_fp.keys())
    if current_cases != golden_cases:
        missing = sorted(golden_cases - current_cases)
        extra = sorted(current_cases - golden_cases)
        if missing:
            mismatches.append(f"Missing cases in current baseline: {missing}")
        if extra:
            mismatches.append(f"Unexpected cases in current baseline: {extra}")

    for case in sorted(current_cases & golden_cases):
        if str(current_fp[case]) != str(golden_fp[case]):
            mismatches.append(
                f"Fingerprint mismatch for case '{case}': "
                f"current={current_fp[case]} golden={golden_fp[case]}"
            )

    return {"ok": len(mismatches) == 0, "mismatches": mismatches}


def _prepare_smoke_config(config: ExperimentConfig) -> ExperimentConfig:
    """Apply deterministic and lightweight settings for smoke runs."""
    scenario = "static"
    if scenario != _slug(config.scenario):
        scenario = "static"

    observability = replace(
        config.observability,
        save_plots=False,
        save_csv=True,
        save_json=True,
    )
    llm = replace(config.llm, provider="mock")
    return replace(
        config,
        name=f"{config.name}-s10-smoke",
        scenario=scenario,
        observability=observability,
        llm=llm,
    )


def _run_single_case(config: ExperimentConfig) -> dict[str, Any]:
    """Run one deterministic single-mode smoke case."""
    run_config = replace(
        config,
        optimization=replace(config.optimization, algorithm="min-load"),
        llm=replace(config.llm, enabled=False),
    )
    state = Experiment(config=run_config).run()
    artifacts = _persist_case_artifacts(
        config=run_config,
        state=state,
        mode="smoke-single",
        extra={"smoke_case": "single"},
    )
    payload = _normalize_for_fingerprint(
        {
            "scenario": state.scenario,
            "algorithm": state.selected_algorithm,
            "summary": _summary_payload(state),
        }
    )
    return {
        "case": "single",
        "fingerprint": _fingerprint(payload),
        "payload": payload,
        "manifest_validation": _manifest_validation(artifacts),
    }


def _run_compare_case(config: ExperimentConfig) -> dict[str, Any]:
    """Run compare-mode smoke case over the stable legacy algorithm set."""
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for raw_algorithm in SMOKE_LEGACY_COMPARE_ALGORITHMS:
        algorithm = normalize_algorithm(raw_algorithm)
        run_config = replace(
            config,
            optimization=replace(config.optimization, algorithm=algorithm),
            intelligence=replace(config.intelligence, enabled=False, adaptive_algorithm=False),
            llm=replace(config.llm, enabled=False),
        )
        state = Experiment(config=run_config).run()
        artifacts = _persist_case_artifacts(
            config=run_config,
            state=state,
            mode="smoke-compare",
            extra={"smoke_case": "compare", "algorithm": algorithm},
        )
        manifests.append(_manifest_validation(artifacts))
        rows.append(_summary_payload(state))
    rows = sorted(rows, key=lambda item: str(item["algorithm"]))
    payload = _normalize_for_fingerprint(rows)
    return {
        "case": "compare",
        "fingerprint": _fingerprint(payload),
        "payload": payload,
        "manifest_validation": _merge_manifest_results(manifests),
    }


def _run_batch_case(
    *,
    config: ExperimentConfig,
    scenarios: list[str],
    algorithms: list[str],
    repeats: int,
) -> dict[str, Any]:
    """Run batch-mode smoke case with strict algorithm comparison."""
    runner = ExperimentRunner(config)
    spec = BatchRunSpec(
        scenarios=[_slug(item) for item in scenarios],
        algorithms=[normalize_algorithm(item) for item in algorithms],
        repeats=max(1, int(repeats)),
        persist_individual_runs=False,
        strict_algorithm_comparison=True,
    )
    result = runner.run_batch(spec, cli_args=["--smoke-baseline"])
    table = result.summary_df.copy()
    columns = [
        "scenario",
        "algorithm",
        "runs",
        "avg_latency_mean",
        "avg_latency_std",
        "throughput_mean",
        "throughput_std",
        "avg_load_mean",
        "avg_load_std",
        "deadline_violations_mean",
        "pending_tasks_mean",
    ]
    available = [col for col in columns if col in table.columns]
    table = table[available].sort_values(["scenario", "algorithm"]).reset_index(drop=True)
    payload = _normalize_for_fingerprint(_records(table))
    manifest_path = result.output_paths.get("batch_manifest_json", "")
    return {
        "case": "batch",
        "fingerprint": _fingerprint(payload),
        "payload": payload,
        "manifest_validation": _manifest_validation({"run_manifest_json": manifest_path}),
    }


def _run_publication_case(
    config: ExperimentConfig,
    seeds: list[int],
) -> dict[str, Any]:
    """Run publication quick-mode smoke case and capture summary fingerprint."""
    result = run_publication_pipeline(
        config,
        seeds=sorted({int(seed) for seed in seeds}) or [42, 43],
        quick=True,
        save_plots=False,
        cli_args=["--smoke-baseline", "--study-quick"],
        include_study_ids=list(SMOKE_LEGACY_PUBLICATION_STUDIES),
        ready_method_keys=list(SMOKE_LEGACY_PUBLICATION_METHODS),
        study_method_overrides=SMOKE_LEGACY_STUDY_METHODS,
    )
    summary_columns = [
        "study_id",
        "scenario",
        "method",
        "n_runs",
        "avg_latency_mean",
        "throughput_mean",
        "load_imbalance_mean",
        "sla_violations_mean",
    ]
    summary = result.summary.copy()
    available = [col for col in summary_columns if col in summary.columns]
    summary = summary[available].sort_values(["study_id", "method"]).reset_index(drop=True)
    hypotheses = result.hypothesis_df.copy().sort_values("hypothesis").reset_index(drop=True)
    payload = _normalize_for_fingerprint(
        {
            "summary": _records(summary),
            "hypotheses": _records(hypotheses),
        }
    )
    manifest_path = result.output_paths.get("publication_manifest_json", "")
    return {
        "case": "publication",
        "fingerprint": _fingerprint(payload),
        "payload": payload,
        "manifest_validation": _manifest_validation({"run_manifest_json": manifest_path}),
    }


def _persist_case_artifacts(
    *,
    config: ExperimentConfig,
    state: SystemState,
    mode: str,
    extra: dict[str, Any],
) -> dict[str, str]:
    """Persist observability and run manifest for one smoke case."""
    out_dir = (
        Path(config.observability.output_dir)
        / config.name
        / "smoke"
        / _slug(mode)
        / _slug(state.scenario)
        / state.selected_algorithm
    )
    manifest = build_run_manifest(
        config=config,
        mode=mode,
        cli_args=["--smoke-baseline"],
        extra=extra,
    )
    return persist_observability(
        state=state,
        output_dir=out_dir,
        save_csv=config.observability.save_csv,
        save_plots=config.observability.save_plots,
        save_json=config.observability.save_json,
        plot_profile=config.observability.plot_profile,
        plot_dpi=config.observability.plot_dpi,
        plot_formats=config.observability.plot_formats,
        run_manifest=manifest,
    )


def _manifest_validation(artifacts: dict[str, str]) -> dict[str, Any]:
    """Validate run-manifest path referenced by artifacts map."""
    path = artifacts.get("run_manifest_json", "")
    if not path:
        return {"ok": False, "path": "", "errors": ["Missing run_manifest_json artifact."]}
    ok, errors = validate_run_manifest_file(path)
    return {"ok": ok, "path": path, "errors": errors}


def _merge_manifest_results(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge many manifest validations into one aggregate status."""
    errors: list[str] = []
    paths: list[str] = []
    ok = True
    for item in items:
        if not item.get("ok", False):
            ok = False
            errors.extend([str(err) for err in item.get("errors", [])])
        path = str(item.get("path", "")).strip()
        if path:
            paths.append(path)
    return {"ok": ok, "paths": paths, "errors": errors}


def _summary_payload(state: SystemState) -> dict[str, Any]:
    """Extract compact, deterministic summary payload for fingerprinting."""
    summary = summarize_state(state)
    keys = [
        "scenario",
        "algorithm",
        "completed_tasks",
        "pending_tasks",
        "deadline_violations",
        "avg_latency",
        "throughput",
        "avg_load",
        "generated_tasks",
        "mas_messages",
        "mas_assignments",
    ]
    return {key: summary.get(key) for key in keys}


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to JSON-safe records for baseline payload."""
    if df.empty:
        return []
    safe_df = df.where(pd.notna(df), None)
    return json.loads(safe_df.to_json(orient="records"))


def _normalize_for_fingerprint(payload: Any) -> Any:
    """Normalize payload recursively to avoid tiny floating-point noise."""
    if isinstance(payload, dict):
        return {
            str(key): _normalize_for_fingerprint(value)
            for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
        }
    if isinstance(payload, list):
        return [_normalize_for_fingerprint(item) for item in payload]
    if isinstance(payload, float):
        return round(payload, 12)
    return payload


def _fingerprint(payload: Any) -> str:
    """Build stable SHA256 for canonical JSON payload."""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_csv(raw: str) -> list[str]:
    """Parse comma-separated values into unique list."""
    parsed: list[str] = []
    for item in str(raw).split(","):
        text = item.strip()
        if text and text not in parsed:
            parsed.append(text)
    return parsed


def _parse_int_csv(raw: str, fallback: list[int]) -> list[int]:
    """Parse comma-separated integer values."""
    parsed: list[int] = []
    for item in _parse_csv(raw):
        try:
            value = int(item)
        except ValueError:
            continue
        if value not in parsed:
            parsed.append(value)
    return parsed or list(fallback)


def _slug(value: str) -> str:
    """Normalize text token for path-safe usage."""
    return str(value).strip().lower().replace("_", "-").replace(" ", "-")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON payload with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
