# Scalability Report Template

Generated at (UTC): `{{created_at_utc}}`  
Schema version: `{{schema_version}}`

## Sweep Specification

- Scenario: `{{scenario}}`
- Topology: `{{topology}}`
- Nodes: `{{node_counts}}`
- Tasks: `{{task_counts}}`
- Algorithms: `{{algorithms}}`

## Summary Table

| nodes | tasks | algorithm | runtime_s | avg_latency | throughput | avg_load | pending | deadline_violations |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| {{node_count}} | {{task_count}} | {{algorithm}} | {{runtime_seconds_mean}} | {{avg_latency_mean}} | {{throughput_mean}} | {{avg_load_mean}} | {{pending_tasks_mean}} | {{deadline_violations_mean}} |

## Winners By Scale Point

| nodes | tasks | winner | score |
|---:|---:|---|---:|
| {{node_count}} | {{task_count}} | {{winner_algorithm}} | {{winner_score}} |

## Notes

- Runtime is machine-dependent and should be interpreted relatively.
- Quality metrics are deterministic for fixed seeds and identical configuration.
