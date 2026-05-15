# Release Candidate Checklist (Sprint 18)

## Scope

This checklist is used to prepare publication-grade release artifacts for the monograph/paper appendix.

Frozen profiles:

- `configs/release_profiles/rc_single.yaml`
- `configs/release_profiles/rc_batch_strict.yaml`
- `configs/release_profiles/rc_publication.yaml`

## 1. Freeze and Lock Profiles

1. Validate and lock release profiles:

```bash
python -m project.experiments.release_profiles --profiles-dir configs/release_profiles --output docs/baselines/release_profile_lock.json
```

2. Ensure lock file is versioned:

- `docs/baselines/release_profile_lock.json`

3. Confirm each profile has:

- fixed `simulation.seed`
- explicit `llm.provider` (no `auto`)
- isolated `observability.output_dir` containing `release_candidate`

## 2. Required Gates

1. Static checks:

```bash
python -m ruff check --no-cache project tests
python -m mypy --no-sqlite-cache --cache-dir .mypy_cache_ci --follow-imports=skip project/core/models.py project/algorithms/schedulers.py project/simulation/context.py project/simulation/mas.py project/simulation/loop.py project/experiments/manifest.py project/experiments/smoke.py project/experiments/performance_budget.py
```

2. Full tests:

```bash
python -m pytest -q
```

3. Smoke baseline:

```bash
python -m project.experiments.smoke --config config.yaml
```

4. Scalability performance budget:

```bash
python -m project.experiments.performance_budget --config config.yaml --nodes 10 --tasks 100 --algorithms min-load,greedy --repeats 1 --topology ring --scenario static --max-runtime-seconds 1.0 --min-throughput 0.05 --max-pending-tasks 500
```

5. Final release QA harness (CLI/Web/Repro/Publication):

```bash
python -m project.experiments.release_qa --strict --output docs/baselines/release_qa_report.json
```

## 3. Reproducibility Artifacts

1. Repro check (`>=30` for publication statistics):

```bash
python -m project.experiments.run --config config.yaml --repro-check --repro-runs 30
```

2. Manifest replay for key runs:

```bash
python -m project.experiments.run --replay-manifest outputs/<exp>/<scenario>/<algorithm>/run_manifest.json --replay-runs 10
```

3. Integrity verification:

```bash
python -m project.experiments.verify_integrity --integrity-file outputs/<...>/artifact_integrity.json
```

4. Build appendix release bundle (manifest + zip):

```bash
python -m project.experiments.release_bundle --strict --output-dir outputs/release_candidate/bundle --bundle-name publication_appendix_bundle_rc
```

## 4. Publication Outputs

1. Publication study:

```bash
python -m project.experiments.run --config config.yaml --publication-study
```

2. Regenerate scalability baseline report:

```bash
python -m project.experiments.scalability_report --summary-csv outputs/sprint9-publication-ready/scalability-profile/scalability_summary.csv --output-json docs/baselines/scalability_baseline.json --output-md docs/baselines/scalability_baseline_report.md --scenario static --topology ring --nodes 10,50 --tasks 100,500 --algorithms round-robin,min-load,greedy
```

3. Confirm generated docs:

- `docs/baselines/scalability_baseline.json`
- `docs/baselines/scalability_baseline_report.md`

## 5. Release Sign-Off

- [ ] All required gates passed on local branch.
- [ ] CI workflow green for PR to `main`.
- [ ] Reproducibility artifacts archived.
- [ ] Final docs package updated.
- [ ] Sprint log updated with closure evidence.
