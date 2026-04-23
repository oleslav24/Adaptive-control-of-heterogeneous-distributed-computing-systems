# Experimental Multi-Agent Testbed

Sprint 7 LLM-agent layer for an experimental platform to study adaptive control of heterogeneous distributed computing systems.

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
```

Artifacts are saved under `outputs/<experiment>/<scenario>/<algorithm>/`:

- `summary.csv`
- `history.csv`
- `completed_tasks.csv`
- `scenario_events.csv`
- `intelligence_ab.csv` (for `--ab-intelligence`)
- `llm_ab.csv` (for `--ab-llm`)
- `metrics_timeseries.png`
- `node_loads.png`
- `outputs/<experiment>/run.log`

## Current scope (Sprint 7)

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
