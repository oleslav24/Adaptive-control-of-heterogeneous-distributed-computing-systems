"""Helpers for local literature evidence retrieval and quality checks."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import math
import re
import textwrap
from typing import Any, Sequence

from project.literature_rag import search_chunks


DEFAULT_QUERY = "adaptive multi-agent scheduling heterogeneous distributed computing"
_CACHE_LIMIT = 64
_SEARCH_CACHE: dict[tuple[str, int, float, int], dict[str, Any]] = {}


def _safe_floats(values: Sequence[float | int] | None) -> list[float]:
    """Convert numeric sequence to float list, skipping invalid values."""
    if not values:
        return []
    cleaned: list[float] = []
    for value in values:
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            continue
    return cleaned


def _relative_change(values: Sequence[float]) -> float:
    """Return relative start-to-end change with safe near-zero denominator."""
    if len(values) < 2:
        return 0.0
    start = float(values[0])
    end = float(values[-1])
    scale = abs(start) if abs(start) > 1e-9 else 1.0
    return (end - start) / scale


def _clean_token(raw: str) -> str:
    """Normalize token by dropping non-alnum separators."""
    token = re.sub(r"[^a-zA-Z0-9-]+", " ", str(raw).strip().lower())
    return re.sub(r"\s+", " ", token).strip()


def build_query_from_metrics(
    metrics: dict[str, Sequence[float | int]],
    *,
    scenario: str = "",
    algorithm: str = "",
) -> str:
    """Build retrieval query based on observed runtime dynamics."""
    latency = _safe_floats(metrics.get("latency"))
    queue = _safe_floats(metrics.get("queue"))
    throughput = _safe_floats(metrics.get("throughput"))
    avg_load = _safe_floats(metrics.get("avg_load"))

    parts: list[str] = [
        "task scheduling",
        "heterogeneous distributed systems",
        "multi-agent control",
    ]

    lat_change = _relative_change(latency)
    queue_change = _relative_change(queue)
    thr_change = _relative_change(throughput)

    if lat_change >= 0.10:
        parts.append("latency reduction")
    elif lat_change <= -0.10:
        parts.append("latency stabilization")

    if queue_change >= 0.10:
        parts.append("queue buildup mitigation")
        parts.append("load balancing")
    elif queue_change <= -0.10:
        parts.append("queue draining strategy")

    if thr_change <= -0.10:
        parts.append("throughput degradation")
    elif thr_change >= 0.10:
        parts.append("throughput optimization")

    if avg_load and max(avg_load) >= 0.85:
        parts.append("resource contention")
    elif avg_load and sum(avg_load) / float(len(avg_load)) < 0.35:
        parts.append("resource underutilization")

    normalized_scenario = _clean_token(scenario)
    if normalized_scenario:
        parts.append(f"scenario {normalized_scenario}")
    normalized_algorithm = _clean_token(algorithm)
    if normalized_algorithm:
        parts.append(f"algorithm {normalized_algorithm}")

    deduped: list[str] = []
    seen = set()
    for part in parts:
        value = part.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(value)
    return " ".join(deduped) if deduped else DEFAULT_QUERY


def search_literature(
    query: str,
    *,
    top_k: int = 5,
    min_score: float = 0.03,
    snippet_chars: int = 280,
) -> dict[str, Any]:
    """Search local RAG corpus and return normalized evidence payload."""
    normalized_query = " ".join(str(query or "").strip().split()) or DEFAULT_QUERY
    key = (normalized_query, int(top_k), float(min_score), int(snippet_chars))
    cached = _SEARCH_CACHE.get(key)
    if cached is not None:
        return deepcopy(cached)

    try:
        rows = search_chunks(normalized_query, top_k=max(1, int(top_k)), min_score=float(min_score))
    except FileNotFoundError:
        payload = {
            "available": False,
            "reason": "index-not-built",
            "query": normalized_query,
            "items": [],
        }
        _store_cache(key, payload)
        return deepcopy(payload)
    except Exception as exc:  # noqa: BLE001 - defensive fallback for web/report flows.
        payload = {
            "available": False,
            "reason": f"search-error:{type(exc).__name__}",
            "query": normalized_query,
            "items": [],
        }
        _store_cache(key, payload)
        return deepcopy(payload)

    items: list[dict[str, Any]] = []
    for row in rows:
        page_value = row.get("page_start", row.get("page", 0))
        try:
            page = int(page_value)
        except (TypeError, ValueError):
            page = 0
        snippet = textwrap.shorten(
            re.sub(r"\s+", " ", str(row.get("text", "")).strip()),
            width=max(80, int(snippet_chars)),
            placeholder=" ...",
        )
        items.append(
            {
                "rank": int(row.get("rank", len(items) + 1)),
                "score": float(row.get("score", 0.0)),
                "article_id": str(row.get("article_id", "")),
                "title": str(row.get("title", "")),
                "page": page,
                "pdf_path": str(row.get("pdf_path", "")),
                "snippet": snippet,
            }
        )

    payload = {
        "available": bool(items),
        "reason": "" if items else "no-matches",
        "query": normalized_query,
        "items": items,
    }
    _store_cache(key, payload)
    return deepcopy(payload)


def validate_evidence_items(
    items: Sequence[dict[str, Any]],
    *,
    min_sources: int = 2,
) -> dict[str, Any]:
    """Validate evidence coverage and citation field format."""
    errors: list[str] = []
    normalized = [item for item in items if isinstance(item, dict)]
    if len(normalized) < max(1, int(min_sources)):
        errors.append(
            f"Expected at least {max(1, int(min_sources))} sources, got {len(normalized)}."
        )

    for idx, item in enumerate(normalized):
        article_id = str(item.get("article_id", "")).strip()
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        pdf_path = str(item.get("pdf_path", "")).strip()
        score = item.get("score")
        page = item.get("page")

        if not article_id:
            errors.append(f"Item {idx}: article_id is empty.")
        if not title:
            errors.append(f"Item {idx}: title is empty.")
        if not snippet:
            errors.append(f"Item {idx}: snippet is empty.")
        if not pdf_path:
            errors.append(f"Item {idx}: pdf_path is empty.")
        else:
            path = Path(pdf_path)
            if not path.is_absolute():
                errors.append(f"Item {idx}: pdf_path must be absolute.")
            if path.suffix.lower() != ".pdf":
                errors.append(f"Item {idx}: pdf_path must point to a .pdf file.")

        try:
            score_value = float(score)
        except (TypeError, ValueError):
            errors.append(f"Item {idx}: score is not numeric.")
        else:
            if not math.isfinite(score_value) or score_value < 0.0:
                errors.append(f"Item {idx}: score must be finite and >= 0.")

        try:
            page_value = int(page)
        except (TypeError, ValueError):
            errors.append(f"Item {idx}: page is not integer-like.")
        else:
            if page_value <= 0:
                errors.append(f"Item {idx}: page must be >= 1.")

    return {
        "ok": not errors,
        "errors": errors,
        "source_count": len(normalized),
        "min_sources": max(1, int(min_sources)),
    }


def render_markdown_evidence(items: Sequence[dict[str, Any]], *, limit: int = 5) -> list[str]:
    """Render evidence list as markdown bullet lines."""
    lines: list[str] = []
    for item in list(items)[: max(1, int(limit))]:
        article_id = str(item.get("article_id", "")).strip() or "unknown"
        page = item.get("page", 0)
        title = str(item.get("title", "")).strip() or "Untitled"
        score = item.get("score")
        snippet = str(item.get("snippet", "")).strip()
        try:
            score_value = float(score)
            score_text = f"{score_value:.4f}"
        except (TypeError, ValueError):
            score_text = "n/a"
        citation = f"[{article_id}, p. {page}]"
        if snippet:
            lines.append(f"- {citation} {title} (score={score_text}): {snippet}")
        else:
            lines.append(f"- {citation} {title} (score={score_text})")
    return lines


def build_query_from_study(summary_df: Any, hypotheses_df: Any) -> str:
    """Build retrieval query from publication/chapter summary tables."""
    parts: list[str] = [
        "adaptive control",
        "heterogeneous distributed computing",
        "task scheduling",
    ]

    try:
        summary_empty = bool(getattr(summary_df, "empty"))
    except Exception:  # noqa: BLE001
        summary_empty = True
    if not summary_empty:
        columns = set(getattr(summary_df, "columns", []))
        if {"method", "avg_latency_mean"}.issubset(columns):
            try:
                best_methods = (
                    summary_df.sort_values("avg_latency_mean")["method"].astype(str).head(3).tolist()
                )
                for method in best_methods:
                    token = _clean_token(method)
                    if token:
                        parts.append(f"method {token}")
            except Exception:  # noqa: BLE001
                pass
        if "scenario" in columns:
            try:
                scenarios = summary_df["scenario"].astype(str).drop_duplicates().head(2).tolist()
                for scenario in scenarios:
                    token = _clean_token(scenario)
                    if token:
                        parts.append(f"scenario {token}")
            except Exception:  # noqa: BLE001
                pass
        if {"co2_per_completed_task_lb_mean", "throughput_mean"}.issubset(columns):
            parts.append("carbon aware scheduling tradeoff")

    try:
        hyp_empty = bool(getattr(hypotheses_df, "empty"))
    except Exception:  # noqa: BLE001
        hyp_empty = True
    if not hyp_empty and "hypothesis" in set(getattr(hypotheses_df, "columns", [])):
        try:
            hyps = {str(value).strip() for value in hypotheses_df["hypothesis"].tolist()}
        except Exception:  # noqa: BLE001
            hyps = set()
        if "H2" in hyps:
            parts.append("multi-agent robustness")
        if "H3" in hyps:
            parts.append("machine learning znn scheduling")
        if "H5" in hyps:
            parts.append("llm coordination distributed systems")

    deduped: list[str] = []
    seen = set()
    for part in parts:
        token = " ".join(str(part).strip().split())
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(token)
    return " ".join(deduped) if deduped else DEFAULT_QUERY


def build_report_evidence(
    *,
    summary_df: Any,
    hypotheses_df: Any,
    top_k: int = 5,
    min_score: float = 0.03,
    min_sources: int = 2,
) -> dict[str, Any]:
    """Build local literature evidence bundle for report rendering."""
    query = build_query_from_study(summary_df, hypotheses_df)
    evidence = search_literature(query, top_k=top_k, min_score=min_score)
    if not evidence.get("available", False):
        return {
            "query": query,
            "evidence": evidence,
            "gate": {
                "ok": False,
                "errors": [f"Evidence unavailable: {evidence.get('reason', 'unknown')}"],
                "source_count": 0,
                "min_sources": max(1, int(min_sources)),
                "skipped": True,
            },
        }
    gate = validate_evidence_items(evidence.get("items", []), min_sources=min_sources)
    gate["skipped"] = False
    return {
        "query": query,
        "evidence": evidence,
        "gate": gate,
    }


def _store_cache(key: tuple[str, int, float, int], payload: dict[str, Any]) -> None:
    """Store payload in tiny in-process cache with bounded size."""
    if len(_SEARCH_CACHE) >= _CACHE_LIMIT:
        oldest = next(iter(_SEARCH_CACHE.keys()), None)
        if oldest is not None:
            _SEARCH_CACHE.pop(oldest, None)
    _SEARCH_CACHE[key] = deepcopy(payload)
