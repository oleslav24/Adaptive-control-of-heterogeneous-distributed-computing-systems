# Sprint 10 - Stabilization Baseline

## Goal

Lock deterministic baseline behavior for four execution modes before deeper refactoring:

1. single
2. compare
3. batch
4. publication (quick)

## Implemented Deliverables

1. Smoke baseline runner: `project/experiments/smoke.py`
2. Golden snapshot file: `docs/baselines/smoke_baseline.json`
3. Manifest schema validation:
   - `validate_run_manifest(...)`
   - `validate_run_manifest_file(...)`
   in `project/experiments/manifest.py`
4. CI workflow: `.github/workflows/smoke-baseline.yml` (`pytest` + smoke baseline)

## Commands

Run baseline and compare against golden:

```bash
python -m project.experiments.smoke --config config.yaml
```

Regenerate golden from current code:

```bash
python -m project.experiments.smoke --config config.yaml --update-golden
```

Optional smoke matrix tuning:

```bash
python -m project.experiments.smoke --config config.yaml --batch-scenarios static,dynamic-load --batch-algorithms round-robin,min-load,greedy --batch-runs 1 --publication-seeds 42,43
```

## Pass/Fail Logic

Smoke check returns `PASS` when:

1. all mode-case manifests are valid (`run_manifest`/`batch_manifest`/`publication_manifest`)
2. fingerprints for all smoke cases match the golden file

Smoke check returns `FAIL` when:

1. any required manifest field is missing or malformed
2. any case fingerprint differs from golden

## Notes

1. Golden comparison uses deterministic payload fingerprints and ignores timestamp noise.
2. Smoke profile disables plot generation for speed.
3. LLM provider for smoke is forced to `mock` to avoid external nondeterminism.
