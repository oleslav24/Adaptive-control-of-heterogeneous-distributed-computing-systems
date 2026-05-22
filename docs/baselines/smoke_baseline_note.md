# Smoke Baseline Contract

Last updated: 2026-05-21 15:47:57 +07:00

## Sprint 26 Investigation

`python -m project.experiments.smoke --config config.yaml` reported fingerprint drift after the carbon-aware/E6 extension:

- `compare` included `carbon-aware` from the mutable runtime config.
- quick `publication` included `E6_carbon_vs_performance` and new E1 method coverage.

The drift was caused by an intentional extension, not by nondeterministic execution. The golden baseline was not refreshed mechanically. Instead, smoke mode now keeps a stable legacy contract:

- compare smoke uses `round-robin`, `min-load`, `greedy`;
- publication smoke is scoped to E1-E5;
- publication smoke excludes `carbon-aware` and E6;
- E1 smoke keeps the original method set used by the golden snapshot.

Carbon-aware/E6 remains available in publication and Chapter 10 pipelines, but it is separated from the legacy smoke fingerprint so older reproducibility checks remain comparable.

