"""Decision trace normalization for MAS/ML/ZNN/LLM observability artifacts."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

TRACE_BASE_COLUMNS = [
    "time",
    "agent",
    "event",
    "active_algorithm",
]


def normalize_decision_trace(records: list[dict[str, object]]) -> list[dict[str, Any]]:
    """Return JSON-safe decision trace records preserving event order."""
    normalized: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        normalized.append({str(key): _json_safe(value) for key, value in item.items()})
    return normalized


def build_decision_trace_dataframe(records: list[dict[str, object]]) -> pd.DataFrame:
    """Build a CSV-friendly decision trace table from normalized records."""
    normalized = normalize_decision_trace(records)
    columns = _ordered_columns(normalized)
    if not normalized:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(normalized)
    for column in df.columns:
        df[column] = df[column].map(_csv_safe)
    return df.reindex(columns=columns)


def _ordered_columns(records: list[dict[str, Any]]) -> list[str]:
    """Keep stable core columns first and sort extension columns."""
    extra: set[str] = set()
    for record in records:
        extra.update(record.keys())
    return TRACE_BASE_COLUMNS + sorted(extra.difference(TRACE_BASE_COLUMNS))


def _json_safe(value: Any) -> Any:
    """Convert nested values to deterministic JSON-compatible objects."""
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _csv_safe(value: Any) -> Any:
    """Render nested trace payloads as stable JSON strings for CSV output."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value
