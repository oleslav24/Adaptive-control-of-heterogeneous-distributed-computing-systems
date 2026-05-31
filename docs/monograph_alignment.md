# Monograph Alignment Matrix (v0.9.1)

Source monograph: `txt/monograph/v0.9.1.pdf` (metadata timestamp: `2026-05-20 18:34:20 +07`).

## Goal

This document maps monograph claims to concrete code modules and reproducible artifacts.
It is used as a traceability contract between the manuscript text and the implementation.

## Chapter-to-Code Traceability

| Monograph chapter | Scope in monograph | Code modules | Primary artifacts |
|---|---|---|---|
| Chapter 2 | Formal model of heterogeneous distributed system | `project/core/models.py`, `project/simulation/bootstrap.py`, `project/simulation/network.py` | `summary.csv`, `scenario_overview.csv` |
| Chapter 3 | System architecture and control loop | `project/simulation/loop.py`, `project/simulation/context.py`, `project/experiments/controller.py` | `manifest.json`, run history CSV/JSON |
| Chapter 4 | Multi-agent system design | `project/agents/*.py`, `project/simulation/mas.py` | `decision_trace.csv/json`, `scenario_overview.csv` |
| Chapter 5 | Scheduling and optimization methods | `project/algorithms/schedulers.py`, `project/experiments/publication_catalog.py` | `method_ranking.csv/json`, `hypotheses.csv/json` |
| Chapter 6 | Metrics and observability | `project/metrics/reporter.py`, `project/experiments/publication_validation.py`, `project/web/agent_control.py` | `summary.csv/json`, `scenario_calibration.csv/json`, plots, validation JSONs, web control-health assessment |
| Chapter 7 | ML and ZNN intelligence layer | `project/intelligence/ml.py`, `project/intelligence/znn.py`, `project/agents/prediction.py` | `hypotheses.csv/json` (H3), `decision_trace.csv/json` |
| Chapter 8 | LLM-assisted control with safety policy | `project/llm/prompt.py`, `project/llm/client.py`, `project/llm/policy.py`, `project/agents/llm.py`, `project/web/agent_control_routes.py`, `project/web/agent_control_views.py` | `hypotheses.csv/json` (H5), `claims_report.json`, `decision_trace.csv/json`, `/agent-control` policy-guard UI |
| Chapter 9 | Integrated architecture and orchestration | `project/simulation/loop.py`, `project/experiments/run.py`, `project/experiments/dispatch.py` | run and batch manifests, integrity JSON |
| Chapter 10 | Experimental evaluation and publication package | `project/experiments/publication.py`, `project/experiments/chapter10.py`, `project/experiments/chapter10_tables.py`, `project/experiments/chapter10_plots.py`, `project/experiments/control_health.py`, `project/experiments/quality_gate.py` | `chapter10_report.md`, `chapter10_control_health.json/md`, `chapter10_manifest.json`, `chapter10_artifact_integrity.json`, `quality_gate.json`, `scenario_calibration.csv/json`, publication package |

## Scope Boundaries

- Hypotheses `H1-H5` are evaluated from the publication baseline studies `E1-E5`.
- Carbon-aware study `E6` is an extension slice and must be interpreted separately from `H1-H5`.
- Quick mode is useful for smoke validation but not for strong scientific claims.
- `/agent-control` demo percentages are operational quality-gate indicators and are explicitly separated from experimental efficiency metrics.
- `chapter10_control_health.*` is an operational quality-gate appendix and must not be reported as algorithmic performance evidence.
- Real-job control assessment is summarized as operational states (`pass/fail/present/unknown`) and component evidence, not as GRVS performance metrics.
- Web control-health uses explicit schema contract `adaptive-testbed.web.control-assessment` v2 with source-aware consistency checks (runtime vs exported artifact).

## Agent Control Mapping

- `policy` -> `project.llm.policy.clamp_decision`, algorithm whitelist, decision-trace guard events.
- `context` -> run manifests (`run_manifest_json`, `publication_manifest_json`, `chapter10_manifest_json`) and reproducibility snapshots.
- `logging` -> runtime job log + observability artifacts (`history.csv/json`, `scenario_events.csv/json`, `decision_trace.csv/json`).
- `iteration` -> gate-oriented modes (`--smoke`, `--repro-check`, publication/chapter10 bundle workflow).
- `qgate` -> publication/chapter10 validation artifacts (`*_validation.json`, claims/evidence gate outputs) and unified contract `quality_gate.json`.
- `autonomy` -> LLM enable/disable flags, provider constraints, guarded action application.
- `integrity` -> `artifact_integrity.json` and CLI verification via `project.experiments.verify_integrity`.

## Known Gaps / Future Work

- Reinforcement learning is conceptual in monograph context and not implemented as a production-ready method family.
- `transport` and `abc` families remain placeholders unless explicitly implemented in future sprint slices.
- LLM experiments are reproducible with `mock` provider by default; real provider runs require separate configuration and are not equivalent baselines.
- Full production distributed deployment (real cluster/network stack) is out of current simulation scope.

## Verification Commands

```powershell
python -m project.experiments.smoke --config config.yaml
python -m pytest -q
python -m project.experiments.run --config config.yaml --publication-study --study-quick --study-seeds 42,43
python -m project.experiments.run --config config.yaml --chapter10 --chapter10-quick --chapter10-seeds 42,43
```

## Usage In Reports

- `publication_report.md` references this document for monograph traceability and scope boundaries.
- `chapter10_report.md` references this document and repeats threats-to-validity constraints for publication-safe interpretation.
