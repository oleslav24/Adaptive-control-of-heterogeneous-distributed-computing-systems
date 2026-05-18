"""Helpers for loading eGRID2021 emission factors and resolving node profiles."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
from pathlib import Path

import pandas as pd

from project.core.config import EnergyConfig
from project.core.models import Node

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmissionFactors:
    """Per-region emission factors used for energy/carbon estimation."""

    co2_lb_per_mwh: float
    co2e_lb_per_mwh: float
    renewable_share: float = 0.0
    source: str = "default"


@dataclass(slots=True)
class EGridLookup:
    """In-memory lookup maps for eGRID region levels."""

    srl: dict[str, EmissionFactors]
    ba: dict[str, EmissionFactors]
    us: EmissionFactors | None

    def resolve(
        self,
        *,
        node: Node,
        level: str,
        fallback: EmissionFactors,
    ) -> EmissionFactors:
        """Resolve factors for node and requested region level with fallback."""
        normalized = str(level).strip().lower()
        if normalized == "ba":
            code = str(node.egrid_ba_code).strip().upper()
            if code and code in self.ba:
                return self.ba[code]
            return self.us or fallback
        if normalized == "us":
            return self.us or fallback

        key = str(node.egrid_subregion).strip().upper()
        if key and key in self.srl:
            return self.srl[key]
        return self.us or fallback


def default_factors(config: EnergyConfig) -> EmissionFactors:
    """Build default factors from runtime energy config."""
    co2 = max(0.0, float(config.default_co2_lb_per_mwh))
    co2e = max(co2, float(config.default_co2e_lb_per_mwh))
    return EmissionFactors(
        co2_lb_per_mwh=co2,
        co2e_lb_per_mwh=co2e,
        renewable_share=0.0,
        source="default-config",
    )


def load_lookup(path: str | Path) -> EGridLookup | None:
    """Load eGRID workbook from path and return typed lookup maps."""
    normalized = str(Path(path))
    try:
        return _load_lookup_cached(normalized)
    except Exception as exc:  # pragma: no cover - defensive fallback
        LOGGER.warning("eGRID load failed (%s): %s", normalized, exc)
        return None


@lru_cache(maxsize=4)
def _load_lookup_cached(path: str) -> EGridLookup | None:
    workbook = Path(path)
    if not workbook.exists():
        LOGGER.warning("eGRID dataset path not found: %s", workbook)
        return None
    try:
        excel = pd.ExcelFile(workbook)
    except Exception as exc:  # pragma: no cover - engine/IO variance
        LOGGER.warning("Cannot open eGRID workbook %s: %s", workbook, exc)
        return None

    srl = _load_level(
        excel=excel,
        sheet="SRL21",
        key_tokens=("subregion acronym",),
        co2_tokens=("annual co2 total output emission rate", "lb/mwh"),
        co2e_tokens=("annual co2 equivalent total output emission rate", "lb/mwh"),
        renewable_tokens=("total renewables generation percent",),
        source_name="srl",
    )
    ba = _load_level(
        excel=excel,
        sheet="BA21",
        key_tokens=("balancing authority code",),
        co2_tokens=("annual co2 total output emission rate", "lb/mwh"),
        co2e_tokens=("annual co2 equivalent total output emission rate", "lb/mwh"),
        renewable_tokens=("total renewables generation percent",),
        source_name="ba",
    )
    us = _load_us_level(excel)
    return EGridLookup(srl=srl, ba=ba, us=us)


def _load_level(
    *,
    excel: pd.ExcelFile,
    sheet: str,
    key_tokens: tuple[str, ...],
    co2_tokens: tuple[str, ...],
    co2e_tokens: tuple[str, ...],
    renewable_tokens: tuple[str, ...],
    source_name: str,
) -> dict[str, EmissionFactors]:
    """Load one keyed region sheet (SRL or BA)."""
    df = excel.parse(sheet)
    df = _filter_data_year(df)
    if df.empty:
        return {}

    key_col = _pick_column(df.columns, key_tokens)
    co2_col = _pick_column(df.columns, co2_tokens)
    co2e_col = _pick_column(df.columns, co2e_tokens)
    renewable_col = _pick_column(df.columns, renewable_tokens)
    if key_col is None or co2_col is None:
        return {}

    table: dict[str, EmissionFactors] = {}
    for _, row in df.iterrows():
        key = str(row.get(key_col, "")).strip().upper()
        if not key:
            continue
        co2 = _to_positive_float(row.get(co2_col))
        if co2 is None:
            continue
        co2e = _to_positive_float(row.get(co2e_col)) if co2e_col is not None else None
        renewable = _to_share(row.get(renewable_col)) if renewable_col is not None else 0.0
        table[key] = EmissionFactors(
            co2_lb_per_mwh=co2,
            co2e_lb_per_mwh=co2e if co2e is not None else co2,
            renewable_share=renewable,
            source=f"egrid2021:{source_name}",
        )
    return table


def _load_us_level(excel: pd.ExcelFile) -> EmissionFactors | None:
    """Load US-level fallback factors from US21 sheet."""
    df = excel.parse("US21")
    df = _filter_data_year(df)
    if df.empty:
        return None
    co2_col = _pick_column(df.columns, ("annual co2 total output emission rate", "lb/mwh"))
    co2e_col = _pick_column(
        df.columns, ("annual co2 equivalent total output emission rate", "lb/mwh")
    )
    renewable_col = _pick_column(df.columns, ("total renewables generation percent",))
    if co2_col is None:
        return None
    row = df.iloc[0]
    co2 = _to_positive_float(row.get(co2_col))
    if co2 is None:
        return None
    co2e = _to_positive_float(row.get(co2e_col)) if co2e_col is not None else None
    renewable = _to_share(row.get(renewable_col)) if renewable_col is not None else 0.0
    return EmissionFactors(
        co2_lb_per_mwh=co2,
        co2e_lb_per_mwh=co2e if co2e is not None else co2,
        renewable_share=renewable,
        source="egrid2021:us",
    )


def _filter_data_year(df: pd.DataFrame) -> pd.DataFrame:
    """Drop metadata rows and keep numeric data year entries (prefer 2021)."""
    year_col = _pick_column(df.columns, ("data year",))
    if year_col is None:
        return df
    years = pd.to_numeric(df[year_col], errors="coerce")
    by_2021 = df[years == 2021]
    if not by_2021.empty:
        return by_2021.reset_index(drop=True)
    return df[years.notna()].reset_index(drop=True)


def _pick_column(columns: object, required_tokens: tuple[str, ...]) -> str | None:
    """Pick first column containing all required tokens (case-insensitive)."""
    for item in columns:
        name = str(item).strip().lower()
        if all(token in name for token in required_tokens):
            return str(item)
    return None


def _to_positive_float(value: object) -> float | None:
    """Parse non-negative finite float, dropping invalid and negative values."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not (parsed >= 0.0):
        return None
    return parsed


def _to_share(value: object) -> float:
    """Parse renewable share and normalize from percent to [0,1] when needed."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed > 1.0:
        parsed = parsed / 100.0
    if parsed < 0.0:
        return 0.0
    if parsed > 1.0:
        return 1.0
    return parsed
