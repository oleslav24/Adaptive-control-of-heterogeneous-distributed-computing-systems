"""Parse simulation metrics from web job logs."""

from __future__ import annotations

import re


DEFAULT_MAX_CHART_POINTS = 300

TICK_METRIC_RE = re.compile(
    r"t=(?P<time>\d+)\s+queue=(?P<queue>\d+)\s+completed=(?P<completed>\d+)\s+"
    r"latency=(?P<latency>[0-9.]+)\s+throughput=(?P<throughput>[0-9.]+)\s+"
    r"avg_load=(?P<avg_load>[0-9.]+)"
)
RUN_INIT_RE = re.compile(
    r"Simulation initialized:\s+(?:scenario=(?P<scenario>[\w\-]+)\s+)?"
    r"algorithm=(?P<algorithm>[\w\-]+)"
)


def split_metric_runs(
    points: list[dict[str, float | int]],
    run_descriptors: list[dict[str, str | int]] | None = None,
) -> list[dict[str, list[float | int] | int | str]]:
    """Split flattened metric points into sub-runs by time reset."""
    if not points:
        return []
    chunks: list[list[dict[str, float | int]]] = []
    current: list[dict[str, float | int]] = []
    previous_t: int | None = None
    for point in points:
        time_value = int(point["time"])
        if previous_t is not None and time_value < previous_t and current:
            chunks.append(current)
            current = []
        current.append(point)
        previous_t = time_value
    if current:
        chunks.append(current)

    descriptors = list(run_descriptors or [])
    descriptor_offset = max(0, len(descriptors) - len(chunks))
    runs: list[dict[str, list[float | int] | int | str]] = []
    for idx, chunk in enumerate(chunks, start=1):
        descriptor: dict[str, str | int] = {}
        descriptor_index = descriptor_offset + idx - 1
        if descriptor_index < len(descriptors):
            descriptor = descriptors[descriptor_index]
        runs.append(
            {
                "run_index": int(descriptor.get("run_index", idx)),
                "scenario": str(descriptor.get("scenario", "")).strip(),
                "algorithm": str(descriptor.get("algorithm", "")).strip(),
                "time": [int(item["time"]) for item in chunk],
                "queue": [int(item["queue"]) for item in chunk],
                "completed": [int(item["completed"]) for item in chunk],
                "latency": [float(item["latency"]) for item in chunk],
                "throughput": [float(item["throughput"]) for item in chunk],
                "avg_load": [float(item["avg_load"]) for item in chunk],
            }
        )
    return runs


def extract_metrics_from_logs(
    lines: list[str],
    *,
    max_chart_points: int = DEFAULT_MAX_CHART_POINTS,
) -> dict[str, object]:
    """Extract timeseries metrics from simulation loop log lines."""
    points: list[dict[str, float | int]] = []
    run_descriptors: list[dict[str, str | int]] = []
    for line in lines:
        run_match = RUN_INIT_RE.search(line)
        if run_match is not None:
            run_descriptors.append(
                {
                    "run_index": len(run_descriptors) + 1,
                    "scenario": (run_match.group("scenario") or "").strip(),
                    "algorithm": (run_match.group("algorithm") or "").strip(),
                }
            )
        match = TICK_METRIC_RE.search(line)
        if match is None:
            continue
        points.append(
            {
                "time": int(match.group("time")),
                "queue": int(match.group("queue")),
                "completed": int(match.group("completed")),
                "latency": float(match.group("latency")),
                "throughput": float(match.group("throughput")),
                "avg_load": float(match.group("avg_load")),
            }
        )
    if len(points) > max_chart_points:
        points = points[-max_chart_points:]

    if not points:
        return {
            "time": [],
            "queue": [],
            "completed": [],
            "latency": [],
            "throughput": [],
            "avg_load": [],
            "runs": [],
        }
    return {
        "time": [int(item["time"]) for item in points],
        "queue": [int(item["queue"]) for item in points],
        "completed": [int(item["completed"]) for item in points],
        "latency": [float(item["latency"]) for item in points],
        "throughput": [float(item["throughput"]) for item in points],
        "avg_load": [float(item["avg_load"]) for item in points],
        "runs": split_metric_runs(points, run_descriptors=run_descriptors),
    }

