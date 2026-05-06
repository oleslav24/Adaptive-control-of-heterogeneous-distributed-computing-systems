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

## Current quality gate commands

```bash
python -m ruff check --no-cache project tests
python -m mypy --no-sqlite-cache --cache-dir .mypy_cache_ci --follow-imports=skip project/core/models.py project/algorithms/schedulers.py project/simulation/context.py project/simulation/mas.py project/simulation/loop.py project/experiments/manifest.py project/experiments/smoke.py
python -m pytest -q
python -B -m project.experiments.smoke --config config.yaml
```

## Current results

1. `pytest`: 13 passed
2. smoke baseline: PASS (golden match)

## Scope note

This is the first Sprint 11 increment.
Next steps in Sprint 11:

1. Expand integration tests around scenario events and batch runner invariants.
2. Add static analysis gates (ruff/mypy) with a pragmatic initial rule set.
