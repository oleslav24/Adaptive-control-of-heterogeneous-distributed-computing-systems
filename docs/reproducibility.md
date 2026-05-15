# Reproducibility SOP (Sprint 15)

## Purpose

This SOP defines an end-to-end reproducibility contract for the testbed:

- deterministic reruns for the same config and seed;
- manifest-based replay from saved run metadata;
- artifact integrity verification by SHA-256 checksums;
- publication-ready export flow.

## 1. Environment Lock

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Use a fixed config file (`config.yaml`) with fixed `simulation.seed`.
4. Prefer deterministic provider settings for LLM experiments:
   - `llm.provider: mock`, or run with `--disable-llm`.

## 2. Run Modes

Single run:

```bash
python -m project.experiments.run --config config.yaml
```

Strict batch comparison:

```bash
python -m project.experiments.run --config config.yaml --batch --batch-runs 5
```

Reproducibility check (repeat identical run N times):

```bash
python -m project.experiments.run --config config.yaml --repro-check --repro-runs 30
```

Manifest replay (rebuild run from saved manifest snapshot):

```bash
python -m project.experiments.run --replay-manifest outputs/<exp>/<scenario>/<algorithm>/run_manifest.json --replay-runs 10
```

Publication pipeline:

```bash
python -m project.experiments.run --config config.yaml --publication-study
```

Smoke baseline:

```bash
python -m project.experiments.smoke --config config.yaml
```

Scalability profiling sweep:

```bash
python -m project.experiments.run --config config.yaml --scalability-profile --scenario static --scalability-nodes 10,50 --scalability-tasks 100,500 --scalability-algorithms round-robin,min-load,greedy --scalability-runs 1 --scalability-topology ring --no-plots
```

Scalability performance budget gate:

```bash
python -m project.experiments.performance_budget --config config.yaml --nodes 10 --tasks 100 --algorithms min-load,greedy --repeats 1 --topology ring --scenario static --max-runtime-seconds 1.0 --min-throughput 0.05 --max-pending-tasks 500
```

Release appendix bundle:

```bash
python -m project.experiments.release_bundle --strict --output-dir outputs/release_candidate/bundle --bundle-name publication_appendix_bundle_rc
```

Generate scalability baseline JSON + markdown report:

```bash
python -m project.experiments.scalability_report --summary-csv outputs/sprint9-publication-ready/scalability-profile/scalability_summary.csv --output-json docs/baselines/scalability_baseline.json --output-md docs/baselines/scalability_baseline_report.md --scenario static --topology ring --nodes 10,50 --tasks 100,500 --algorithms round-robin,min-load,greedy
```

Update smoke golden snapshot (only on intentional baseline refresh):

```bash
python -m project.experiments.smoke --config config.yaml --update-golden
```

## 3. Required Artifacts

Single/compare/AB/repro/replay flows export:

- run/repro/replay manifests (`*_manifest.json`);
- metric outputs (`*.csv`, `*.json`);
- `artifact_integrity.json` (or mode-specific integrity file);
- replay verification report for replay mode:
  - `replay_verification_report.json`.

Batch flow additionally exports:

- `batch_manifest.json`;
- `batch_runs.csv`, `batch_summary.csv`, `batch_ranking.csv`, `batch_winners.csv`;
- `artifact_integrity.json` in batch output directory.

Publication flow additionally exports:

- `publication_manifest.json`;
- summary/hypothesis validation JSON;
- report markdown;
- publication plots and tabular outputs;
- `artifact_integrity.json`.

## 4. Integrity Verification

Run checksum verification against produced integrity report:

```bash
python -m project.experiments.verify_integrity --integrity-file outputs/<...>/artifact_integrity.json
```

Expected behavior:

- exit code `0`: all files exist and match recorded `sha256`/size;
- exit code `2`: at least one artifact mismatch or missing file.

## 5. Replay Verification Procedure

1. Produce source run and keep its `run_manifest.json`.
2. Execute `--replay-manifest` with required repeat count.
3. Inspect:
   - `replay_runs.csv`;
   - `replay_verification_report.json`;
   - `replay_artifact_integrity.json`.
4. Verify replay integrity report using `verify_integrity` command.
5. Treat reproducibility as confirmed only when:
   - `reproducible: true` in replay report;
   - integrity check passes.

## 6. Publication-Grade Checklist

Before exporting results for paper/monograph:

1. Re-run smoke baseline and confirm no fingerprint drift.
2. Run `--repro-check` with statistically meaningful repeats (recommended `>=30`).
3. Run replay from saved manifests for key experiments (E1-E5).
4. Verify artifact integrity reports for:
   - single key runs;
   - batch outputs;
   - publication outputs.
5. Archive manifests, integrity reports, and generated tables/plots together.

## 7. Notes

- For strict algorithm-only comparison, use `--batch` without `--batch-keep-adaptive`.
- `git_dirty: true` in manifests indicates local uncommitted state; avoid using such runs for final publication tables.
