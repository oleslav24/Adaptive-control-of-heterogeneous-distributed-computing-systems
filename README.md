# Experimental Multi-Agent Testbed

Sprint 2 baseline multi-agent system for an experimental platform to study adaptive control of heterogeneous distributed computing systems.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --index-url https://pypi.org/simple
set MPLCONFIGDIR=.mplconfig  # cmd.exe
# or in PowerShell: $env:MPLCONFIGDIR=".mplconfig"
python -m project.experiments.run --config config.yaml
```

## Current scope (Sprint 2)

- Core system model (`Node`, `Task`, `Network`, `SystemState`)
- Task queue and time-based task release
- Baseline MAS with communication: `Monitoring`, `Compute`, `Network`, `QoS`
- Agent messaging primitive: `agent.send(message)`
- Simulation loop: `generate_tasks -> agents.step(state) -> update_state`
