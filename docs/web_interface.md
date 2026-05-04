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
  - stop button for running job
- `/files?path=...`
  - workspace-safe file browser
  - previews for text and image artifacts
- `/download?path=...`
  - raw file download/inline delivery

## Safety

- Path access is restricted to the workspace root.
- Jobs are started with explicit command arrays (no shell interpolation).
- Logs are capped in memory to avoid unbounded growth.

## Notes

- This interface is intentionally lightweight (standard library HTTP server, no external web framework).
- Multiple jobs can run concurrently; each run is isolated as a subprocess.
- Use `Ctrl+C` in terminal to stop the web server.
