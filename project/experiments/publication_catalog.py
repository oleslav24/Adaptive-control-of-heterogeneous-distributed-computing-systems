"""Method catalog and study spec generation for publication experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace


NETWORK_PROFILES: dict[str, dict[str, float]] = {
    "weak": {"bandwidth": 200.0, "latency": 25.0},
    "medium": {"bandwidth": 1000.0, "latency": 10.0},
    "high": {"bandwidth": 5000.0, "latency": 3.0},
}


@dataclass(slots=True)
class MethodVariant:
    """Definition of one compared method in the publication catalog."""

    key: str
    label: str
    family: str
    ready: bool
    algorithm: str
    intelligence_enabled: bool
    adaptive_algorithm: bool
    llm_enabled: bool
    llm_provider: str = "mock"
    znn_gain: float = 0.35
    note: str = ""


METHOD_CATALOG: list[MethodVariant] = [
    MethodVariant(
        key="round-robin",
        label="Round-Robin",
        family="baseline",
        ready=True,
        algorithm="round-robin",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
    ),
    MethodVariant(
        key="min-load",
        label="Min-Load",
        family="baseline",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
    ),
    MethodVariant(
        key="greedy",
        label="Greedy",
        family="baseline",
        ready=True,
        algorithm="greedy",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
    ),
    MethodVariant(
        key="carbon-aware",
        label="Carbon-Aware",
        family="baseline",
        ready=True,
        algorithm="carbon-aware",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
    ),
    MethodVariant(
        key="mas-basic",
        label="MAS (No ML)",
        family="multi-agent",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
    ),
    MethodVariant(
        key="mas-ml",
        label="MAS + ML",
        family="multi-agent",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=True,
        adaptive_algorithm=False,
        llm_enabled=False,
        znn_gain=0.01,
    ),
    MethodVariant(
        key="mas-znn",
        label="MAS + ZNN",
        family="neural",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=True,
        adaptive_algorithm=False,
        llm_enabled=False,
        znn_gain=0.55,
    ),
    MethodVariant(
        key="mas-hybrid",
        label="Hybrid MAS",
        family="hybrid",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=True,
        adaptive_algorithm=True,
        llm_enabled=False,
        znn_gain=0.40,
    ),
    MethodVariant(
        key="mas-llm",
        label="MAS + LLM",
        family="llm",
        ready=True,
        algorithm="min-load",
        intelligence_enabled=True,
        adaptive_algorithm=True,
        llm_enabled=True,
        llm_provider="mock",
        znn_gain=0.40,
    ),
    MethodVariant(
        key="transport",
        label="Transport (Classical)",
        family="classical-optimization",
        ready=False,
        algorithm="min-load",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
        note="Placeholder for dedicated transport-solver integration.",
    ),
    MethodVariant(
        key="abc",
        label="ABC",
        family="metaheuristic",
        ready=False,
        algorithm="greedy",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
        note="Placeholder for Artificial Bee Colony implementation.",
    ),
    MethodVariant(
        key="max-min",
        label="Max-Min",
        family="metaheuristic",
        ready=True,
        algorithm="max-min",
        intelligence_enabled=False,
        adaptive_algorithm=False,
        llm_enabled=False,
        note="Deterministic bottleneck-preserving Max-Min resource heuristic.",
    ),
    MethodVariant(
        key="abc-max-min",
        label="Hybrid ABC + Max-Min",
        family="hybrid",
        ready=False,
        algorithm="greedy",
        intelligence_enabled=True,
        adaptive_algorithm=True,
        llm_enabled=False,
        note="Placeholder for hybrid ABC+Max-Min implementation.",
    ),
]


@dataclass(slots=True)
class StudyRunSpec:
    """One experiment specification for a study/scenario/method subset."""

    study_id: str
    scenario: str
    node_count: int
    task_count: int
    task_type: str
    network_profile: str
    topology: str
    methods: list[str]
    seeds: list[int]


def build_study_specs(
    *,
    seeds: list[int],
    ready_methods: list[str],
    quick: bool,
    method_overrides_by_study: dict[str, list[str]] | None = None,
) -> list[StudyRunSpec]:
    """Build study specs for quick smoke or full publication execution."""
    if quick:
        quick_specs = [
            StudyRunSpec(
                study_id="E1_scalability",
                scenario="static",
                node_count=n,
                task_count=t,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=[
                    "round-robin",
                    "min-load",
                    "greedy",
                    "max-min",
                    "carbon-aware",
                    "mas-hybrid",
                    "mas-llm",
                ],
                seeds=seeds,
            )
            for n, t in [(10, 100), (50, 500)]
        ] + [
            StudyRunSpec(
                study_id="E2_adaptivity",
                scenario="dynamic-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-basic", "mas-hybrid", "mas-ml", "mas-znn", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E2_adaptivity",
                scenario="peak-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-basic", "mas-hybrid", "mas-ml", "mas-znn", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E3_robustness",
                scenario="node-failures",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["round-robin", "min-load", "mas-basic", "mas-hybrid"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E4_hybrid_vs_classical",
                scenario="dynamic-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["round-robin", "min-load", "greedy", "max-min", "mas-hybrid"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E5_llm_vs_algorithmic",
                scenario="dynamic-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E5_llm_vs_algorithmic",
                scenario="peak-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E6_carbon_vs_performance",
                scenario="dynamic-load",
                node_count=50,
                task_count=300,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "greedy", "carbon-aware", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
        ]
        return _apply_method_overrides(
            _filter_specs_by_ready_methods(quick_specs, ready_methods),
            method_overrides_by_study,
        )

    base_specs: list[StudyRunSpec] = []
    scalability_nodes = [10, 50, 100, 500]
    scalability_tasks = [100, 500, 1000, 5000]
    for node_count, task_count in zip(scalability_nodes, scalability_tasks):
        base_specs.append(
            StudyRunSpec(
                study_id="E1_scalability",
                scenario="static",
                node_count=node_count,
                task_count=task_count,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=[
                    "round-robin",
                    "min-load",
                    "greedy",
                    "max-min",
                    "carbon-aware",
                    "mas-hybrid",
                    "mas-llm",
                ],
                seeds=seeds,
            )
        )

    base_specs.extend(
        [
            StudyRunSpec(
                study_id="E2_adaptivity",
                scenario="dynamic-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-basic", "mas-hybrid", "mas-ml", "mas-znn", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E2_adaptivity",
                scenario="peak-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-basic", "mas-hybrid", "mas-ml", "mas-znn", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E3_robustness",
                scenario="node-failures",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["round-robin", "min-load", "mas-basic", "mas-hybrid"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E4_hybrid_vs_classical",
                scenario="dynamic-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["round-robin", "min-load", "greedy", "max-min", "mas-hybrid"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E5_llm_vs_algorithmic",
                scenario="dynamic-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E5_llm_vs_algorithmic",
                scenario="peak-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
            StudyRunSpec(
                study_id="E6_carbon_vs_performance",
                scenario="dynamic-load",
                node_count=100,
                task_count=1000,
                task_type="mixed",
                network_profile="medium",
                topology="ring",
                methods=["min-load", "greedy", "carbon-aware", "mas-hybrid", "mas-llm"],
                seeds=seeds,
            ),
        ]
    )

    return _apply_method_overrides(
        _filter_specs_by_ready_methods(base_specs, ready_methods),
        method_overrides_by_study,
    )


def _filter_specs_by_ready_methods(
    specs: list[StudyRunSpec],
    ready_methods: list[str],
) -> list[StudyRunSpec]:
    """Remove unavailable methods from study specs without changing study order."""
    ready_set = set(ready_methods)
    filtered_specs: list[StudyRunSpec] = []
    for spec in specs:
        available = [method for method in spec.methods if method in ready_set]
        if available:
            filtered_specs.append(replace(spec, methods=available))
    return filtered_specs


def _apply_method_overrides(
    specs: list[StudyRunSpec],
    method_overrides_by_study: dict[str, list[str]] | None,
) -> list[StudyRunSpec]:
    """Apply optional per-study method whitelists while preserving spec order."""
    if not method_overrides_by_study:
        return specs

    overrides: dict[str, set[str]] = {
        str(study_id): {str(method).strip() for method in methods if str(method).strip()}
        for study_id, methods in method_overrides_by_study.items()
    }
    filtered_specs: list[StudyRunSpec] = []
    for spec in specs:
        allowed = overrides.get(spec.study_id)
        if allowed is None:
            filtered_specs.append(spec)
            continue
        methods = [method for method in spec.methods if method in allowed]
        if methods:
            filtered_specs.append(replace(spec, methods=methods))
    return filtered_specs


def method_to_row(variant: MethodVariant) -> dict[str, object]:
    """Serialize method variant into flat table row."""
    return {
        "key": variant.key,
        "label": variant.label,
        "family": variant.family,
        "ready": variant.ready,
        "algorithm": variant.algorithm,
        "intelligence_enabled": variant.intelligence_enabled,
        "adaptive_algorithm": variant.adaptive_algorithm,
        "llm_enabled": variant.llm_enabled,
        "llm_provider": variant.llm_provider,
        "znn_gain": variant.znn_gain,
        "note": variant.note,
    }


def get_method_variant(key: str) -> MethodVariant:
    """Resolve method key from catalog or raise on unknown key."""
    for variant in METHOD_CATALOG:
        if variant.key == key:
            return variant
    raise KeyError(f"Unknown method variant '{key}'.")

