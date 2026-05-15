# Scalability Baseline Report

Generated at (UTC): 2026-05-15T04:39:51.149863+00:00
Schema version: `sprint17-scalability-baseline-v1`

## Sweep Specification

- Scenario: `static`
- Topology: `ring`
- Nodes: `[10, 50]`
- Tasks: `[100, 500]`
- Algorithms: `['round-robin', 'min-load', 'greedy']`

## Summary Table

| nodes | tasks | algorithm | runtime_s | avg_latency | throughput | avg_load | pending | deadline_violations |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 10 | 100 | greedy | 0.007753 | 3.519 | 3.375 | 0.177 | 83.000 | 0.000 |
| 10 | 100 | min-load | 0.008577 | 3.708 | 3.000 | 0.224 | 86.000 | 0.000 |
| 10 | 100 | round-robin | 0.005857 | 3.141 | 8.875 | 0.227 | 39.000 | 0.000 |
| 10 | 500 | greedy | 0.029734 | 4.048 | 5.250 | 0.084 | 473.000 | 4.000 |
| 10 | 500 | min-load | 0.033883 | 4.190 | 5.250 | 0.107 | 473.000 | 7.000 |
| 10 | 500 | round-robin | 0.014953 | 3.722 | 13.500 | 0.518 | 407.000 | 0.000 |
| 50 | 100 | greedy | 0.030133 | 2.717 | 5.750 | 0.043 | 72.000 | 0.000 |
| 50 | 100 | min-load | 0.030336 | 2.905 | 5.250 | 0.029 | 76.000 | 0.000 |
| 50 | 100 | round-robin | 0.010149 | 2.670 | 11.375 | 0.142 | 27.000 | 0.000 |
| 50 | 500 | greedy | 0.105058 | 4.622 | 5.625 | 0.046 | 467.000 | 2.000 |
| 50 | 500 | min-load | 0.131533 | 4.568 | 5.500 | 0.028 | 468.000 | 2.000 |
| 50 | 500 | round-robin | 0.022974 | 3.271 | 40.125 | 0.548 | 191.000 | 0.000 |

## Winners By Scale Point

| nodes | tasks | winner | score |
|---:|---:|---|---:|
| 10 | 100 | round-robin | 2.643 |
| 10 | 500 | round-robin | 6.442 |
| 50 | 100 | round-robin | 1.803 |
| 50 | 500 | round-robin | 1.169 |

## Notes

- `runtime_seconds_mean` is machine-dependent and used as a relative baseline.
- Quality metrics are deterministic for fixed seeds/spec.
