# Sprint Plan And Execution Log

Last updated: 2026-05-14 16:00:45 +07:00  
Timezone: Asia/Krasnoyarsk (UTC+07:00)

## Source Sprint Roadmap

| Sprint | Goal | Definition of Done (short) | Status |
|---|---|---|---|
| 0 | Preparation and architecture skeleton | Project bootstraps, empty simulation loop | Historical completed |
| 1 | Simulation core | Tasks execute, state updates each tick | Historical completed |
| 2 | Base MAS | Agents coordinate task distribution | Historical completed |
| 3 | Control algorithms | >=3 algorithms, configurable switching | Historical completed |
| 4 | Metrics and observability | Metrics, logs, CSV, plots | Historical completed |
| 5 | Dynamic scenarios | >=3 scenarios, adaptive reactions | Historical completed |
| 6 | Intelligent methods (ML/ZNN) | Forecast is used and improves metrics | Historical completed |
| 7 | LLM agent integration | LLM affects control and is compared vs algorithms | Historical completed |
| 8 | Experimental module | Batch experiment runner + comparison tables | Historical completed |
| 9 | Publication-level finish | Reproducibility and clean code baseline | Historical completed |
| 10 | Stabilization baseline | Smoke regression + manifest validation | Closed |
| 11 | Quality gates | Expanded tests + static checks + mutation baseline | Closed |
| 12 | Web modular refactor | Web app decomposition into tested modules | Closed |
| 13 | Experiments orchestration refactor | `project.experiments.run` decomposed into tested modules | In progress (slices complete, pending merge) |
| 14 | Publication pipeline hardening | `publication.py` split + statistics validation | In progress (slices complete, pending merge) |
| 15 | Reproducibility contract hardening | Strong manifests + deterministic replay checks | In progress |
| 16 | Web production hardening | Stable web UX, resilience, and diagnostics | Planned |
| 17 | Scalability and performance | Profiling-backed optimization and load envelopes | Planned |
| 18 | Release candidate for paper/monograph | Reproducible artifacts and final release checklist | Planned |

## Execution Guardrails (mandatory each slice)

1. Map slice to one or more sprint backlog items before coding.
2. Implement only one bounded slice per commit.
3. Run targeted tests, then full `python -m pytest -q`.
4. Update `Active Sprint Slice Log` in this file after each slice.
5. Close sprint only when all DoD items are done and merged.
6. Create/refresh PR when sprint is fully completed.

## Sprint Closure Register

| Sprint | Status | Closed at (UTC+07) | Evidence |
|---|---|---|---|
| 0 | Historical (not backfilled) | n/a | n/a |
| 1 | Historical (not backfilled) | n/a | n/a |
| 2 | Historical (not backfilled) | n/a | n/a |
| 3 | Historical (not backfilled) | n/a | n/a |
| 4 | Historical (not backfilled) | n/a | n/a |
| 5 | Historical (not backfilled) | n/a | n/a |
| 6 | Historical (not backfilled) | n/a | n/a |
| 7 | Historical (not backfilled) | n/a | n/a |
| 8 | Historical (not backfilled) | n/a | n/a |
| 9 | Historical (not backfilled) | n/a | n/a |
| 10 | Closed | 2026-05-06 18:30:02 +07:00 | commit `2426af1`, merged via PR #3 |
| 11 | Closed | 2026-05-06 19:38:10 +07:00 | commit `5a09403` |
| 12 | Closed | 2026-05-14 10:14:40 +07:00 | merged to `main` via PRs #10-#15, tip merge commit `c892939` |
| 13 | In progress | n/a | active branch `codex/sprint13-experiments-orchestration` |
| 14 | In progress | n/a | active branch `codex/sprint13-experiments-orchestration` (until Sprint 13 merge) |
| 15 | In progress | n/a | active branch `codex/sprint13-experiments-orchestration` |
| 16 | Planned | n/a | n/a |
| 17 | Planned | n/a | n/a |
| 18 | Planned | n/a | n/a |

## Detailed Sprint Backlog And Status

### Sprint 0 - Preparation and architecture

| Task | Description | Status |
|---|---|---|
| 0.1 | Create project structure (`core/agents/algorithms/simulation/experiments/metrics`) | Done (historical) |
| 0.2 | Define base interfaces: `Node`, `Task`, `Agent`, `SystemState` | Done (historical) |
| 0.3 | Add experiment configuration (`config.yaml`) | Done (historical) |
| 0.4 | Setup Python environment and `requirements.txt` | Done (historical) |

### Sprint 1 - Simulation core

| Task | Description | Status |
|---|---|---|
| 1.1 | Implement `Node` resources and load model | Done (historical) |
| 1.2 | Implement `Task` requirements and deadline model | Done (historical) |
| 1.3 | Implement network graph via `networkx` | Done (historical) |
| 1.4 | Implement task queue | Done (historical) |
| 1.5 | Implement `SystemState` | Done (historical) |
| 1.6 | Implement base loop (`generate -> assign -> update`) | Done (historical) |

### Sprint 2 - Base MAS

| Task | Description | Status |
|---|---|---|
| 2.1 | Implement base `Agent` class | Done (historical) |
| 2.2 | Implement `MonitoringAgent` | Done (historical) |
| 2.3 | Implement `ComputeAgent` | Done (historical) |
| 2.4 | Implement `NetworkAgent` | Done (historical) |
| 2.5 | Implement `QoSAgent` | Done (historical) |
| 2.6 | Implement agent communication (`agent.send(message)`) | Done (historical) |

### Sprint 3 - Control algorithms

| Task | Description | Status |
|---|---|---|
| 3.1 | Implement round-robin scheduler | Done (historical) |
| 3.2 | Implement min-load scheduler | Done (historical) |
| 3.3 | Implement greedy scheduler | Done (historical) |
| 3.4 | Implement `OptimizationAgent` | Done (historical) |
| 3.5 | Support algorithm switching via config | Done (historical) |

### Sprint 4 - Metrics and observability

| Task | Description | Status |
|---|---|---|
| 4.1 | Implement metrics: latency / throughput / load | Done (historical) |
| 4.2 | Implement logging | Done (historical) |
| 4.3 | Save results to CSV | Done (historical) |
| 4.4 | Add visualization via `matplotlib` | Done (historical) |

### Sprint 5 - Dynamics and scenarios

| Task | Description | Status |
|---|---|---|
| 5.1 | Dynamic load scenario | Done (historical) |
| 5.2 | Peak load scenario | Done (historical) |
| 5.3 | Node failure scenario | Done (historical) |
| 5.4 | Heterogeneous tasks scenario | Done (historical) |

### Sprint 6 - Intelligent methods (ML/ZNN)

| Task | Description | Status |
|---|---|---|
| 6.1 | Implement `PredictionAgent` | Done (historical) |
| 6.2 | Add simple regression model | Done (historical) |
| 6.3 | Add simplified ZNN module | Done (historical) |
| 6.4 | Integrate intelligence output into control | Done (historical) |

### Sprint 7 - LLM agent integration

| Task | Description | Status |
|---|---|---|
| 7.1 | Convert state to text payload | Done (historical) |
| 7.2 | Add prompt template | Done (historical) |
| 7.3 | Integrate with LLM API client | Done (historical) |
| 7.4 | Generate control decisions from LLM | Done (historical) |
| 7.5 | Add action policy guard / clamping | Done (historical) |

### Sprint 8 - Experimental module

| Task | Description | Status |
|---|---|---|
| 8.1 | Implement experiment runner | Done (historical) |
| 8.2 | Implement batch execution | Done (historical) |
| 8.3 | Implement algorithm comparison | Done (historical) |
| 8.4 | Implement consolidated result output | Done (historical) |

### Sprint 9 - Publication-level finalization

| Task | Description | Status |
|---|---|---|
| 9.1 | Documentation baseline | Done (historical) |
| 9.2 | Seed fixation and reproducibility practices | Done (historical) |
| 9.3 | Result export pathways | Done (historical) |
| 9.4 | Publication-ready plotting profiles | Done (historical) |

### Sprint 10 - Stabilization baseline

| Task | Description | Status |
|---|---|---|
| 10.1 | Smoke runner for main execution modes | Done |
| 10.2 | Golden smoke baseline snapshots | Done |
| 10.3 | Manifest schema validation | Done |
| 10.4 | CI smoke workflow | Done |

### Sprint 11 - Quality gates

| Task | Description | Status |
|---|---|---|
| 11.1 | Expand unit and integration test coverage | Done |
| 11.2 | Add static gates (`ruff`, `mypy`) | Done |
| 11.3 | Add pre-commit hooks | Done |
| 11.4 | Add mutation baseline harness | Done |

### Sprint 12 - Web modular refactor

| Task | Description | Status |
|---|---|---|
| 12.1 | Split large `project/web/app.py` into route/view/helper modules | Done |
| 12.2 | Add unit tests for extracted modules | Done |
| 12.3 | Add end-to-end web flow integration tests | Done |
| 12.4 | Close sprint in governance log | Done |

### Sprint 13 - Experiments orchestration refactor (next)

| Task | Description | Status |
|---|---|---|
| 13.1 | Extract CLI parser/schema from `project/experiments/run.py` | Done |
| 13.2 | Extract run mode dispatch table and handlers | Done |
| 13.3 | Split single/compare execution paths into dedicated modules | Done |
| 13.4 | Split batch/repro/AB/publication mode handlers | Done |
| 13.5 | Add integration tests per mode + update docs | Done |

### Sprint 14 - Publication pipeline hardening

| Task | Description | Status |
|---|---|---|
| 14.1 | Decompose `project/experiments/publication.py` into cohesive modules | Done |
| 14.2 | Add strict validation for statistical outputs (mean/std/CI) | Done |
| 14.3 | Add hypothesis result contract checks (H1-H5) | Done |
| 14.4 | Add deterministic fixtures for publication scenarios | Done |
| 14.5 | Add regression tests for publication artifacts | Done |

### Sprint 15 - Reproducibility contract hardening

| Task | Description | Status |
|---|---|---|
| 15.1 | Strengthen run/batch/publication manifest schema and versioning | Done |
| 15.2 | Add deterministic replay command and verification report | Done |
| 15.3 | Add artifact integrity checks (hashes for manifests/results) | Done |
| 15.4 | Document reproducibility SOP end-to-end | Done |

### Sprint 16 - Web production hardening

| Task | Description | Status |
|---|---|---|
| 16.1 | Add resilient job supervision and timeout/error surfacing in UI | Planned |
| 16.2 | Add server-side request validation and safer defaults | Planned |
| 16.3 | Add diagnostics endpoints/log bundle export for failed runs | Planned |
| 16.4 | Add web-level regression tests for key user flows | Planned |

### Sprint 17 - Scalability and performance

| Task | Description | Status |
|---|---|---|
| 17.1 | Add profiling harness for large-scale runs (nodes/tasks sweeps) | Planned |
| 17.2 | Optimize hot paths in simulation loop and metrics pipeline | Planned |
| 17.3 | Add performance budgets and threshold checks in CI | Planned |
| 17.4 | Publish scalability report templates and baseline numbers | Planned |

### Sprint 18 - Release candidate for paper/monograph

| Task | Description | Status |
|---|---|---|
| 18.1 | Finalize release checklist and freeze config profiles | Planned |
| 18.2 | Produce reproducible experiment bundle for publication appendix | Planned |
| 18.3 | Final QA pass across CLI/Web/repro/publication flows | Planned |
| 18.4 | Prepare final docs package (architecture, methods, threats to validity) | Planned |

## Active Sprint Slice Log (Sprint 12)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-13 18:24:13 | Extract job page renderer | OK (modular decomposition) | full pytest pass | `3b463e4` |
| 2026-05-13 18:29:17 | Extract run start/stop routes | OK (route-level split) | full pytest pass | `0ec6c0a` |
| 2026-05-13 18:46:44 | Extract dashboard and job page routes | OK (route-level split) | full pytest pass | `04ff82f` |
| 2026-05-13 18:52:54 | Add dispatch table and simplify handler | OK (controller thinning) | full pytest pass | `b1bc6ab` |
| 2026-05-13 18:59:15 | Extract top-level request orchestration | OK (controller thinning) | full pytest pass | `d6cd62c` |
| 2026-05-13 19:10:03 | Add explicit sprint plan/log governance file | OK (process compliance) | docs only | `920472f` |
| 2026-05-14 09:57:53 | Add end-to-end web integration tests (critical routes + job lifecycle) | OK (DoD closure coverage) | targeted + full pytest pass | `b186445` |

## Active Sprint Slice Log (Sprint 13)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 11:18:42 | 13.1 Extract CLI parser/schema from `run.py` | OK (parser extracted to dedicated module) | targeted + full pytest pass | current slice commit |
| 2026-05-14 11:24:36 | 13.2 Extract run mode dispatch table and handlers | OK (main dispatch chain replaced by mode table) | targeted + full pytest pass | current slice commit |
| 2026-05-14 11:29:15 | 13.3 Split single/compare execution paths into dedicated modules | OK (`mode_single_compare` + shared `common` helpers extracted) | targeted + full pytest pass | current slice commit |
| 2026-05-14 11:33:12 | 13.4 Split batch/repro/AB/publication mode handlers | OK (`mode_advanced` extracted and wired into dispatcher) | targeted + full pytest pass | current slice commit |
| 2026-05-14 11:35:10 | 13.5 Add integration tests per mode + update docs | OK (handler wiring tests added for all run modes) | targeted + full pytest pass | current slice commit |

## Remaining Work To Close Sprint 13

1. Create/refresh PR from `codex/sprint13-experiments-orchestration` to `main`.
2. Merge PR to `main`.
3. Update `Sprint Closure Register` row for Sprint 13 with close timestamp and merge evidence.

## Active Sprint Slice Log (Sprint 14)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 12:15:09 | 14.1 Extract method catalog and study spec builder from `publication.py` | OK (`publication_catalog` introduced, `publication.py` decoupled from catalog/spec construction) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:17:50 | 14.2 Add strict validation for summary statistics | OK (`publication_validation` added and enforced in pipeline) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:20:30 | 14.3 Add hypothesis table contract validation (H1-H5) | OK (H1-H5 schema/value checks added and enforced in pipeline) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:23:22 | 14.4 Add deterministic publication scenario fixtures | OK (`publication_scenarios` extracted + deterministic task/scenario fixture tests) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:25:06 | 14.5 Add publication artifact regression tests | OK (CSV/JSON/report artifact persistence checks added) | targeted + full pytest pass | current slice commit |

## Remaining Work To Close Sprint 14

1. Create/refresh PR from `codex/sprint13-experiments-orchestration` to `main`.
2. Merge PR to `main`.
3. Update `Sprint Closure Register` row for Sprint 14 with close timestamp and merge evidence.

## Active Sprint Slice Log (Sprint 15)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 12:27:09 | 15.1 Strengthen manifest schema and versioning | OK (`manifest_schema` + `manifest_schema_version` contract enforced and tested) | targeted + full pytest pass | current slice commit |
| 2026-05-14 15:18:06 | 15.2 Add deterministic replay command and verification report | OK (`--replay-manifest` mode added with validated replay + JSON verification report artifacts) | targeted + full pytest pass | current slice commit |
| 2026-05-14 15:48:12 | 15.3 Add artifact integrity checks (hashes for manifests/results) | OK (`artifact_integrity` module + SHA-256 reports integrated into single/batch/publication/repro/replay paths) | targeted + full pytest pass | current slice commit |
| 2026-05-14 16:00:45 | 15.4 Document reproducibility SOP end-to-end | OK (`docs/reproducibility.md` rewritten as Sprint 15 SOP with replay/integrity workflow) | docs + full pytest pass | current slice commit |

## Remaining Work To Close Sprint 15

1. Create/refresh PR from `codex/sprint13-experiments-orchestration` to `main`.
2. Merge PR to `main`.
3. Update `Sprint Closure Register` row for Sprint 15 with close timestamp and merge evidence.
