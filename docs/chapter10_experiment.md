# Chapter 10 Experimental Package

## Purpose

`chapter10` mode packages publication pipeline outputs into chapter-ready artifacts:

- normalized tables;
- publication-quality plots;
- compact markdown report;
- reproducibility manifest + integrity file.

The mode is intended for direct use in Chapter 10 text preparation.

## Run

```bash
python -m project.experiments.run --config config.yaml --chapter10
```

Quick run:

```bash
python -m project.experiments.run --config config.yaml --chapter10 --chapter10-quick --chapter10-seeds 42,43
```

## Config

`config.yaml` supports a dedicated section:

```yaml
chapter10:
  enabled: false
  seeds: [42, 43, 44, 45, 46]
  quick: false
  save_plots: true
```

CLI flags override config values.

## Outputs

Artifacts are written to:

`outputs/<experiment>/chapter10/`

Main files:

- `method_ranking.csv` / `method_ranking.json`
- `scenario_overview.csv` / `scenario_overview.json`
- `hypotheses.csv` / `hypotheses.json`
- `chapter10_report.md`
- `chapter10_control_health.json` / `chapter10_control_health.md`
- `chapter10_manifest.json`
- `chapter10_artifact_integrity.json`

When plotting is enabled:

- `chapter10_scalability_latency.{png,pdf,svg}`
- `chapter10_scenario_throughput.{png,pdf,svg}`
- `chapter10_method_latency_boxplot.{png,pdf,svg}`

## Notes

- `chapter10` internally reuses `run_publication_pipeline`.
- Source publication artifacts are referenced in Chapter 10 manifest payload (`publication_*` keys).
- `chapter10_control_health.*` is an operational quality-gate appendix (policy/context/logging/iteration/qgate/autonomy/integrity signals), not a replacement for algorithmic H1-H5 effectiveness metrics.
