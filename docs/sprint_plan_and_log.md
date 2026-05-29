# Sprint Plan And Execution Log

Last updated: 2026-05-29 12:56:27 +07:00
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
| 13 | Experiments orchestration refactor | `project.experiments.run` decomposed into tested modules | Closed |
| 14 | Publication pipeline hardening | `publication.py` split + statistics validation | Closed |
| 15 | Reproducibility contract hardening | Strong manifests + deterministic replay checks | Closed |
| 16 | Web production hardening | Stable web UX, resilience, and diagnostics | Closed |
| 17 | Scalability and performance | Profiling-backed optimization and load envelopes | Closed |
| 18 | Release candidate for paper/monograph | Reproducible artifacts and final release checklist | Closed |
| 19 | Chapter 10 package pipeline | Chapter-ready tables/plots/report + CLI mode + tests | Closed |
| 20 | Paper bundle and chapter10 web orchestration | One-click paper bundle mode in CLI/Web with full tests | Closed |
| 21 | Carbon-aware optimization | Carbon-aware scheduler integrated into MAS/CLI/Web with tests | Closed |
| 22 | Carbon evidence pipeline | Publication/Chapter10 carbon trade-off evidence and reproducible study outputs | Closed |
| 23 | Carbon analytics and publication quality | Carbon-specific dashboards/summary contracts and interpretation layer for paper results | Closed |
| 24 | Literature RAG integration for evidence-backed analysis | Researcher/Web/Report evidence flow + quality gate + tests | Closed |
| 25 | Evidence-to-claim pipeline | Structured claims + evidence quality gates + Web/Report exposure | Closed |
| 26 | Monograph P0 smoke reproducibility | Smoke/golden/reproducibility stabilized without mechanical golden refresh | Closed |
| 27 | Monograph P1 publication calibration and method catalog | H2-H5 evidence calibrated, reports avoid unsupported claims, method catalog gaps resolved or explicit | Closed |
| 28 | Monograph P2 Chapter 10 package hardening | Chapter 10 artifacts/report/integrity are publication-ready and traceable | Closed |
| 29 | Monograph P2 decision trace observability | Per-run decision trace artifacts explain MAS/ML/ZNN/LLM policy decisions | Closed |
| 30 | Monograph P3 alignment and validity packaging | Explicit monograph-to-code traceability and bounded carbon scope in publication reports | Closed |
| 31 | Publication significance hardening | Hypotheses include deterministic significance/effect metadata with validation and tests | Closed |
| 32 | Agent control and quality-gate integration | Integrated `/agent-control` model+web+tests+docs, separated demo vs real-job signals | Closed |
| 33 | Agent control operational artifacts | Export control assessment artifacts for diagnostics and operational quality-gate traceability | Closed |
| 34 | Chapter10 operational control-health appendix | Add control-health appendix artifacts into chapter10/paper bundle pipeline with tests | Closed |
| 35 | Web job control-health artifact export | Auto-export `control_assessment.json` into run artifact directories for completed web jobs | Closed |
| 36 | Job-data control assessment surfacing | Expose control assessment in `/job-data` with artifact-first/fallback-runtime strategy | Closed |
| 37 | Job page control-assessment UX | Render control assessment signals directly on `/job` page from `/job-data` payload | Closed |
| 38 | Agent-control real-job summary hardening | Add aggregate assessment summary + latest terminal mode + docs/tests sync | Closed |
| 39 | Job page control-health UX hardening | Add compact control summary + evidence + deep-link from `/job` to `/agent-control` | In progress |

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
| 13 | Closed | 2026-05-14 16:12:14 +07:00 | merged via PR #18, merge commit `145a999` |
| 14 | Closed | 2026-05-14 16:12:14 +07:00 | merged via PR #18, merge commit `145a999` |
| 15 | Closed | 2026-05-14 16:12:14 +07:00 | merged via PR #18, merge commit `145a999` |
| 16 | Closed | 2026-05-15 10:39:06 +07:00 | merged via PR #19, merge commit `60b5101` |
| 17 | Closed | 2026-05-15 11:45:09 +07:00 | merged via PR #20, merge commit `ee1b2e1` |
| 18 | Closed | 2026-05-15 18:45:02 +07:00 | merged via PR #21, merge commit `4b7273d` |
| 19 | Closed | 2026-05-16 15:47:37 +07:00 | merged via PR #22, merge commit `f4b1a5c` |
| 20 | Closed | 2026-05-19 11:32:40 +07:00 | merged to `main`, tip `54186b9` (PRs #24, #25) |
| 21 | Closed | 2026-05-19 16:45:54 +07:00 | merged to `main`, merge commit `9f83c53` (PR #26) |
| 22 | Closed | 2026-05-19 17:24:58 +07:00 | merged to `main`, merge commit `83372a5` (PR #27) |
| 23 | Closed | 2026-05-20 15:13:57 +07:00 | merged to `main`, merge commit `ca916a6` (PR #28) |
| 24 | Closed | 2026-05-20 16:56:45 +07:00 | merged to `main`, merge commit `058cc61` (PR #29) |
| 25 | Closed | 2026-05-21 15:01:55 +07:00 | merged to `main`, merge commit `e364dfb` (PR #30) |
| 26 | Closed | 2026-05-22 10:38:44 +07:00 | merged to `main`, merge commit `6169ba2` (PR #32) |
| 27 | Closed | 2026-05-22 11:52:11 +07:00 | merged to `main`, merge commit `ec2d6f6` (PR #33) |
| 28 | Closed | 2026-05-22 14:43:09 +07:00 | merged to `main`, merge commit `762ca2a` (PR #34) |
| 29 | Closed | 2026-05-22 16:05:41 +07:00 | merged to `main`, merge commit `be1bae4` (PR #35) |
| 30 | Closed | 2026-05-22 16:58:18 +07:00 | merged to `main`, merge commit `f97d027` (PR #37) |
| 31 | Closed | 2026-05-27 13:52:06 +07:00 | merged to `main`, merge commit `c04c03e` (PR #40) |
| 32 | Closed | 2026-05-28 11:00:00 +07:00 | merged to `main`, merge commit `029117e` (PR #42) |
| 33 | Closed | 2026-05-28 12:20:10 +07:00 | merged to `main`, merge commit `0c297ab` (PR #43) |
| 34 | Closed | 2026-05-28 13:53:32 +07:00 | merged to `main`, merge commit `d8ca569` (PR #44) |
| 35 | Closed | 2026-05-28 17:01:13 +07:00 | merged to `main`, merge commit `6fb5a60` (PR #45) |
| 36 | Closed | 2026-05-28 17:31:08 +07:00 | merged to `main`, merge commit `64f7af7` (PR #46) |
| 37 | Closed | 2026-05-28 17:40:30 +07:00 | merged to `main`, merge commit `d8a21b0` (PR #47) |
| 38 | Closed | 2026-05-29 09:15:00 +07:00 | merged to `main`, merge commit `941d03a` (PR #48) |
| 39 | Open | n/a | in progress on branch `codex/sprint36-next` |

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
| 16.1 | Add resilient job supervision and timeout/error surfacing in UI | Done |
| 16.2 | Add server-side request validation and safer defaults | Done |
| 16.3 | Add diagnostics endpoints/log bundle export for failed runs | Done |
| 16.4 | Add web-level regression tests for key user flows | Done |

### Sprint 17 - Scalability and performance

| Task | Description | Status |
|---|---|---|
| 17.1 | Add profiling harness for large-scale runs (nodes/tasks sweeps) | Done |
| 17.2 | Optimize hot paths in simulation loop and metrics pipeline | Done |
| 17.3 | Add performance budgets and threshold checks in CI | Done |
| 17.4 | Publish scalability report templates and baseline numbers | Done |

### Sprint 18 - Release candidate for paper/monograph

| Task | Description | Status |
|---|---|---|
| 18.1 | Finalize release checklist and freeze config profiles | Done |
| 18.2 | Produce reproducible experiment bundle for publication appendix | Done |
| 18.3 | Final QA pass across CLI/Web/repro/publication flows | Done |
| 18.4 | Prepare final docs package (architecture, methods, threats to validity) | Done |

### Sprint 19 - Chapter 10 package pipeline

| Task | Description | Status |
|---|---|---|
| 19.1 | Restore `chapter10` experiment orchestrator module | Done |
| 19.2 | Add chapter tables/plots generators and artifacts | Done |
| 19.3 | Integrate `--chapter10` CLI mode and config section | Done |
| 19.4 | Add tests and chapter10 documentation | Done |

### Sprint 20 - Paper bundle and chapter10 web orchestration

| Task | Description | Status |
|---|---|---|
| 20.1 | Add `paper_bundle` experiment orchestrator (chapter10 + release zip) | Done |
| 20.2 | Integrate `--paper-bundle` mode into CLI dispatch/run handlers | Done |
| 20.3 | Integrate chapter10/paper-bundle into Web mode builder + validation | Done |
| 20.4 | Add mode-level tests (CLI/dispatch/handlers/paper_bundle/web) | Done |
| 20.5 | Add eGRID-driven energy/CO2 accounting in simulation and observability | Done |

### Sprint 21 - Carbon-aware optimization

| Task | Description | Status |
|---|---|---|
| 21.1 | Add `carbon-aware` algorithm to supported scheduler catalog and normalization | Done |
| 21.2 | Integrate carbon-aware scoring in `ComputeAgent` using eGRID node factors | Done |
| 21.3 | Pass per-node CO2 factors via simulation context and expose configurable carbon/load/bandwidth weights | Done |
| 21.4 | Integrate new algorithm into config/CLI/Web catalogs | Done |
| 21.5 | Add regression/unit tests and validate full suite | Done |

### Sprint 22 - Carbon evidence pipeline

| Task | Description | Status |
|---|---|---|
| 22.1 | Extend publication catalog with `carbon-aware` method and dedicated carbon/performance study (`E6`) | Done |
| 22.2 | Add Chapter10 carbon trade-off tables for publication-ready interpretation | Done |
| 22.3 | Add publication/chapter output visuals for carbon-performance frontier | Done |
| 22.4 | Add reproducible carbon-study presets (`>=30` seeds) and manifest contract | Done |
| 22.5 | Add regression/integration tests for Sprint 22 artifacts and CLI/Web wiring | Done |

### Sprint 23 - Carbon analytics and publication quality

| Task | Description | Status |
|---|---|---|
| 23.1 | Add carbon-study aggregate summary artifact with deltas vs baseline (`min-load`) | Done |
| 23.2 | Add publication/chapter report section with explicit carbon-performance interpretation text blocks | Done |
| 23.3 | Add web job page block for carbon-study key outcomes (CO2/task, CO2 total, latency trade-off) | Done |
| 23.4 | Add contract validation for carbon summary schema and numeric constraints | Done |
| 23.5 | Add regression/integration tests for Sprint 23 artifacts and UI exposure | Done |

### Sprint 24 - Literature RAG integration for evidence-backed analysis

| Task | Description | Status |
|---|---|---|
| 24.1 | Integrate local RAG evidence retrieval into researcher/web runtime payload flow | Done |
| 24.2 | Add publication and Chapter10 report sections with explicit local literature evidence references | Done |
| 24.3 | Add web job-page evidence block with query, citations, and quality indicator | Done |
| 24.4 | Add evidence quality gate (minimum source coverage + citation schema checks) with persisted gate artifacts | Done |
| 24.5 | Add regression/unit tests for Sprint 24 integrations and run full suite | Done |

### Sprint 25 - Evidence-to-claim pipeline

| Task | Description | Status |
|---|---|---|
| 25.1 | Add structured claim model (`claim_id`, `hypothesis`, `statement`, `evidence`, `confidence`, `status`) | Done |
| 25.2 | Generate runtime claims from researcher metrics + local RAG evidence | Done |
| 25.3 | Add claims quality gate v2 (sources per claim, retrieval score, H1-H5 coverage, insufficient evidence status) | Done |
| 25.4 | Add publication and Chapter10 `Evidence-backed Claims` sections plus `claims_report.json` artifacts | Done |
| 25.5 | Add Web job-page claims block with hypothesis/confidence/evidence filters | Done |
| 25.6 | Add regression/unit tests and validate full suite | Done |

### Sprint 26 - Monograph P0 smoke reproducibility

| Task | Description | Status |
|---|---|---|
| 26.1 | Run `python -m project.experiments.smoke --config config.yaml` and inspect fingerprint drift | Done |
| 26.2 | Compare current smoke payloads against `docs/baselines/smoke_baseline.json` before any golden update | Done |
| 26.3 | Isolate carbon-aware/E6 and new quick-study coverage from legacy smoke fingerprints | Done |
| 26.4 | Add tests for quick-study filtering and study-specific method overrides | Done |
| 26.5 | Re-run smoke, full pytest, commit, push, and prepare PR | Done |

### Sprint 27 - Monograph P1 publication calibration and method catalog

| Task | Description | Status |
|---|---|---|
| 27.1 | Run quick publication and Chapter 10 pipelines and inspect `hypotheses.csv` / report claims | Done |
| 27.2 | Identify whether H2-H5 gaps are caused by scenarios, metrics, implementation, or over-strong text | Done |
| 27.3 | Calibrate scenario/report behavior so unsupported hypotheses are clearly marked `not-supported` | Done |
| 27.4 | Resolve method catalog placeholders by implementing `max-min` or excluding placeholders from ready comparisons | Done |
| 27.5 | Add regression tests for calibrated hypotheses/report/method catalog behavior | Done |
| 27.6 | Run smoke/full pytest, commit, push, and prepare PR | Done |

### Sprint 28 - Monograph P2 Chapter 10 package hardening

| Task | Description | Status |
|---|---|---|
| 28.1 | Audit `--chapter10 --chapter10-quick` artifact completeness against P2 acceptance | Done |
| 28.2 | Add Chapter 10 report blocks for manifest linkage, integrity linkage, and threats to validity | Done |
| 28.3 | Add monograph chapter-to-artifact traceability table to Chapter 10 report | Done |
| 28.4 | Add regression tests for Chapter 10 report completeness and artifact links | Done |
| 28.5 | Run chapter10/publication integrity, smoke, full pytest, commit, push, and prepare PR | Done |

### Sprint 29 - Monograph P2 decision trace observability

| Task | Description | Status |
|---|---|---|
| 29.1 | Audit current simulation/MAS/LLM event history and identify trace insertion points | Done |
| 29.2 | Add compact `decision_trace.csv/json` schema and artifact writers | Done |
| 29.3 | Capture algorithm switches, prediction hints, ZNN node bias, LLM raw/clamped decisions, and applied policy | Done |
| 29.4 | Wire decision trace into run/publication/Chapter 10 manifests without polluting unrelated baselines | Done |
| 29.5 | Add tests for policy guard clamping, whitelist, invalid decision handling, and trace completeness | Done |
| 29.6 | Run targeted tests, smoke, full pytest, commit, push, and prepare PR | Done |

### Sprint 30 - Monograph P3 alignment and validity packaging

| Task | Description | Status |
|---|---|---|
| 30.1 | Add `docs/monograph_alignment.md` with chapter-to-code/artifact traceability matrix | Done |
| 30.2 | Add explicit carbon-scope boundary section in publication/chapter10 reports (`E6` as extension) | Done |
| 30.3 | Add explicit known gaps/future work statements linked to implementation status | Done |
| 30.4 | Add regression tests for new report sections and alignment doc references | Done |
| 30.5 | Run targeted tests + full pytest, commit, push, and prepare PR | Done (branch merged via PR #37) |

### Sprint 31 - Publication significance hardening

| Task | Description | Status |
|---|---|---|
| 31.1 | Add deterministic statistics helper module (permutation p-value, Cliff's delta, sample sanitization) | Done |
| 31.2 | Enrich H1-H5 evaluation with significance/effect metadata columns | Done |
| 31.3 | Extend hypotheses table validator for optional significance fields | Done |
| 31.4 | Add tests for statistics helpers and enriched hypothesis evaluation | Done |
| 31.5 | Run targeted + full pytest, update sprint log, prepare commit/PR | Done (commit+push completed on `codex/sprint31-next`) |
| 31.6 | Add explicit significance snapshot sections to publication/chapter10 markdown reports | Done |
| 31.7 | Add regression tests for significance snapshot sections and rerun smoke/pytest gates | Done |

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

## Sprint 13 Closure

Closed in `main` via PR #18 (merge commit `145a999`).

## Active Sprint Slice Log (Sprint 14)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 12:15:09 | 14.1 Extract method catalog and study spec builder from `publication.py` | OK (`publication_catalog` introduced, `publication.py` decoupled from catalog/spec construction) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:17:50 | 14.2 Add strict validation for summary statistics | OK (`publication_validation` added and enforced in pipeline) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:20:30 | 14.3 Add hypothesis table contract validation (H1-H5) | OK (H1-H5 schema/value checks added and enforced in pipeline) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:23:22 | 14.4 Add deterministic publication scenario fixtures | OK (`publication_scenarios` extracted + deterministic task/scenario fixture tests) | targeted + full pytest pass | current slice commit |
| 2026-05-14 12:25:06 | 14.5 Add publication artifact regression tests | OK (CSV/JSON/report artifact persistence checks added) | targeted + full pytest pass | current slice commit |

## Sprint 14 Closure

Closed in `main` via PR #18 (merge commit `145a999`).

## Active Sprint Slice Log (Sprint 15)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 12:27:09 | 15.1 Strengthen manifest schema and versioning | OK (`manifest_schema` + `manifest_schema_version` contract enforced and tested) | targeted + full pytest pass | current slice commit |
| 2026-05-14 15:18:06 | 15.2 Add deterministic replay command and verification report | OK (`--replay-manifest` mode added with validated replay + JSON verification report artifacts) | targeted + full pytest pass | current slice commit |
| 2026-05-14 15:48:12 | 15.3 Add artifact integrity checks (hashes for manifests/results) | OK (`artifact_integrity` module + SHA-256 reports integrated into single/batch/publication/repro/replay paths) | targeted + full pytest pass | current slice commit |
| 2026-05-14 16:00:45 | 15.4 Document reproducibility SOP end-to-end | OK (`docs/reproducibility.md` rewritten as Sprint 15 SOP with replay/integrity workflow) | docs + full pytest pass | current slice commit |

## Sprint 15 Closure

Closed in `main` via PR #18 (merge commit `145a999`).

## Active Sprint Slice Log (Sprint 16)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-14 16:24:57 | 16.1 Resilient job supervision + timeout/error surfacing in UI | OK (`JobManager` watchdog + timeout status/details + UI status details line + timeout form control) | targeted + full pytest pass | current slice commit |
| 2026-05-14 16:29:14 | 16.2 Server-side request validation and safer defaults | OK (strict `/run` validation for mode/config/timeout/seeds + bounded defaults with HTTP 400 feedback) | targeted + full pytest pass | current slice commit |
| 2026-05-14 16:33:48 | 16.3 Diagnostics endpoints and failed-run log bundle export | OK (`/job-diagnostics` JSON + `/job-bundle` zip export for failed/timeout/stopped jobs + UI link) | targeted + full pytest pass | current slice commit |
| 2026-05-14 16:36:48 | 16.4 Web-level regression tests for key user flows | OK (`/run` invalid request rejection + failed run diagnostics/bundle integration test) | targeted + full pytest pass (`142 passed`) | current slice commit |

## Sprint 16 Closure

Closed in `main` via PR #19 (merge commit `60b5101`).

## Active Sprint Slice Log (Sprint 17)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-15 10:49:11 | 17.1 Profiling harness for large-scale runs (nodes/tasks sweeps) | OK (`scalability-profile` mode added with deterministic synthetic workload/topology generation, sweep aggregation, and artifact persistence) | targeted + full pytest pass (`145 passed`) | current slice commit |
| 2026-05-15 11:32:04 | 17.2 Optimize hot paths in simulation loop and metrics pipeline | OK (`future_tasks` switched to deque, completed-task/deadline/latency aggregation moved to incremental updates, history dataframe flattening vectorized) | targeted + full pytest pass (`146 passed`) | current slice commit |
| 2026-05-15 11:36:28 | 17.3 Add performance budgets and threshold checks in CI | OK (`performance_budget` gate added and wired into GitHub Actions smoke workflow with runtime/throughput/pending thresholds) | targeted + full pytest pass (`149 passed`) | current slice commit |
| 2026-05-15 11:40:33 | 17.4 Publish scalability report template and baseline numbers | OK (`scalability_report` generator + baseline JSON/markdown artifacts + docs template) | targeted + full pytest pass (`152 passed`) | current slice commit |

## Sprint 17 Closure

Closed in `main` via PR #20 (merge commit `ee1b2e1`).

## Active Sprint Slice Log (Sprint 18)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-15 11:51:37 | 18.1 Finalize release checklist and freeze config profiles | OK (frozen release profiles added + deterministic `release_profile_lock.json` generator + release candidate checklist) | targeted + full pytest pass (`155 passed`) | current slice commit |
| 2026-05-15 17:43:14 | 18.2 Produce reproducible experiment bundle for publication appendix | OK (`release_bundle` CLI + manifest/ZIP builder + strict include validation + RC bundle generation command documented) | targeted + full pytest pass (`158 passed`) | current slice commit |
| 2026-05-15 18:31:48 | 18.3 Final QA pass across CLI/Web/repro/publication flows | OK (`release_qa` harness added, strict QA run persisted in `docs/baselines/release_qa_report.json`) | targeted + full pytest pass (`161 passed`) | current slice commit |
| 2026-05-15 18:34:23 | 18.4 Prepare final docs package (architecture, methods, threats to validity) | OK (`publication_docs_package.md` added and included into default release bundle set) | targeted + full pytest pass (`162 passed`) | current slice commit |

## Sprint 18 Closure

Closed in `main` via PR #21 (merge commit `4b7273d`).

## Active Sprint Slice Log (Sprint 19)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-16 15:45:15 | 19.1-19.4 Chapter 10 package pipeline (orchestrator + tables/plots + CLI + docs/tests) | OK (new chapter10 mode and artifacts implemented from clean `main`) | targeted + full pytest pass (`164 passed`) | current slice commit |

## Sprint 19 Closure

Closed in `main` via PR #22 (merge commit `f4b1a5c`).

## Active Sprint Slice Log (Sprint 20)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-18 12:25:34 | 20.1-20.4 Orchestration + CLI/Web wiring + tests for `paper-bundle` and `chapter10` | OK (mapped to Sprint 20 backlog items 20.1-20.4) | targeted tests + full pytest pass (`173 passed`) | `c565d23` |
| 2026-05-18 13:24:02 | 20.5 eGRID integration: node mapping + runtime energy/CO2 metrics + tests | OK (mapped to Sprint 20 backlog item 20.5) | targeted tests + full pytest pass (`175 passed`) | current slice commit |

## Sprint 20 Closure

Closed in `main` via PR #24 and PR #25 (tip merge commit `54186b9`).

## Active Sprint Slice Log (Sprint 21)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-19 11:32:40 | 21.1-21.5 Carbon-aware scheduler end-to-end (MAS + context + config/CLI/Web + tests) | OK (mapped to Sprint 21 backlog items 21.1-21.5) | targeted tests + full pytest pass (`178 passed`) | current slice commit |

## Sprint 21 Closure

Closed in `main` via PR #26 (merge commit `9f83c53`).

## Active Sprint Slice Log (Sprint 22)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-19 16:50:23 | 22.1-22.2 Publication catalog + Chapter10 carbon tradeoff tables (`carbon-aware`, `E6_carbon_vs_performance`) | OK (mapped to Sprint 22 backlog items 22.1-22.2) | targeted + full pytest pass (`181 passed`) | current slice commit |
| 2026-05-19 16:53:08 | 22.3 Carbon/performance frontier Chapter10 plot + plot regression tests + Matplotlib compatibility fix | OK (mapped to Sprint 22 backlog items 22.3, 22.5) | targeted + full pytest pass (`183 passed`) | current slice commit |
| 2026-05-19 17:01:15 | 22.4-22.5 Reproducible `carbon-study` mode (CLI/config/manifest) + Web wiring + coverage | OK (mapped to Sprint 22 backlog items 22.4-22.5) | targeted + full pytest pass (`186 passed`) | current slice commit |

## Sprint 22 Closure

Closed in `main` via PR #27 (merge commit `83372a5`).

## Active Sprint Slice Log (Sprint 23)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-19 17:24:58 | Sprint 22 closure recorded + Sprint 23 backlog opened | OK (process compliance and continuity) | docs only | current slice commit |
| 2026-05-19 17:28:50 | 23.1 Carbon summary artifact (`carbon_summary.csv/json`) with baseline deltas + regression tests | OK (mapped to Sprint 23 backlog items 23.1 and 23.5) | targeted + full pytest pass (`189 passed`) | current slice commit |
| 2026-05-19 17:32:14 | 23.2 Report interpretation sections for publication/chapter outputs + coverage updates | OK (mapped to Sprint 23 backlog items 23.2 and 23.5) | targeted + full pytest pass (`189 passed`) | current slice commit |
| 2026-05-19 17:43:17 | 23.3 Web job page carbon outcomes block + payload parsing from `carbon_summary.csv` + UI tests | OK (mapped to Sprint 23 backlog items 23.3 and 23.5) | targeted + full pytest pass (`190 passed`) | current slice commit |
| 2026-05-19 17:45:44 | 23.4 Carbon summary schema validation in publication pipeline + validation tests | OK (mapped to Sprint 23 backlog items 23.4 and 23.5) | targeted + full pytest pass (`192 passed`) | current slice commit |

## Sprint 23 Closure

Closed in `main` via PR #28 (merge commit `ca916a6`).

## Active Sprint Slice Log (Sprint 24)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-20 15:49:34 | 24.1-24.5 Literature evidence integration across researcher/web/reports + evidence quality gate + tests | OK (mapped to Sprint 24 backlog items 24.1-24.5) | targeted tests + full pytest pass (`198 passed`) | current slice commit |

## Sprint 24 Closure

Closed in `main` via PR #29 (merge commit `058cc61`).

## Active Sprint Slice Log (Sprint 25)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-21 14:53:17 | 25.1-25.6 Structured evidence-backed claims across runtime Web payloads and publication/chapter reports | OK (mapped to Sprint 25 backlog items 25.1-25.6) | targeted tests pass (`18 passed`), full pytest pass (`203 passed`) | current slice commit |

## Sprint 25 Closure

Closed in `main` via PR #30 (merge commit `e364dfb`).

## Active Sprint Slice Log (Sprint 26)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 10:34:10 | 26.1-26.5 P0 smoke baseline drift investigation and isolation | OK (mapped to monograph plan P0 smoke/golden/reproducibility) | targeted tests pass (`7 passed`), smoke PASS against golden, full pytest pass (`205 passed`) | current slice commit |

## Sprint 26 Closure

Closed in `main` via PR #32 (merge commit `6169ba2`).

## Active Sprint Slice Log (Sprint 27)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 10:55:35 | 27.1-27.6 P1 publication calibration + `max-min` method catalog gap closure | OK (mapped to monograph plan P1 hypotheses/scenario calibration + method catalog gaps) | targeted tests pass (`35 passed`), publication/chapter10 quick PASS, integrity PASS, smoke PASS, full pytest pass (`208 passed`) | current slice commit |

## Sprint 27 Closure

Closed in `main` via PR #33 (merge commit `ec2d6f6`).

## Active Sprint Slice Log (Sprint 28)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 11:52:11 | 28.1 Open Sprint 28 after Sprint 27 merge | OK (mapped to monograph plan P2 Chapter 10 package) | not run yet | pending |
| 2026-05-22 12:00:23 | 28.1-28.5 Chapter 10 package hardening: required artifact validation, report traceability, integrity coverage | OK (mapped to monograph plan P2 Chapter 10 package) | targeted tests pass (`7 passed`), chapter10 quick PASS, chapter10 integrity PASS, smoke PASS, full pytest pass (`208 passed`) | current slice commit |

## Sprint 28 Closure

Closed in `main` via PR #34 (merge commit `762ca2a`).

## Active Sprint Slice Log (Sprint 29)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 14:43:09 | 29.1 Open Sprint 29 after Sprint 28 merge | OK (mapped to monograph plan P2 decision trace observability) | not run yet | pending |
| 2026-05-22 14:59:43 | 29.1-29.6 Decision trace artifacts for MAS/ML/ZNN/LLM policy explainability | OK (mapped to monograph plan P2 decision trace observability) | targeted tests pass (`10 passed`), smoke PASS, publication quick PASS, Chapter10 quick PASS, integrity PASS, full pytest pass (`210 passed`) | current slice commit |

## Sprint 29 Closure

Closed in `main` via PR #35 (merge commit `be1bae4`).

## Active Sprint Slice Log (Sprint 30)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 16:25:22 | 30.1 Open Sprint 30 after Sprint 29 merge | OK (mapped to monograph plan P3 alignment and validity packaging) | not run yet | pending |
| 2026-05-22 16:31:25 | 30.1-30.4 Monograph alignment doc + publication/chapter10 scope boundaries + known gaps + web validation path-escape CI fix | OK (mapped to Sprint 30 backlog items 30.1-30.4, plus CI stability hotfix) | targeted tests pass (`14 passed`), full pytest pass (`210 passed`) | current slice commit |
| 2026-05-22 16:33:48 | 30.5 Reproducibility gate before PR | OK (pre-PR smoke gate for regression safety) | smoke PASS (`baseline match: true`) | current slice commit |
| 2026-05-22 16:35:51 | 30.5 Commit/push/PR attempt | Partial (commit + push completed; GitHub API PR creation blocked: `must be a collaborator`) | n/a | commit `d70c813`, branch `codex/sprint30-monograph-alignment` |

## Sprint 30 Closure

Closed in `main` via PR #37 (merge commit `f97d027`).

## Active Sprint Slice Log (Sprint 31)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-22 17:28:40 | 31.1-31.4 Deterministic significance layer for publication hypotheses + validator contract + tests | OK (mapped to Sprint 31 backlog items 31.1-31.4) | targeted tests pass (`10 passed`), full pytest pass (`214 passed`) | current slice commit |
| 2026-05-22 17:33:08 | 31.5 Smoke gate and baseline drift triage for publication fingerprint | OK (non-mechanical baseline refresh after payload diff verification) | smoke initial FAIL (publication fingerprint), payload diff verified intentional, smoke PASS after baseline refresh | current slice commit |
| 2026-05-22 17:36:06 | 31.5 Commit + push checkpoint | OK (Sprint 31 start slice persisted remotely) | n/a | commit `1151883` |
| 2026-05-27 13:46:12 | 31.6-31.7 Report significance snapshot integration + regression coverage refresh | OK (mapped to Sprint 31 backlog items 31.6-31.7) | targeted tests pass (`8 passed`), full pytest pass (`215 passed`), smoke PASS | commit `bd71412` |
| 2026-05-27 13:47:48 | 31.PR Finalize sprint branch and create one PR | Partial (branch is ready; GitHub API PR creation blocked: `must be a collaborator`) | n/a | branch `codex/sprint31-next` |

## Sprint 31 Closure

Closed in `main` via PR #40 (merge commit `c04c03e`).

### Sprint 32 - Agent control and quality-gate integration

| Task | Description | Status |
|---|---|---|
| 32.1 | Add pure Python controllability model (`project/web/agent_control.py`) with demo profile and deterministic status/metric recomputation | Done |
| 32.2 | Add `/agent-control` route + view modules integrated via dispatch/request handlers | Done |
| 32.3 | Add dashboard quick link and language propagation (`lang` query param) | Done |
| 32.4 | Add real-job assessment mode with `pass/fail/present/unknown` signals and artifact-based checks | Done |
| 32.5 | Add tests for model transitions, route rendering, dashboard/web wiring | Done |
| 32.6 | Update web and monograph alignment docs with demo-vs-real mapping | Done |
| 32.7 | Run full regression test suite and prepare sprint PR | Done |

## Active Sprint Slice Log (Sprint 32)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-27 15:10:43 | 32.1-32.6 Agent control integration (model + route/view + dashboard + docs) | OK (mapped to integration backlog and monograph alignment mapping) | targeted web/model suites pass (`26 passed`) | pending |
| 2026-05-27 15:13:32 | 32.7 Full regression gate before PR | OK (all acceptance tests and smoke baseline) | `python -m pytest -q` (`224 passed`), smoke PASS (`baseline match: true`) | pending |

## Sprint 32 Closure

Closed in `main` via PR #42 (merge commit `029117e`).

### Sprint 33 - Agent control operational artifacts

| Task | Description | Status |
|---|---|---|
| 33.1 | Export `control_assessment.json` for job diagnostics | Done |
| 33.2 | Include control assessment in diagnostics bundle ZIP | Done |
| 33.3 | Expose control assessment in `/job-diagnostics` API payload | Done |
| 33.4 | Add/refresh diagnostics tests for new artifact contract | Done |
| 33.5 | Update web docs and sprint log, run full regression | Done |

## Active Sprint Slice Log (Sprint 33)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 11:07:15 | 33.1-33.4 Diagnostics control-health artifact integration | OK (mapped to P4 operational artifact scope) | targeted suites pass (`12 passed`, `13 passed`) | commit `5ba5088` |
| 2026-05-28 11:07:15 | 33.5 Regression gate after integration | OK (full suite stable) | `python -m pytest -q` (`224 passed`) | commit `5ba5088` |
| 2026-05-28 12:20:10 | 33.PR Merge confirmation and sprint closure sync | OK (status reconciled with GitHub merge state) | n/a | merge `0c297ab` (PR #43) |

## Sprint 33 Closure

Closed in `main` via PR #43 (merge commit `0c297ab`).

### Sprint 34 - Chapter10 operational control-health appendix

| Task | Description | Status |
|---|---|---|
| 34.1 | Add reusable control-health builder for chapter10/paper artifacts | Done |
| 34.2 | Export `chapter10_control_health.json` and `chapter10_control_health.md` from chapter10 pipeline | Done |
| 34.3 | Update chapter10 report/manifest/integrity flow to include control-health appendix | Done |
| 34.4 | Add/refresh tests for chapter10 + control-health appendix contracts | Done |
| 34.5 | Update docs and run targeted/full regression before PR | Done |

## Active Sprint Slice Log (Sprint 34)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 12:20:10 | 34.1-34.3 Start control-health appendix integration in chapter10 pipeline | OK (mapped to P4 operational appendix scope, separated from H1-H5 metrics) | pending | pending |
| 2026-05-28 12:26:53 | 34.1-34.4 Control-health module + chapter10 integration + unit coverage | OK (control-health appendix integrated as operational artifact, not hypothesis metric) | targeted tests pass (`5 passed`), full pytest pass (`226 passed`) | current slice commit |
| 2026-05-28 12:26:53 | 34.5 Runtime validation + docs sync | OK (`chapter10-quick` run emits control-health appendix with stable package validation/integrity) | `python -m project.experiments.run --config config.yaml --chapter10 --chapter10-quick --chapter10-seeds 42,43 --log-level warning` PASS | current slice commit |
| 2026-05-28 12:28:51 | 34.PR Push + PR creation attempt | Partial (branch pushed, GitHub API PR creation blocked: `must be a collaborator`) | n/a | branch `codex/sprint34-control-health-appendix` |

## Sprint 34 Closure

Closed in `main` via PR #44 (merge commit `d8ca569`).

### Sprint 35 - Web job control-health artifact export

| Task | Description | Status |
|---|---|---|
| 35.1 | Export `control_assessment.json` into completed job artifact directories when output paths are available | Done |
| 35.2 | Append exported control artifact path to job log (`control_assessment_json: ...`) for web/UI discovery | Done |
| 35.3 | Add/refresh tests for job-level control artifact export behavior | Done |
| 35.4 | Update docs and sprint log, run targeted/full regression before PR | Done |

## Active Sprint Slice Log (Sprint 35)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 13:53:32 | 35.1-35.2 Start job-level control artifact export implementation | OK (extends operational control-health pipeline without mixing into algorithmic metrics) | pending | pending |
| 2026-05-28 13:54:59 | 35.1-35.4 Implementation + tests + docs | OK (web jobs now persist operational control assessment beside run artifacts when manifests/output paths exist) | targeted tests pass (`16 passed`), full pytest pass (`227 passed`) | current slice commit |
| 2026-05-28 13:55:55 | 35.PR Push + PR creation attempt | Partial (branch pushed, GitHub API PR creation blocked: `must be a collaborator`) | n/a | branch `codex/sprint35-web-control-health-job-export` |

## Sprint 35 Closure

Closed in `main` via PR #45 (merge commit `6fb5a60`).

### Sprint 36 - Job-data control assessment surfacing

| Task | Description | Status |
|---|---|---|
| 36.1 | Include `control_assessment` in `/job-data` payload | Done |
| 36.2 | Use exported `control_assessment_json` artifact when present, fallback to runtime assessment otherwise | Done |
| 36.3 | Add/refresh payload tests for artifact-first and fallback behavior | Done |
| 36.4 | Update docs and sprint log, run targeted/full regression before PR | Done |

## Active Sprint Slice Log (Sprint 36)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 17:01:13 | 36.1-36.2 Start `/job-data` control-assessment surfacing | OK (extends web observability path for operational control-health reuse) | pending | pending |
| 2026-05-28 17:03:04 | 36.1-36.4 `/job-data` control-assessment integration + tests + docs | OK (artifact-first payload with runtime fallback is implemented and regression-safe) | targeted tests pass (`20 passed`), full pytest pass (`229 passed`) | current slice commit |
| 2026-05-28 17:04:08 | 36.PR Push + PR creation attempt | Partial (branch pushed, GitHub API PR creation blocked: `must be a collaborator`) | n/a | branch `codex/sprint36-next` |

## Sprint 36 Closure

Closed in `main` via PR #46 (merge commit `64f7af7`).

### Sprint 37 - Job page control-assessment UX

| Task | Description | Status |
|---|---|---|
| 37.1 | Add control-assessment card to `/job` page layout | Done |
| 37.2 | Render per-component `pass/fail/present/unknown` signals and reasons from `/job-data` payload | Done |
| 37.3 | Add i18n labels and update tests for job page/payload integration | Done |
| 37.4 | Update docs and sprint log, run targeted/full regression (no PR per request) | Done |

## Active Sprint Slice Log (Sprint 37)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 17:29:47 | 37.1-37.3 Job page control-assessment UI wiring | OK (extends existing operational control-health observability in web UI without changing experiment metrics) | pending | pending |
| 2026-05-28 17:31:08 | 37.1-37.4 UI + i18n + tests + docs | OK (control assessment is now visible directly on `/job` and remains artifact-first from `/job-data`) | targeted tests pass (`19 passed`), full pytest pass (`229 passed`) | current slice commit |
| 2026-05-28 17:31:08 | 37.PR | Skipped by request (`без PR`) | n/a | branch `codex/sprint36-next` |

## Sprint 37 Closure

Closed in `main` via PR #47 (merge commit `d8a21b0`).

### Sprint 38 - Agent-control real-job summary hardening

| Task | Description | Status |
|---|---|---|
| 38.1 | Add aggregate control summary (`overall`, state counts, failing components) to real-job assessment payload | Done |
| 38.2 | Add `latest completed job` assessment mode in `/agent-control` | Done |
| 38.3 | Update route/model/payload tests for summary and latest-terminal behavior | Done |
| 38.4 | Update docs and sprint log, run targeted/full regression before sprint closure | Done |

## Active Sprint Slice Log (Sprint 38)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-28 17:36:10 | 38.1-38.2 Implement control summary and latest-terminal mode | OK (extends operational quality-gate observability and does not alter GRVS algorithmic metrics) | pending | pending |
| 2026-05-28 17:43:19 | 38.1-38.4 Tests + docs + sprint log sync | OK (real-job assessment now provides compact aggregate health view and deterministic latest completed-job selection) | targeted tests pass (`28 passed`), full pytest pass (`230 passed`) | current slice commit |

## Sprint 38 Closure

Closed in `main` via PR #48 (merge commit `941d03a`).

### Sprint 39 - Job page control-health UX hardening

| Task | Description | Status |
|---|---|---|
| 39.1 | Render compact control summary (`overall`, per-state counts, failing components) on `/job` | Done |
| 39.2 | Show control signal evidence in `/job` control assessment rows | Done |
| 39.3 | Add deep-link from `/job` to `/agent-control?assess=job&id=<job_id>` | Done |
| 39.4 | Update web docs and tests (`job page`, `integration`, `payload`) + full regression | Done |

## Active Sprint Slice Log (Sprint 39)

| Timestamp (UTC+07) | Slice | Plan check | Tests | Commit |
|---|---|---|---|---|
| 2026-05-29 12:31:25 | 39.1-39.3 Job page control assessment UX hardening | OK (keeps operational control-health separate from algorithmic performance metrics) | pending | pending |
| 2026-05-29 12:55:10 | 39.1-39.4 Tests + docs + regression gate | OK (`/job` now exposes summary + evidence + deep-link with backward-compatible summary fallback) | targeted tests pass (`21 passed`), full pytest pass (`230 passed`) | current slice commit |
