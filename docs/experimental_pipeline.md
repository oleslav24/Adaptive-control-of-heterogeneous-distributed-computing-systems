# Experimental Research Pipeline (Publication Mode)

## 1. Goal

Quantitatively evaluate adaptive multi-agent control in heterogeneous distributed computing systems against classical, hybrid, intelligent, and LLM-assisted approaches.

## 2. Hypotheses (H1-H5)

- H1 Adaptivity: adaptive methods reduce latency and load imbalance.
- H2 Multi-agent architecture: MAS improves robustness and stability under node failures.
- H3 Intelligent methods: ML/ZNN improve decision quality under dynamic load.
- H4 Hybrid approach: hybrid control outperforms standalone baseline methods.
- H5 LLM agent: LLM-assisted control improves coordination/flexibility against purely algorithmic control.

The pipeline exports `hypotheses.csv` and `hypotheses.json` with per-hypothesis deltas and a boolean confirmation flag.

## 3. Experimental Model

- System model: `S(t) = <N, E, T(t), S(t)>`
- Control law: `X(t) = A(S(t))`
- Initialization API: `init_system(N, topology)` via `project.simulation`.

## 4. Compared Methods

Ready methods in current codebase:

- Baseline: Round-Robin, Min-Load, Greedy
- Multi-agent: MAS (No ML), MAS+ML, MAS+ZNN, Hybrid MAS
- LLM-based: MAS+LLM

Placeholders tracked in method catalog (for future extension):

- Transport (classical optimization)
- ABC
- Max-Min
- Hybrid ABC + Max-Min

## 5. Metrics

Primary:

- `makespan`
- `avg_latency`
- `load_imbalance`

Secondary:

- `sla_violations`
- `throughput`
- `resource_utilization`

Advanced:

- `adaptivity` (throughput delta / load delta)
- `stability_latency_var`
- `stability_throughput_var`

Statistical outputs:

- mean
- std
- 95% confidence interval (`ci95`)

## 6. Pipeline Steps

1. `init_system(N, topology)`
2. deterministic task generation per seed
3. method run: `X(t) = A(S(t))`
4. execution simulation
5. metrics collection
6. repeat over seeds

Default publication seeds in CLI: `42-71` (30 runs).

## 7. Key Experiments (E1-E5)

- E1 Scalability: node growth with corresponding task scale.
- E2 Adaptivity: peak-load scenario.
- E3 Robustness: node-failure scenario.
- E4 Hybrid vs Classical.
- E5 LLM vs Algorithmic.

## 8. Reproducibility

- Fixed seed per run.
- Full config snapshot in manifests.
- Dependency versions and git commit tracked in manifests.
- Exported artifacts in CSV + JSON + publication plots (`png/pdf/svg`).

## 9. Run Commands

Full publication pipeline:

```bash
python -m project.experiments.run --config config.yaml --publication-study
```

Quick smoke pipeline:

```bash
python -m project.experiments.run --config config.yaml --publication-study --study-quick --study-seeds 42,43
```

## 10. Output Layout

`outputs/<experiment>/publication/`:

- raw runs
- summarized statistics with CI
- hypothesis table
- methods catalog
- unsupported methods list
- publication manifest
- publication report
- scalability and boxplot figures in `png/pdf/svg`
