# Publication Docs Package (Sprint 18)

## 1. Experimental Setup and Architecture

The platform implements the system model:

- `S(t) = <N, E, T(t), S(t)>`
- control law: `X(t) = A(S(t))`

Architecture layers:

1. Simulation Core (`project/simulation`): nodes, tasks, queue, topology, scenarios, loop.
2. Multi-Agent System (`project/agents` + `project/simulation/mas.py`): monitoring, compute, network, QoS, optimization, prediction, LLM.
3. Algorithms and Intelligence (`project/algorithms`, `project/intelligence`, `project/llm`): scheduling policies, ML/ZNN signals, LLM policy guard.
4. Experiments and Publication (`project/experiments`): single/compare/batch/repro/publication/scalability/replay/QA workflows.
5. Metrics and Artifacts (`project/metrics` + manifests/integrity): CSV/JSON/plots + reproducibility metadata.

The release-candidate flow is profile-driven through:

- `configs/release_profiles/rc_single.yaml`
- `configs/release_profiles/rc_batch_strict.yaml`
- `configs/release_profiles/rc_publication.yaml`

Profiles are validated and locked via:

- `python -m project.experiments.release_profiles`
- output: `docs/baselines/release_profile_lock.json`

## 2. Compared Methods and Scenarios

Implemented comparison set:

- Baseline algorithms: `round-robin`, `min-load`, `greedy`
- MAS variants: `mas`, `hybrid-mas`, `mas-ml`, `mas-znn`
- LLM-assisted mode: `mas-llm`

Publication scenarios:

- Static load
- Dynamic load
- Peak load
- Node failure
- Heterogeneous tasks

Key publication experiments in code:

- E1 Scalability
- E2 Adaptivity
- E3 Robustness
- E4 Hybrid vs Classical
- E5 LLM vs Algorithmic

Primary metrics:

- `makespan`
- `avg_latency`
- `load_imbalance`

Secondary/advanced metrics:

- `sla_violations`
- `throughput`
- `resource_utilization`
- adaptivity/stability derivatives in publication summary

Statistical outputs include `mean`, `std`, and `95% CI` where applicable.

## 3. Threats to Validity

### 3.1 Internal Validity

- Threat: hidden nondeterminism across runs.
- Mitigation:
  - fixed seeds in configs/manifests;
  - replay mode with verification report;
  - artifact integrity checks (`sha256`, size).

- Threat: environment drift.
- Mitigation:
  - dependency/version capture in manifests;
  - smoke baseline and performance budget gates.

### 3.2 Construct Validity

- Threat: metrics not representing intended quality dimensions.
- Mitigation:
  - explicit metric taxonomy (primary/secondary/advanced);
  - hypothesis table contract checks (H1-H5);
  - summary validation in publication pipeline.

### 3.3 External Validity

- Threat: simulation may not fully represent production distributed systems.
- Mitigation:
  - heterogeneous node/task profiles;
  - multiple topologies/scenarios;
  - scalability sweeps across node/task sizes.

### 3.4 Conclusion Validity

- Threat: unstable claims due to low run count.
- Mitigation:
  - reproducibility mode with repeated runs (`>=30` for publication);
  - confidence intervals and variance outputs;
  - fixed release profiles for consistent comparison.

## 4. Release Evidence Map

Core release evidence artifacts:

- Profile lock: `docs/baselines/release_profile_lock.json`
- QA report: `docs/baselines/release_qa_report.json`
- Smoke baseline: `docs/baselines/smoke_baseline.json`
- Scalability baseline: `docs/baselines/scalability_baseline.json`
- Scalability report: `docs/baselines/scalability_baseline_report.md`
- Release checklist: `docs/release_candidate_checklist.md`
- Reproducibility SOP: `docs/reproducibility.md`

Bundle assembly command:

```bash
python -m project.experiments.release_bundle --strict --output-dir outputs/release_candidate/bundle --bundle-name publication_appendix_bundle_rc
```
