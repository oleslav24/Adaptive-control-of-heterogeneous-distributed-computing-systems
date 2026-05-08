"""Unit tests for parsing web realtime metrics from logs."""

from project.web.metrics_parser import extract_metrics_from_logs, split_metric_runs


def test_split_metric_runs_by_time_reset() -> None:
    """Time reset splits flattened stream into independent runs."""
    points = [
        {"time": 0, "queue": 4, "completed": 0, "latency": 1.0, "throughput": 0.0, "avg_load": 0.2},
        {"time": 1, "queue": 3, "completed": 1, "latency": 0.9, "throughput": 1.0, "avg_load": 0.3},
        {"time": 0, "queue": 6, "completed": 0, "latency": 1.4, "throughput": 0.0, "avg_load": 0.4},
    ]
    runs = split_metric_runs(points)
    assert len(runs) == 2
    assert runs[0]["time"] == [0, 1]
    assert runs[1]["time"] == [0]


def test_extract_metrics_from_logs_with_run_descriptors() -> None:
    """Parser maps descriptors to corresponding run chunks."""
    lines = [
        "Simulation initialized: scenario=static algorithm=min-load",
        "t=0 queue=4 completed=0 latency=1.0 throughput=0.0 avg_load=0.2",
        "t=1 queue=2 completed=1 latency=0.8 throughput=1.0 avg_load=0.3",
        "Simulation initialized: scenario=peak-load algorithm=greedy",
        "t=0 queue=6 completed=0 latency=1.5 throughput=0.0 avg_load=0.5",
        "t=1 queue=5 completed=1 latency=1.2 throughput=1.0 avg_load=0.6",
    ]
    metrics = extract_metrics_from_logs(lines)
    assert metrics["time"] == [0, 1, 0, 1]
    runs = metrics["runs"]
    assert isinstance(runs, list)
    assert len(runs) == 2
    first = runs[0]
    second = runs[1]
    assert first["scenario"] == "static"
    assert first["algorithm"] == "min-load"
    assert first["time"] == [0, 1]
    assert second["scenario"] == "peak-load"
    assert second["algorithm"] == "greedy"
    assert second["time"] == [0, 1]


def test_extract_metrics_from_logs_truncates_to_latest_points() -> None:
    """When history is long, parser keeps only latest chart points."""
    lines = [
        "Simulation initialized: scenario=static algorithm=min-load",
        "t=0 queue=4 completed=0 latency=1.0 throughput=0.0 avg_load=0.2",
        "t=1 queue=2 completed=1 latency=0.8 throughput=1.0 avg_load=0.3",
        "Simulation initialized: scenario=peak-load algorithm=greedy",
        "t=0 queue=6 completed=0 latency=1.5 throughput=0.0 avg_load=0.5",
        "t=1 queue=5 completed=1 latency=1.2 throughput=1.0 avg_load=0.6",
    ]
    metrics = extract_metrics_from_logs(lines, max_chart_points=2)
    assert metrics["time"] == [0, 1]
    runs = metrics["runs"]
    assert isinstance(runs, list)
    assert len(runs) == 1
    assert runs[0]["scenario"] == "peak-load"
    assert runs[0]["algorithm"] == "greedy"


def test_extract_metrics_from_logs_empty_payload() -> None:
    """Non-matching logs yield empty metrics structure."""
    metrics = extract_metrics_from_logs(["random line"])
    assert metrics == {
        "time": [],
        "queue": [],
        "completed": [],
        "latency": [],
        "throughput": [],
        "avg_load": [],
        "runs": [],
    }
