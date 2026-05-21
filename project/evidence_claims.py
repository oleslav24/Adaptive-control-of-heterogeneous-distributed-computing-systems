"""Evidence-backed claim generation and validation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any, Sequence


REQUIRED_HYPOTHESES = ("H1", "H2", "H3", "H4", "H5")


@dataclass(slots=True)
class EvidenceClaim:
    """Structured claim tied to an experiment hypothesis and local evidence."""

    claim_id: str
    hypothesis: str
    statement: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "insufficient-evidence"

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable claim representation."""
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 4)
        return payload


def _safe_floats(values: Sequence[float | int] | None) -> list[float]:
    """Convert numeric sequence to floats while skipping invalid values."""
    if not values:
        return []
    cleaned: list[float] = []
    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            cleaned.append(parsed)
    return cleaned


def _relative_change(values: Sequence[float]) -> float:
    """Return relative start-to-end change with safe near-zero denominator."""
    if len(values) < 2:
        return 0.0
    start = float(values[0])
    end = float(values[-1])
    scale = abs(start) if abs(start) > 1e-9 else 1.0
    return (end - start) / scale


def _evidence_items(evidence_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract evidence item list from normalized literature payload."""
    if not evidence_payload or not evidence_payload.get("available", False):
        return []
    items = evidence_payload.get("items", [])
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _top_evidence(
    evidence_payload: dict[str, Any] | None,
    *,
    limit: int,
    min_score: float,
) -> list[dict[str, Any]]:
    """Return best evidence rows above threshold."""
    rows: list[dict[str, Any]] = []
    for item in _evidence_items(evidence_payload):
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score) or score < float(min_score):
            continue
        normalized = dict(item)
        normalized["score"] = score
        rows.append(normalized)
    rows.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return rows[: max(1, int(limit))]


def _status(base_status: str, evidence: list[dict[str, Any]], min_sources: int) -> str:
    """Apply evidence availability to a metric-derived claim status."""
    if len(evidence) < max(1, int(min_sources)):
        return "insufficient-evidence"
    return base_status


def _confidence(
    *,
    metric_strength: float,
    evidence: list[dict[str, Any]],
    min_sources: int,
) -> float:
    """Combine metric signal strength with evidence coverage into [0, 1]."""
    metric_part = min(1.0, max(0.0, metric_strength))
    if not evidence:
        evidence_part = 0.0
    else:
        scores = []
        for item in evidence:
            try:
                scores.append(float(item.get("score", 0.0)))
            except (TypeError, ValueError):
                continue
        score_part = min(1.0, (fmean(scores) / 0.25) if scores else 0.0)
        coverage_part = min(1.0, len(evidence) / float(max(1, int(min_sources))))
        evidence_part = (score_part * 0.55) + (coverage_part * 0.45)
    return min(1.0, (metric_part * 0.65) + (evidence_part * 0.35))


def build_runtime_claims(
    metrics: dict[str, Sequence[float | int]],
    evidence_payload: dict[str, Any] | None,
    *,
    scenario: str = "",
    algorithm: str = "",
    min_sources_per_claim: int = 2,
    min_score: float = 0.03,
) -> dict[str, Any]:
    """Build evidence-backed claims from live chart metrics."""
    latency = _safe_floats(metrics.get("latency"))
    throughput = _safe_floats(metrics.get("throughput"))
    queue = _safe_floats(metrics.get("queue"))
    avg_load = _safe_floats(metrics.get("avg_load"))
    evidence = _top_evidence(
        evidence_payload,
        limit=max(2, int(min_sources_per_claim)),
        min_score=min_score,
    )

    claims: list[EvidenceClaim] = []
    context = _runtime_context(scenario=scenario, algorithm=algorithm)
    if len(latency) >= 2:
        change = _relative_change(latency)
        improving = change <= -0.10
        base_status = "supported" if improving else "needs-review"
        direction = "decreased" if improving else "did not decrease"
        statement = (
            f"{context}Latency {direction} over the observed run "
            f"({latency[0]:.3f} -> {latency[-1]:.3f}), which informs H1 on adaptive performance."
        )
        claims.append(
            EvidenceClaim(
                claim_id="runtime-H1-latency",
                hypothesis="H1",
                statement=statement,
                evidence=evidence,
                confidence=_confidence(
                    metric_strength=min(1.0, abs(change) * 2.0),
                    evidence=evidence,
                    min_sources=min_sources_per_claim,
                ),
                status=_status(base_status, evidence, min_sources_per_claim),
            )
        )
    else:
        claims.append(
            EvidenceClaim(
                claim_id="runtime-H1-latency",
                hypothesis="H1",
                statement=f"{context}There are not enough latency samples to evaluate H1.",
                evidence=evidence,
                confidence=0.0,
                status="insufficient-data",
            )
        )

    if len(queue) >= 2 and len(throughput) >= 2:
        queue_change = _relative_change(queue)
        throughput_change = _relative_change(throughput)
        stable_or_better = queue_change <= 0.10 and throughput_change >= -0.10
        base_status = "supported" if stable_or_better else "needs-review"
        statement = (
            f"{context}Queue change is {queue_change:+.3f} and throughput change is "
            f"{throughput_change:+.3f}, which informs H2 on MAS robustness and stability."
        )
        claims.append(
            EvidenceClaim(
                claim_id="runtime-H2-stability",
                hypothesis="H2",
                statement=statement,
                evidence=evidence,
                confidence=_confidence(
                    metric_strength=min(1.0, abs(queue_change) + abs(throughput_change)),
                    evidence=evidence,
                    min_sources=min_sources_per_claim,
                ),
                status=_status(base_status, evidence, min_sources_per_claim),
            )
        )

    algorithm_key = str(algorithm or "").lower()
    if any(token in algorithm_key for token in ("ml", "znn", "hybrid")) and avg_load:
        load_mean = fmean(avg_load)
        base_status = "supported" if load_mean <= 0.85 else "needs-review"
        claims.append(
            EvidenceClaim(
                claim_id="runtime-H3-intelligence",
                hypothesis="H3",
                statement=(
                    f"{context}The intelligent mode kept average observed load at {load_mean:.3f}, "
                    "which informs H3 on ML/ZNN-assisted control."
                ),
                evidence=evidence,
                confidence=_confidence(
                    metric_strength=max(0.0, 1.0 - load_mean),
                    evidence=evidence,
                    min_sources=min_sources_per_claim,
                ),
                status=_status(base_status, evidence, min_sources_per_claim),
            )
        )

    claim_rows = [claim.to_dict() for claim in claims]
    gate = validate_claims(
        claim_rows,
        min_sources_per_claim=min_sources_per_claim,
        min_score=min_score,
        required_hypotheses=(),
    )
    return {"claims": claim_rows, "gate": gate}


def _runtime_context(*, scenario: str, algorithm: str) -> str:
    """Build compact runtime context prefix."""
    parts = []
    if scenario:
        parts.append(f"scenario={scenario}")
    if algorithm:
        parts.append(f"algorithm={algorithm}")
    return f"[{', '.join(parts)}] " if parts else ""


def build_report_claims(
    *,
    summary_df: Any,
    hypotheses_df: Any,
    evidence_payload: dict[str, Any] | None,
    min_sources_per_claim: int = 2,
    min_score: float = 0.03,
) -> dict[str, Any]:
    """Build H1-H5 claims from publication/chapter hypotheses and literature evidence."""
    evidence = _top_evidence(
        evidence_payload,
        limit=max(2, int(min_sources_per_claim)),
        min_score=min_score,
    )
    claims: list[EvidenceClaim] = []
    indexed = _hypotheses_by_id(hypotheses_df)
    for hypothesis in REQUIRED_HYPOTHESES:
        row = indexed.get(hypothesis)
        if row is None:
            claims.append(
                EvidenceClaim(
                    claim_id=f"report-{hypothesis}",
                    hypothesis=hypothesis,
                    statement=f"{hypothesis}: no experiment row was available for this hypothesis.",
                    evidence=evidence,
                    confidence=0.0,
                    status="insufficient-data",
                )
            )
            continue
        confirmed = bool(row.get("confirmed", False))
        title = str(row.get("title", hypothesis)).strip() or hypothesis
        criterion = str(row.get("criterion", "")).strip()
        metric_summary = _metric_summary(row)
        status = "supported" if confirmed else "not-supported"
        if len(evidence) < max(1, int(min_sources_per_claim)):
            status = "insufficient-evidence"
        statement = (
            f"{hypothesis} ({title}) is {'confirmed' if confirmed else 'not confirmed'} "
            f"by the current experiment metrics."
        )
        if criterion:
            statement += f" Criterion: {criterion}"
        if metric_summary:
            statement += f" Metrics: {metric_summary}."
        claims.append(
            EvidenceClaim(
                claim_id=f"report-{hypothesis}",
                hypothesis=hypothesis,
                statement=statement,
                evidence=evidence,
                confidence=_report_confidence(
                    confirmed=confirmed,
                    row=row,
                    evidence=evidence,
                    min_sources=min_sources_per_claim,
                ),
                status=status,
            )
        )

    claim_rows = [claim.to_dict() for claim in claims]
    gate = validate_claims(
        claim_rows,
        min_sources_per_claim=min_sources_per_claim,
        min_score=min_score,
        required_hypotheses=REQUIRED_HYPOTHESES,
    )
    gate["summary_row_count"] = _row_count(summary_df)
    return {"claims": claim_rows, "gate": gate}


def _hypotheses_by_id(hypotheses_df: Any) -> dict[str, dict[str, Any]]:
    """Index hypotheses DataFrame-like object by hypothesis id."""
    if getattr(hypotheses_df, "empty", True):
        return {}
    if "hypothesis" not in set(getattr(hypotheses_df, "columns", [])):
        return {}
    records = getattr(hypotheses_df, "to_dict")("records")
    indexed: dict[str, dict[str, Any]] = {}
    for row in records:
        hypothesis = str(row.get("hypothesis", "")).strip()
        if hypothesis:
            indexed[hypothesis] = dict(row)
    return indexed


def _row_count(df: Any) -> int:
    """Return row count for DataFrame-like object."""
    try:
        return int(len(df))
    except Exception:  # noqa: BLE001
        return 0


def _metric_summary(row: dict[str, Any]) -> str:
    """Summarize numeric delta fields from a hypothesis row."""
    parts: list[str] = []
    for key, value in row.items():
        if not str(key).startswith("delta_"):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            parts.append(f"{key}={parsed:+.4f}")
    return ", ".join(parts[:4])


def _report_confidence(
    *,
    confirmed: bool,
    row: dict[str, Any],
    evidence: list[dict[str, Any]],
    min_sources: int,
) -> float:
    """Compute report claim confidence from hypothesis result and evidence quality."""
    deltas: list[float] = []
    for key, value in row.items():
        if not str(key).startswith("delta_"):
            continue
        try:
            parsed = abs(float(value))
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            deltas.append(parsed)
    signal = min(1.0, (fmean(deltas) * 4.0) if deltas else (0.65 if confirmed else 0.35))
    return _confidence(metric_strength=signal, evidence=evidence, min_sources=min_sources)


def validate_claims(
    claims: Sequence[dict[str, Any]],
    *,
    min_sources_per_claim: int = 2,
    min_score: float = 0.03,
    required_hypotheses: Sequence[str] = REQUIRED_HYPOTHESES,
) -> dict[str, Any]:
    """Validate claim schema, evidence coverage, and hypothesis coverage."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    covered: set[str] = set()
    valid_statuses = {"supported", "not-supported", "needs-review", "insufficient-data", "insufficient-evidence"}

    for idx, claim in enumerate(claims):
        claim_id = str(claim.get("claim_id", "")).strip()
        hypothesis = str(claim.get("hypothesis", "")).strip()
        statement = str(claim.get("statement", "")).strip()
        status = str(claim.get("status", "")).strip()
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []

        if not claim_id:
            errors.append(f"Claim {idx}: claim_id is empty.")
        elif claim_id in seen_ids:
            errors.append(f"Claim {idx}: duplicate claim_id '{claim_id}'.")
        seen_ids.add(claim_id)
        if not hypothesis:
            errors.append(f"Claim {idx}: hypothesis is empty.")
        else:
            covered.add(hypothesis)
        if not statement:
            errors.append(f"Claim {idx}: statement is empty.")
        if status not in valid_statuses:
            errors.append(f"Claim {idx}: invalid status '{status}'.")
        try:
            confidence = float(claim.get("confidence", 0.0))
        except (TypeError, ValueError):
            errors.append(f"Claim {idx}: confidence is not numeric.")
            confidence = 0.0
        if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
            errors.append(f"Claim {idx}: confidence must be in [0, 1].")

        if status != "insufficient-data":
            if len(evidence) < max(1, int(min_sources_per_claim)):
                errors.append(
                    f"Claim {claim_id or idx}: expected at least {min_sources_per_claim} evidence sources."
                )
        for ev_idx, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"Claim {claim_id or idx}: evidence {ev_idx} is not an object.")
                continue
            if not str(item.get("article_id", "")).strip():
                errors.append(f"Claim {claim_id or idx}: evidence {ev_idx} missing article_id.")
            if not str(item.get("title", "")).strip():
                errors.append(f"Claim {claim_id or idx}: evidence {ev_idx} missing title.")
            try:
                score = float(item.get("score", 0.0))
            except (TypeError, ValueError):
                errors.append(f"Claim {claim_id or idx}: evidence {ev_idx} score is not numeric.")
                continue
            if not math.isfinite(score) or score < float(min_score):
                errors.append(
                    f"Claim {claim_id or idx}: evidence {ev_idx} score {score:.4f} below {min_score:.4f}."
                )

    missing = sorted(set(required_hypotheses) - covered)
    if missing:
        errors.append(f"Missing hypothesis coverage: {', '.join(missing)}.")

    return {
        "ok": not errors,
        "errors": errors,
        "claim_count": len(list(claims)),
        "covered_hypotheses": sorted(covered),
        "required_hypotheses": list(required_hypotheses),
        "min_sources_per_claim": max(1, int(min_sources_per_claim)),
        "min_score": float(min_score),
    }


def render_markdown_claims(claims: Sequence[dict[str, Any]], *, limit: int = 10) -> list[str]:
    """Render claims as markdown bullet lines with compact citations."""
    lines: list[str] = []
    for claim in list(claims)[: max(1, int(limit))]:
        hypothesis = str(claim.get("hypothesis", "")).strip() or "H?"
        status = str(claim.get("status", "")).strip() or "unknown"
        confidence = float(claim.get("confidence", 0.0) or 0.0)
        statement = str(claim.get("statement", "")).strip()
        citations = _claim_citations(claim.get("evidence", []))
        suffix = f" Evidence: {citations}." if citations else ""
        lines.append(f"- `{hypothesis}` `{status}` confidence={confidence:.2f}: {statement}{suffix}")
    return lines


def _claim_citations(evidence: Any) -> str:
    """Render compact evidence citations for one claim."""
    if not isinstance(evidence, list):
        return ""
    parts: list[str] = []
    for item in evidence[:3]:
        if not isinstance(item, dict):
            continue
        article_id = str(item.get("article_id", "")).strip()
        page = item.get("page", "?")
        if article_id:
            parts.append(f"[{article_id}, p. {page}]")
    return ", ".join(parts)


def write_claims_report(
    path: Path,
    *,
    claims: Sequence[dict[str, Any]],
    gate: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    """Persist claims report JSON and return path as string."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "claims": list(claims),
        "gate": gate,
        "context": context or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)
