# Sprint 11 - Quality Gates and Test Foundation

## Goal

Establish a reliable automated test foundation before deeper refactoring of large modules.

## Implemented in this increment

1. Unit tests for core domain model:
   - `tests/test_core_models.py`
2. Unit tests for scheduling heuristics:
   - `tests/test_algorithms_schedulers.py`
3. MAS integration test (message routing lifecycle):
   - `tests/test_simulation_mas.py`
4. Simulation loop integration test (minimal deterministic scenario):
   - `tests/test_simulation_loop.py`
5. Existing smoke baseline checks remain active in CI workflow:
   - `.github/workflows/smoke-baseline.yml`
6. Static analysis gate:
   - `ruff` config: `pyproject.toml`
   - `mypy` config: `mypy.ini`
7. Pre-commit hooks:
   - `.pre-commit-config.yaml`
8. Mutation-testing baseline harness:
   - `project/quality/mutation_baseline.py`
   - baseline report: `docs/baselines/mutation_baseline.json`

## Current quality gate commands

```bash
$env:PRE_COMMIT_HOME=".precommit_cache"  # PowerShell
python -m pre_commit install
python -m pre_commit install --hook-type pre-push
python -m pre_commit run --all-files
python -m ruff check --no-cache project tests
python -m mypy --no-sqlite-cache --cache-dir .mypy_cache_ci --follow-imports=skip project/core/models.py project/algorithms/schedulers.py project/simulation/context.py project/simulation/mas.py project/simulation/loop.py project/experiments/manifest.py project/experiments/smoke.py
python -m pytest -q
python -B -m project.experiments.smoke --config config.yaml
python -B -m project.quality.mutation_baseline --output docs/baselines/mutation_baseline.json
```

## Current results

1. `pytest`: 16 passed
2. smoke baseline: PASS (golden match)
3. mutation baseline: 6/6 killed, mutation score = 1.000

## Scope note

Sprint 11 status: complete (current planned scope).
