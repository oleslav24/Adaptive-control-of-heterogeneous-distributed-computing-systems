# Experimental Multi-Agent Testbed

Sprint 1 simulation core for an experimental platform to study adaptive control of heterogeneous distributed computing systems.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --index-url https://pypi.org/simple
set MPLCONFIGDIR=.mplconfig  # cmd.exe
# or in PowerShell: $env:MPLCONFIGDIR=".mplconfig"
python -m project.experiments.run --config config.yaml
```

## Current scope (Sprint 1)

- Core system model (`Node`, `Task`, `Network`, `SystemState`)
- Task queue and time-based task release
- Baseline scheduling without agents
- Simulation loop: `generate_tasks -> assign_tasks -> update_state`
