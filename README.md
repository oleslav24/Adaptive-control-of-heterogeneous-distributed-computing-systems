# Experimental Multi-Agent Testbed

Sprint 9 publication-ready module for an adaptive control platform targeting heterogeneous distributed computing systems.

Detailed reproducibility protocol: `docs/reproducibility.md`.
Publication pipeline protocol (E1-E5, H1-H5): `docs/experimental_pipeline.md`.
Codebase module map: `docs/codebase_modules.md`.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --index-url https://pypi.org/simple
set MPLCONFIGDIR=.mplconfig  # cmd.exe
# or in PowerShell: $env:MPLCONFIGDIR=".mplconfig"
python -m project.experiments.run --config config.yaml
python -m project.experiments.run --config config.yaml --algorithm greedy
python -m project.experiments.run --config config.yaml --compare
python -m project.experiments.run --config config.yaml --scenario peak-load
python -m project.experiments.run --config config.yaml --scenario node-failures
python -m project.experiments.run --config config.yaml --scenario heterogeneous-tasks
python -m project.experiments.run --config config.yaml --ab-intelligence
python -m project.experiments.run --config config.yaml --disable-intelligence
python -m project.experiments.run --config config.yaml --ab-llm
python -m project.experiments.run --config config.yaml --disable-llm
python -m project.experiments.run --config config.yaml --llm-provider mock
python -m project.experiments.run --config config.yaml --batch
python -m project.experiments.run --config config.yaml --batch --batch-runs 5
python -m project.experiments.run --config config.yaml --batch --batch-scenarios static,peak-load --batch-algorithms round-robin,min-load,greedy
python -m project.experiments.run --config config.yaml --repro-check --repro-runs 3
python -m project.experiments.run --config config.yaml --publication-study
python -m project.experiments.run --config config.yaml --publication-study --study-quick --study-seeds 42,43
python -m project.web.app --host 127.0.0.1 --port 8080
```

Web UI guide: `docs/web_interface.md`.

Artifacts are saved under `outputs/<experiment>/<scenario>/<algorithm>/`:

- `summary.csv`
- `history.csv`
- `completed_tasks.csv`
- `scenario_events.csv`
- `summary.json`
- `history.json`
- `completed_tasks.json`
- `scenario_events.json`
- `run_manifest.json`
- `intelligence_ab.csv` (for `--ab-intelligence`)
- `llm_ab.csv` (for `--ab-llm`)
- `repro_check.csv` (for `--repro-check`)
- `repro_check_manifest.json` (for `--repro-check`)
- `batch/batch_runs.csv` (for `--batch`)
- `batch/batch_summary.csv` (for `--batch`)
- `batch/batch_ranking.csv` (for `--batch`)
- `batch/batch_winners.csv` (for `--batch`)
- `batch/batch_manifest.json` (for `--batch`)
- `metrics_timeseries.{png,pdf,svg}`
- `node_loads.{png,pdf,svg}`
- `batch/batch_metric_latency.{png,pdf,svg}`
- `batch/batch_metric_throughput.{png,pdf,svg}`
- `batch/batch_metric_load.{png,pdf,svg}`
- `outputs/<experiment>/run.log`

Publication study artifacts (`--publication-study`) are saved under `outputs/<experiment>/publication/`:

- `raw_runs.csv` / `raw_runs.json`
- `summary.csv` / `summary.json`
- `hypotheses.csv` / `hypotheses.json` (H1-H5)
- `methods_catalog.csv` / `methods_catalog.json`
- `unsupported_methods.csv`
- `publication_manifest.json`
- `publication_report.md`
- `e1_scalability_makespan.{png,pdf,svg}`
- `e4_hybrid_vs_classical_latency_boxplot.{png,pdf,svg}`
- `e5_llm_vs_algorithmic_latency_boxplot.{png,pdf,svg}`
- `global_load_imbalance_boxplot.{png,pdf,svg}`

## Current scope (Sprint 9)

- Core system model (`Node`, `Task`, `Network`, `SystemState`)
- Task queue and time-based task release
- Baseline MAS with communication: `Monitoring`, `Compute`, `Network`, `QoS`, `Optimization`
- Agent messaging primitive: `agent.send(message)`
- Optimization agent and algorithm policy delivery to compute
- Algorithms: `round-robin`, `min-load`, `greedy`
- Config-driven algorithm switching and CLI comparison mode
- Metrics: `latency`, `throughput`, `load`
- Observability: logging, CSV export, matplotlib plots
- Scenarios: dynamic load, peak load, node failures, heterogeneous tasks
- Prediction agent with ML regression load forecast
- Simplified ZNN balancing module for node-level biasing
- Predictive integration into control loop and adaptive algorithm hinting
- LLM Agent: `state -> text`, prompt template, API integration (`auto/openai/mock`)
- LLM policy guard: strict action schema, algorithm whitelist, clamped node bias
- LLM integration into control via MAS messages (`llm_policy`, `llm_algorithm_hint`)
- Simulation loop: `generate_tasks -> agents.step(state) -> update_state`
- Experiment Runner: automatic batch matrix (`scenario x algorithm x repeat`)
- Batch comparison tables: aggregated mean/std metrics and scenario winners
- Reproducibility controls: fixed global seed per run and run/batch manifests
- Publication export: high-DPI plots with vector formats (`pdf`, `svg`)
- Reproducibility check mode: repeated run consistency verification (`--repro-check`)
- Publication study mode: E1-E5 pipeline + H1-H5 evaluation (`--publication-study`)
