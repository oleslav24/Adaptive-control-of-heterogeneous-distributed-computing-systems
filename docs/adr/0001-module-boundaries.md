# ADR 0001 — Module Boundaries for Refactoring

## Status

Accepted (Sprint 10 baseline)

## Context

The project already implements simulation, MAS, algorithms, publication pipeline, and web control.
Before structural refactoring, module boundaries must be explicitly fixed to avoid accidental coupling regressions.

## Decision

Keep and enforce these package-level boundaries:

1. `project.core`
   - domain model (`Node`, `Task`, `SystemState`)
   - config schema
   - base agent contract
2. `project.simulation`
   - simulation loop, queue, scenario injection, MAS orchestration glue
   - can depend on `core`, `agents`, `algorithms`, `intelligence`, `llm`
3. `project.agents`
   - concrete agent implementations only
   - no direct persistence/export logic
4. `project.algorithms`
   - pure scheduling strategy logic
   - no knowledge of CLI/Web
5. `project.intelligence`
   - ML/ZNN utilities
   - no HTTP/CLI concerns
6. `project.llm`
   - prompt/client/policy guard
   - no simulation orchestration
7. `project.metrics`
   - summarization/export/plots
   - no decision-making logic
8. `project.experiments`
   - run orchestration (single/batch/publication/smoke)
9. `project.web`
   - HTTP UI and job management only
   - calls experiment layer, does not own domain logic

## Refactoring Guardrails

1. New feature code must enter the owning package above, not `run.py`/`web/app.py` directly.
2. Cross-package calls should go through stable helper functions instead of inline duplication.
3. Manifest schema is part of reproducibility contract; field removals are breaking changes.
4. Any change to run-mode behavior must pass smoke baseline:
   - `single`
   - `compare`
   - `batch`
   - `publication (quick)`

## Consequences

Positive:

1. Lower risk during large decomposition of `project/web/app.py` and `project/experiments/run.py`.
2. Clear ownership zones for Sprint 11+ work (tests, quality gates, security hardening).

Trade-off:

1. Slightly more boilerplate at package boundaries.
