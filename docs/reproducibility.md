# Reproducibility Guide (Sprint 9)

## Goal

Provide a stable, publication-grade process to reproduce simulation results, export tables, and regenerate figures.

## Environment

1. Create and activate virtual environment.
2. Install dependencies from `requirements.txt`.
3. Use a fixed configuration file (`config.yaml`) with a fixed `simulation.seed`.

## Core Commands

Single run:

```bash
python -m project.experiments.run --config config.yaml
```

Batch experiments:

```bash
python -m project.experiments.run --config config.yaml --batch --batch-runs 5
```

Reproducibility check:

```bash
python -m project.experiments.run --config config.yaml --repro-check --repro-runs 3
```

## Reproducibility Signals

Each run exports:

- `run_manifest.json` with:
  - `git_commit`
  - `git_dirty`
  - dependency versions
  - CLI arguments
  - full config snapshot
- deterministic `seed` in config (`simulation.seed`)
- consistent CSV/JSON outputs for metrics

Batch mode additionally exports:

- `batch_manifest.json`
- `batch_runs.csv` / `batch_summary.csv` / `batch_ranking.csv` / `batch_winners.csv`
- publication plots in `png`, `pdf`, and `svg`

## Publication Figures

Publication profile is controlled by `observability`:

- `plot_profile: publication`
- `plot_dpi: 300`
- `plot_formats: [png, pdf, svg]`

This yields raster and vector outputs suitable for monographs and paper submissions.

## Notes

- For strict algorithm comparison, use `--batch` without `--batch-keep-adaptive`; this disables adaptive intelligence and LLM during batch ranking.
- If external LLM API is enabled, deterministic reproducibility may degrade; use `--disable-llm` or provider `mock` for stable reruns.
