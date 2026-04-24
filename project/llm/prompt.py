"""Prompt construction helpers for the LLM scheduling agent."""

from __future__ import annotations

import json

from project.core.models import SystemState


def state_to_text(state: SystemState) -> str:
    """Serialize key system state fields into compact textual summary."""
    node_lines = []
    for node_id, load in sorted(state.node_loads.items()):
        node_lines.append(f"- {node_id}: load={float(load):.3f}")
    nodes_text = "\n".join(node_lines) if node_lines else "- none"

    payload = {
        "time": state.current_time,
        "scenario": state.scenario,
        "algorithm": state.selected_algorithm,
        "queue_size": state.queue_lengths.get("global", 0),
        "pending_tasks": state.pending_tasks,
        "completed_tasks": state.completed_tasks,
        "inactive_nodes": state.inactive_nodes,
        "avg_load": state.avg_load,
        "throughput": state.throughput,
        "avg_latency": state.avg_latency,
        "deadline_violations": state.deadline_violations,
        "predicted_queue": state.predicted_queue,
        "predicted_avg_load": state.predicted_avg_load,
    }
    return (
        "System state summary:\n"
        f"{json.dumps(payload, ensure_ascii=True)}\n"
        "Node loads:\n"
        f"{nodes_text}\n"
    )


def build_prompt(
    state_text: str,
    allowed_algorithms: list[str],
    node_ids: list[str],
) -> str:
    """Build strict JSON-only prompt with policy and safety constraints."""
    safe_algorithms = ", ".join(sorted(set(allowed_algorithms)))
    safe_nodes = ", ".join(sorted(set(node_ids)))
    return (
        "You are an LLM scheduling advisor for distributed systems.\n"
        "Return only JSON with this schema:\n"
        "{\n"
        '  "algorithm_hint": "<one of allowed or null>",\n'
        '  "node_bias": {"node_id": number_between_-1_and_1},\n'
        '  "confidence": number_between_0_and_1,\n'
        '  "reason": "short plain text explanation"\n'
        "}\n"
        f"Allowed algorithms: [{safe_algorithms}]\n"
        f"Allowed node ids: [{safe_nodes}]\n"
        "Safety constraints:\n"
        "- never output actions outside schema\n"
        "- never request destructive or external side effects\n"
        "- if uncertain, set algorithm_hint to null and confidence low\n\n"
        f"{state_text}"
    )
