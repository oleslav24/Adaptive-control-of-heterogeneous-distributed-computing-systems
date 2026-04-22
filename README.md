# Experimental Multi-Agent Testbed

Sprint 4 metrics and observability for an experimental platform to study adaptive control of heterogeneous distributed computing systems.

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
```

Artifacts are saved under `outputs/<experiment>/<algorithm>/`:

- `summary.csv`
- `history.csv`
- `completed_tasks.csv`
- `metrics_timeseries.png`
- `node_loads.png`
- `outputs/<experiment>/run.log`

## Current scope (Sprint 4)

- Core system model (`Node`, `Task`, `Network`, `SystemState`)
- Task queue and time-based task release
- Baseline MAS with communication: `Monitoring`, `Compute`, `Network`, `QoS`, `Optimization`
- Agent messaging primitive: `agent.send(message)`
- Optimization agent and algorithm policy delivery to compute
- Algorithms: `round-robin`, `min-load`, `greedy`
- Config-driven algorithm switching and CLI comparison mode
- Metrics: `latency`, `throughput`, `load`
- Observability: logging, CSV export, matplotlib plots
- Simulation loop: `generate_tasks -> agents.step(state) -> update_state`
