"""Configuration schema and YAML loader for experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from project.algorithms import SUPPORTED_ALGORITHMS, normalize_algorithm

from .models import NetworkEdge, Node, Task


@dataclass(slots=True)
class SimulationConfig:
    """Simulation timing and deterministic randomization settings."""

    time_horizon: int = 10
    seed: int = 42
    step_seconds: float = 1.0


@dataclass(slots=True)
class OptimizationConfig:
    """Scheduling algorithm selection and comparison set."""

    algorithm: str = "min-load"
    compare_algorithms: list[str] = field(
        default_factory=lambda: ["round-robin", "min-load", "greedy"]
    )


@dataclass(slots=True)
class ObservabilityConfig:
    """Persistence, logging, and plotting settings for outputs."""

    output_dir: str = "outputs"
    log_level: str = "INFO"
    save_csv: bool = True
    save_plots: bool = True
    save_json: bool = True
    plot_profile: str = "publication"  # publication | default
    plot_dpi: int = 300
    plot_formats: list[str] = field(default_factory=lambda: ["png", "pdf", "svg"])


@dataclass(slots=True)
class IntelligenceConfig:
    """Prediction and adaptive-control parameters (ML/ZNN layer)."""

    enabled: bool = True
    prediction_window: int = 6
    znn_gain: float = 0.35
    high_queue_threshold: float = 2.0
    high_load_threshold: float = 0.70
    adaptive_algorithm: bool = True
    congestion_algorithm: str = "round-robin"
    normal_algorithm: str = "min-load"


@dataclass(slots=True)
class LLMConfig:
    """LLM integration settings and policy guard toggles."""

    enabled: bool = True
    provider: str = "auto"  # auto | openai | mock
    model: str = "gpt-5.4-mini"
    temperature: float = 0.2
    max_tokens: int = 300
    timeout_seconds: int = 12
    api_base_url: str = "https://api.openai.com"
    api_key_env: str = "OPENAI_API_KEY"
    allow_algorithm_override: bool = True
    allow_node_bias_override: bool = True
    allowed_algorithms: list[str] = field(
        default_factory=lambda: ["round-robin", "min-load", "greedy"]
    )


@dataclass(slots=True)
class DynamicLoadConfig:
    """Dynamic load generator parameters for scenario engine."""

    enabled: bool = False
    base_rate: float = 0.0
    amplitude: float = 0.0
    period: int = 8
    max_new_tasks: int = 8
    cpu_range: tuple[float, float] = (1.0, 4.0)
    memory_range: tuple[float, float] = (2.0, 10.0)
    data_size_range: tuple[float, float] = (64.0, 512.0)
    duration_range: tuple[int, int] = (1, 4)
    deadline_slack_range: tuple[int, int] = (2, 8)


@dataclass(slots=True)
class PeakLoadConfig:
    """Burst window configuration for peak-load experiments."""

    enabled: bool = False
    start: int = 0
    end: int = 0
    multiplier: float = 2.0


@dataclass(slots=True)
class NodeFailureEventConfig:
    """Single node-failure event in simulation time."""

    node_id: str
    time: int
    duration: int = 0


@dataclass(slots=True)
class NodeFailuresConfig:
    """Collection of node failure events."""

    enabled: bool = False
    events: list[NodeFailureEventConfig] = field(default_factory=list)


@dataclass(slots=True)
class HeterogeneousProfileConfig:
    """Task profile for heterogeneous workload generation."""

    name: str
    cpu_range: tuple[float, float]
    memory_range: tuple[float, float]
    data_size_range: tuple[float, float]
    duration_range: tuple[int, int]
    deadline_slack_range: tuple[int, int]


@dataclass(slots=True)
class HeterogeneousTasksConfig:
    """Heterogeneous task generation switch and profile set."""

    enabled: bool = False
    profiles: list[HeterogeneousProfileConfig] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioConfig:
    """Scenario-layer configuration bundle."""

    dynamic_load: DynamicLoadConfig = field(default_factory=DynamicLoadConfig)
    peak_load: PeakLoadConfig = field(default_factory=PeakLoadConfig)
    node_failures: NodeFailuresConfig = field(default_factory=NodeFailuresConfig)
    heterogeneous_tasks: HeterogeneousTasksConfig = field(
        default_factory=HeterogeneousTasksConfig
    )


@dataclass(slots=True)
class Chapter10Config:
    """Chapter 10 experiment pipeline defaults and toggles."""

    enabled: bool = False
    seeds: list[int] = field(default_factory=lambda: list(range(42, 72)))
    quick: bool = False
    save_plots: bool = True


@dataclass(slots=True)
class EnergyConfig:
    """Energy/CO2 estimation settings including eGRID dataset mapping."""

    enabled: bool = True
    egrid_dataset_path: str = "data/DataSet/eGRID2021_data.xlsx"
    egrid_level: str = "srl"  # srl | ba | us
    default_co2_lb_per_mwh: float = 855.0
    default_co2e_lb_per_mwh: float = 900.0
    node_power_idle_kw: float = 0.12
    node_power_max_kw: float = 0.35


@dataclass(slots=True)
class ExperimentConfig:
    """Top-level experiment configuration object."""

    name: str = "sprint0-smoke"
    scenario: str = "static"
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    intelligence: IntelligenceConfig = field(default_factory=IntelligenceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    scenarios: ScenarioConfig = field(default_factory=ScenarioConfig)
    chapter10: Chapter10Config = field(default_factory=Chapter10Config)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    nodes: list[Node] = field(default_factory=list)
    network_edges: list[NetworkEdge] = field(default_factory=list)
    initial_tasks: list[Task] = field(default_factory=list)


def load_config(path: str | Path) -> ExperimentConfig:
    """Load YAML config and convert it into a fully typed ExperimentConfig."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    simulation_raw = raw.get("simulation", {})
    simulation = SimulationConfig(
        time_horizon=max(1, _as_int(simulation_raw.get("time_horizon", 10), 10)),
        seed=_as_int(simulation_raw.get("seed", 42), 42),
        step_seconds=max(0.001, _as_float(simulation_raw.get("step_seconds", 1.0), 1.0)),
    )

    optimization_raw = raw.get("optimization", {})
    raw_compare = optimization_raw.get("compare_algorithms", list(SUPPORTED_ALGORITHMS))
    compare_algorithms = _normalize_algorithm_list(raw_compare)
    optimization = OptimizationConfig(
        algorithm=normalize_algorithm(str(optimization_raw.get("algorithm", "min-load"))),
        compare_algorithms=compare_algorithms or list(SUPPORTED_ALGORITHMS),
    )

    intelligence = _load_intelligence_config(raw.get("intelligence", {}))
    llm = _load_llm_config(raw.get("llm", {}))

    observability_raw = raw.get("observability", {})
    plot_formats = _parse_plot_formats(observability_raw.get("plot_formats", ["png"]))
    observability = ObservabilityConfig(
        output_dir=str(observability_raw.get("output_dir", "outputs")),
        log_level=str(observability_raw.get("log_level", "INFO")),
        save_csv=_as_bool(observability_raw.get("save_csv", True)),
        save_plots=_as_bool(observability_raw.get("save_plots", True)),
        save_json=_as_bool(observability_raw.get("save_json", True)),
        plot_profile=_parse_plot_profile(observability_raw.get("plot_profile", "publication")),
        plot_dpi=max(72, _as_int(observability_raw.get("plot_dpi", 300), 300)),
        plot_formats=plot_formats or ["png"],
    )

    scenarios = _load_scenario_config(raw.get("scenarios", {}))
    chapter10 = _load_chapter10_config(raw.get("chapter10", {}))
    energy = _load_energy_config(raw.get("energy", {}))

    nodes = [_build_node(item) for item in raw.get("nodes", [])]
    edges = [
        NetworkEdge(
            source=item["source"],
            target=item["target"],
            bandwidth=float(item["bandwidth"]),
            latency=float(item["latency"]),
        )
        for item in raw.get("network_edges", [])
    ]
    tasks = [
        Task(
            id=item["id"],
            cpu_required=float(item["cpu_required"]),
            memory_required=float(item["memory_required"]),
            data_size=float(item["data_size"]),
            deadline=float(item["deadline"]),
            arrival_time=int(item.get("arrival_time", 0)),
            duration=int(item.get("duration", 1)),
        )
        for item in raw.get("initial_tasks", [])
    ]

    return ExperimentConfig(
        name=str(raw.get("name", "sprint0-smoke")),
        scenario=str(raw.get("scenario", "static")),
        simulation=simulation,
        optimization=optimization,
        intelligence=intelligence,
        llm=llm,
        observability=observability,
        scenarios=scenarios,
        chapter10=chapter10,
        energy=energy,
        nodes=nodes,
        network_edges=edges,
        initial_tasks=tasks,
    )


def _load_scenario_config(raw: object) -> ScenarioConfig:
    """Parse scenario subsection and build ScenarioConfig."""
    data = raw if isinstance(raw, dict) else {}

    dynamic_raw = data.get("dynamic_load", {})
    dynamic_data = dynamic_raw if isinstance(dynamic_raw, dict) else {}
    dynamic = DynamicLoadConfig(
        enabled=_as_bool(dynamic_data.get("enabled", False)),
        base_rate=max(0.0, _as_float(dynamic_data.get("base_rate", 0.0), 0.0)),
        amplitude=max(0.0, _as_float(dynamic_data.get("amplitude", 0.0), 0.0)),
        period=max(1, _as_int(dynamic_data.get("period", 8), 8)),
        max_new_tasks=max(0, _as_int(dynamic_data.get("max_new_tasks", 8), 8)),
        cpu_range=_parse_float_range(dynamic_data.get("cpu_range"), (1.0, 4.0)),
        memory_range=_parse_float_range(dynamic_data.get("memory_range"), (2.0, 10.0)),
        data_size_range=_parse_float_range(
            dynamic_data.get("data_size_range"), (64.0, 512.0)
        ),
        duration_range=_parse_int_range(dynamic_data.get("duration_range"), (1, 4)),
        deadline_slack_range=_parse_int_range(
            dynamic_data.get("deadline_slack_range"), (2, 8)
        ),
    )

    peak_raw = data.get("peak_load", {})
    peak_data = peak_raw if isinstance(peak_raw, dict) else {}
    peak_start = _as_int(peak_data.get("start", 0), 0)
    peak_end = _as_int(peak_data.get("end", peak_start), peak_start)
    peak = PeakLoadConfig(
        enabled=_as_bool(peak_data.get("enabled", False)),
        start=min(peak_start, peak_end),
        end=max(peak_start, peak_end),
        multiplier=max(1.0, _as_float(peak_data.get("multiplier", 2.0), 2.0)),
    )

    failures_raw = data.get("node_failures", {})
    if isinstance(failures_raw, list):
        failures = NodeFailuresConfig(
            enabled=False,
            events=_parse_failure_events(failures_raw),
        )
    elif isinstance(failures_raw, dict):
        failures = NodeFailuresConfig(
            enabled=_as_bool(failures_raw.get("enabled", False)),
            events=_parse_failure_events(failures_raw.get("events", [])),
        )
    else:
        failures = NodeFailuresConfig()

    hetero_raw = data.get("heterogeneous_tasks", {})
    hetero_data = hetero_raw if isinstance(hetero_raw, dict) else {}
    profiles = _parse_heterogeneous_profiles(hetero_data.get("profiles", []))
    if not profiles:
        profiles = _default_heterogeneous_profiles()
    heterogeneous = HeterogeneousTasksConfig(
        enabled=_as_bool(hetero_data.get("enabled", False)),
        profiles=profiles,
    )

    return ScenarioConfig(
        dynamic_load=dynamic,
        peak_load=peak,
        node_failures=failures,
        heterogeneous_tasks=heterogeneous,
    )


def _load_intelligence_config(raw: object) -> IntelligenceConfig:
    """Parse intelligence subsection with defaults and clamping."""
    data = raw if isinstance(raw, dict) else {}
    return IntelligenceConfig(
        enabled=_as_bool(data.get("enabled", True)),
        prediction_window=max(2, _as_int(data.get("prediction_window", 6), 6)),
        znn_gain=max(0.01, _as_float(data.get("znn_gain", 0.35), 0.35)),
        high_queue_threshold=max(
            0.1, _as_float(data.get("high_queue_threshold", 2.0), 2.0)
        ),
        high_load_threshold=min(
            1.0, max(0.1, _as_float(data.get("high_load_threshold", 0.70), 0.70))
        ),
        adaptive_algorithm=_as_bool(data.get("adaptive_algorithm", True)),
        congestion_algorithm=normalize_algorithm(
            str(data.get("congestion_algorithm", "round-robin"))
        ),
        normal_algorithm=normalize_algorithm(str(data.get("normal_algorithm", "min-load"))),
    )


def _load_llm_config(raw: object) -> LLMConfig:
    """Parse LLM subsection and validate provider/allowed algorithms."""
    data = raw if isinstance(raw, dict) else {}
    allowed = _normalize_algorithm_list(data.get("allowed_algorithms", []))
    if not allowed:
        allowed = list(SUPPORTED_ALGORITHMS)
    provider = str(data.get("provider", "auto")).strip().lower()
    if provider not in {"auto", "openai", "mock"}:
        provider = "auto"
    return LLMConfig(
        enabled=_as_bool(data.get("enabled", True)),
        provider=provider,
        model=str(data.get("model", "gpt-5.4-mini")),
        temperature=max(0.0, _as_float(data.get("temperature", 0.2), 0.2)),
        max_tokens=max(64, _as_int(data.get("max_tokens", 300), 300)),
        timeout_seconds=max(3, _as_int(data.get("timeout_seconds", 12), 12)),
        api_base_url=str(data.get("api_base_url", "https://api.openai.com")).rstrip("/"),
        api_key_env=str(data.get("api_key_env", "OPENAI_API_KEY")),
        allow_algorithm_override=_as_bool(data.get("allow_algorithm_override", True)),
        allow_node_bias_override=_as_bool(data.get("allow_node_bias_override", True)),
        allowed_algorithms=allowed,
    )


def _load_chapter10_config(raw: object) -> Chapter10Config:
    """Parse Chapter 10 experiment defaults from config."""
    data = raw if isinstance(raw, dict) else {}
    seeds = _parse_int_list(data.get("seeds", list(range(42, 72))))
    if not seeds:
        seeds = list(range(42, 72))
    return Chapter10Config(
        enabled=_as_bool(data.get("enabled", False)),
        seeds=seeds,
        quick=_as_bool(data.get("quick", False)),
        save_plots=_as_bool(data.get("save_plots", True)),
    )


def _load_energy_config(raw: object) -> EnergyConfig:
    """Parse optional energy/eGRID settings from config."""
    data = raw if isinstance(raw, dict) else {}
    level = str(data.get("egrid_level", "srl")).strip().lower()
    if level not in {"srl", "ba", "us"}:
        level = "srl"
    idle_kw = max(0.01, _as_float(data.get("node_power_idle_kw", 0.12), 0.12))
    max_kw = max(idle_kw, _as_float(data.get("node_power_max_kw", 0.35), 0.35))
    return EnergyConfig(
        enabled=_as_bool(data.get("enabled", True)),
        egrid_dataset_path=str(data.get("egrid_dataset_path", "data/DataSet/eGRID2021_data.xlsx")),
        egrid_level=level,
        default_co2_lb_per_mwh=max(
            0.0, _as_float(data.get("default_co2_lb_per_mwh", 855.0), 855.0)
        ),
        default_co2e_lb_per_mwh=max(
            0.0, _as_float(data.get("default_co2e_lb_per_mwh", 900.0), 900.0)
        ),
        node_power_idle_kw=idle_kw,
        node_power_max_kw=max_kw,
    )


def _build_node(item: dict[str, object]) -> Node:
    """Build Node model from YAML item and optional initial load."""
    cpu = float(item["cpu"])
    load = float(item.get("load", 0.0))
    used_cpu = max(0.0, min(cpu, cpu * load))
    return Node(
        id=str(item["id"]),
        cpu=cpu,
        memory=float(item["memory"]),
        gpu=float(item.get("gpu", 0.0)),
        used_cpu=used_cpu,
        used_memory=0.0,
        egrid_subregion=str(item.get("egrid_subregion", item.get("subregion", ""))).strip(),
        egrid_ba_code=str(item.get("egrid_ba_code", item.get("ba_code", ""))).strip(),
    )


def _normalize_algorithm_list(raw: object) -> list[str]:
    """Normalize list-like algorithm input to unique supported names."""
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for item in raw:
        name = normalize_algorithm(str(item))
        if name not in normalized:
            normalized.append(name)
    return normalized


def _parse_failure_events(raw: object) -> list[NodeFailureEventConfig]:
    """Parse node failure event list from config."""
    if not isinstance(raw, list):
        return []
    events: list[NodeFailureEventConfig] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id", "")).strip()
        if not node_id:
            continue
        events.append(
            NodeFailureEventConfig(
                node_id=node_id,
                time=max(0, _as_int(item.get("time", 0), 0)),
                duration=max(0, _as_int(item.get("duration", 0), 0)),
            )
        )
    return events


def _parse_heterogeneous_profiles(raw: object) -> list[HeterogeneousProfileConfig]:
    """Parse heterogeneous task profiles from config."""
    if not isinstance(raw, list):
        return []
    profiles: list[HeterogeneousProfileConfig] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", f"profile-{i + 1}")).strip() or f"profile-{i + 1}"
        profiles.append(
            HeterogeneousProfileConfig(
                name=name,
                cpu_range=_parse_float_range(item.get("cpu_range"), (1.0, 4.0)),
                memory_range=_parse_float_range(item.get("memory_range"), (2.0, 10.0)),
                data_size_range=_parse_float_range(item.get("data_size_range"), (64.0, 512.0)),
                duration_range=_parse_int_range(item.get("duration_range"), (1, 4)),
                deadline_slack_range=_parse_int_range(
                    item.get("deadline_slack_range"), (2, 8)
                ),
            )
        )
    return profiles


def _default_heterogeneous_profiles() -> list[HeterogeneousProfileConfig]:
    """Fallback profile set used when none is provided in config."""
    return [
        HeterogeneousProfileConfig(
            name="cpu-heavy",
            cpu_range=(5.0, 9.0),
            memory_range=(2.0, 6.0),
            data_size_range=(96.0, 320.0),
            duration_range=(2, 5),
            deadline_slack_range=(2, 5),
        ),
        HeterogeneousProfileConfig(
            name="memory-heavy",
            cpu_range=(1.0, 3.0),
            memory_range=(10.0, 22.0),
            data_size_range=(256.0, 768.0),
            duration_range=(2, 5),
            deadline_slack_range=(3, 7),
        ),
        HeterogeneousProfileConfig(
            name="balanced",
            cpu_range=(2.0, 5.0),
            memory_range=(4.0, 12.0),
            data_size_range=(128.0, 512.0),
            duration_range=(1, 4),
            deadline_slack_range=(2, 6),
        ),
    ]


def _parse_float_range(raw: object, default: tuple[float, float]) -> tuple[float, float]:
    """Parse numeric [low, high] range with ordering normalization."""
    if not isinstance(raw, list) or len(raw) != 2:
        return default
    lo = _as_float(raw[0], default[0])
    hi = _as_float(raw[1], default[1])
    return (min(lo, hi), max(lo, hi))


def _parse_int_range(raw: object, default: tuple[int, int]) -> tuple[int, int]:
    """Parse integer [low, high] range with non-negative bounds."""
    if not isinstance(raw, list) or len(raw) != 2:
        return default
    lo = _as_int(raw[0], default[0])
    hi = _as_int(raw[1], default[1])
    lo = max(0, lo)
    hi = max(0, hi)
    return (min(lo, hi), max(lo, hi))


def _as_bool(value: object) -> bool:
    """Convert loose YAML value into bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _as_int(value: object, default: int) -> int:
    """Convert value to int with fallback default."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float) -> float:
    """Convert value to float with fallback default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int_list(value: object) -> list[int]:
    """Parse list-like integer values into unique ordered list."""
    if not isinstance(value, list):
        return []
    parsed: list[int] = []
    for item in value:
        try:
            integer = int(item)
        except (TypeError, ValueError):
            continue
        if integer not in parsed:
            parsed.append(integer)
    return parsed


def _parse_plot_profile(value: object) -> str:
    """Normalize plot profile to a supported option."""
    profile = str(value).strip().lower()
    if profile in {"publication", "default"}:
        return profile
    return "publication"


def _parse_plot_formats(value: object) -> list[str]:
    """Normalize plot formats to unique supported extensions."""
    allowed = {"png", "pdf", "svg"}
    raw_items: list[str]
    if isinstance(value, list):
        raw_items = [str(item).strip().lower() for item in value]
    elif isinstance(value, str):
        raw_items = [item.strip().lower() for item in value.split(",")]
    else:
        raw_items = []

    normalized: list[str] = []
    for item in raw_items:
        if item in allowed and item not in normalized:
            normalized.append(item)
    return normalized
