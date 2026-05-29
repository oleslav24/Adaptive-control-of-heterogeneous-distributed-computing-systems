# Web Interface Guide

## Goal

`project.web.app` provides a local browser-based console to:

- start experiments in all major modes,
- monitor run status and logs in real time,
- browse and preview generated artifacts in `outputs/`.

## Start

```bash
python -m project.web.app --host 127.0.0.1 --port 8080
```

Then open: `http://127.0.0.1:8080`

## Supported run modes

- `single`
- `compare`
- `batch`
- `publication`
- `ab-intelligence`
- `ab-llm`
- `repro-check`

The UI maps each mode to the existing CLI (`project.experiments.run`) and runs commands in background worker threads.

## Main screens

- `/` dashboard
  - language switcher `RUS/ENG` (query param `lang=ru|en`)
  - run form
  - compare algorithms and batch scenarios are selected via checkbox flags (not comma text)
  - active/recent jobs table
  - quick links to files and health check
- `/job?id=<job_id>`
  - command details
  - status (`queued/running/success/failed/stopped`)
  - live log stream
  - realtime charts from loop metrics (`latency`, `throughput`, `avg_load`, `queue/completed`)
  - inline line explanations under each chart:
    - color = sub-run
    - on `queue/completed`: solid = queue, dashed = completed
  - `ResearcherAgent` textual conclusions based on chart trends (localized RU/EN)
  - control assessment card with per-component `pass/fail/present/unknown` reasons and evidence (artifact-first, runtime fallback)
  - compact control summary (`overall`, per-state counts, failing components)
  - deep-link to `/agent-control?assess=job&id=<job_id>` for detailed assessment
  - stop button for running job
  - diagnostics payload includes `control_assessment` (operational quality-gate health)
  - `control_assessment` follows schema v2:
    - `control_assessment_schema = adaptive-testbed.web.control-assessment`
    - `control_assessment_schema_version = 2`
    - metadata: `generated_at_utc`, `source`
  - after terminal status (`success/failed/timeout/stopped`) web runner exports `control_assessment.json` near produced run artifacts (when manifest/output paths are available)
  - `/job-data` payload includes `control_assessment`; if exported artifact path is present in logs (`control_assessment_json: ...`), payload uses that file, otherwise it falls back to runtime assessment
- `/agent-control`
  - integrated controllability module (`Agent Control / Quality Gate`) with `lang=ru|en`
  - demo profile mirrors colleague stand logic as maintained Python model (`project.web.agent_control`)
  - demo controls: `run scenario`, `disable next`, `enable all`, `controlled state`, `reset`
  - deterministic status transitions: `STABLE -> WARNING -> CRITICAL -> CONTROLLED_STATE`
  - critical combo scenario: `autonomy + qgate + integrity` disabled => `CRITICAL`
  - controlled state freezes demo metrics in partial recovery band `[55..75]`
  - real-job assessment mode:
    - `demo` (no job),
    - `assess latest job`,
    - `assess latest completed job`,
    - `assess by job id`
  - real-job signals are reported as `pass/fail/present/unknown` and are separated from demo percentages
  - real-job panel includes aggregate summary (`overall`, per-state counts, failing components)
  - artifact-based checks include: manifests, integrity report, validation gates, decision trace, runtime logs
  - quick links from assessed job:
    - `/job?id=<job_id>`
    - `/job-diagnostics?id=<job_id>`
    - `/job-bundle?id=<job_id>` (only for `failed/timeout/stopped`)
- `/job-diagnostics?id=<job_id>`
  - includes:
    - `control_assessment` (runtime snapshot, schema v2)
    - `control_assessment_consistency` (runtime vs artifact comparison, when artifact exists)
    - `control_assessment_validation` (schema validation errors per source)
- `/files?path=...`
  - workspace-safe file browser
  - previews for text and image artifacts
- `/download?path=...`
  - raw file download/inline delivery

## Diagnostics bundle extension

- Failed/timeout/stopped job bundle (`/job-bundle`) now includes:
  - `diagnostics.json`
  - `diagnostics.log`
  - `control_assessment.json`
- `control_assessment.json` is an operational health artifact (policy/context/logging/iteration/qgate/autonomy/integrity signals as `pass/fail/present/unknown`).
- This artifact is not part of algorithmic efficiency metrics and should not be interpreted as GRVS performance evidence.

## Safety

- Path access is restricted to the workspace root.
- Jobs are started with explicit command arrays (no shell interpolation).
- Logs are capped in memory to avoid unbounded growth.

## Notes

- This interface is intentionally lightweight (standard library HTTP server, no external web framework).
- Multiple jobs can run concurrently; each run is isolated as a subprocess.
- Use `Ctrl+C` in terminal to stop the web server.
- Demo profile weights on `/agent-control` are synthetic and intended for conceptual validation only (not empirical GRVS metrics).
