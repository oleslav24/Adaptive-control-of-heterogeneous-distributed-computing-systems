# Experimental Multi-Agent Testbed

Sprint 0 skeleton for an experimental platform to study adaptive control of heterogeneous distributed computing systems.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --index-url https://pypi.org/simple
set MPLCONFIGDIR=.mplconfig  # cmd.exe
# or in PowerShell: $env:MPLCONFIGDIR=".mplconfig"
python -m project.experiments.run --config config.yaml
```

## Current scope (Sprint 0)

- Base project structure
- Core interfaces and domain models
- Empty simulation loop
- Config-based experiment startup
