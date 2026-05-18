"""Unit tests for eGRID lookup/fallback helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from project.core.config import EnergyConfig
from project.core.models import Node
from project.metrics.egrid_loader import EmissionFactors, default_factors, load_lookup


def test_load_lookup_resolves_srl_ba_and_us_fallbacks() -> None:
    """Lookup should parse workbook and resolve SRL/BA with US fallback."""
    root = _workspace_dir("egrid-loader")
    workbook = root / "mini_egrid.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            [
                {
                    "Data Year": "YEAR",
                    "eGRID subregion acronym": "SUBRGN",
                    "eGRID subregion annual CO2 total output emission rate (lb/MWh)": "SRCO2RTA",
                    "eGRID subregion annual CO2 equivalent total output emission rate (lb/MWh)": "SRC2ERTA",
                    "eGRID subregion total renewables generation percent (resource mix)": "SRTRPR",
                },
                {
                    "Data Year": 2021,
                    "eGRID subregion acronym": "CAMX",
                    "eGRID subregion annual CO2 total output emission rate (lb/MWh)": 531.678,
                    "eGRID subregion annual CO2 equivalent total output emission rate (lb/MWh)": 540.0,
                    "eGRID subregion total renewables generation percent (resource mix)": 0.39,
                },
            ]
        ).to_excel(writer, sheet_name="SRL21", index=False)
        pd.DataFrame(
            [
                {
                    "Data Year": "YEAR",
                    "Balancing Authority Code": "BACODE",
                    "BA annual CO2 total output emission rate (lb/MWh)": "BACO2RTA",
                    "BA annual CO2 equivalent total output emission rate (lb/MWh)": "BAC2ERTA",
                    "BA total renewables generation percent (resource mix)": "BATRPR",
                },
                {
                    "Data Year": 2021,
                    "Balancing Authority Code": "AZPS",
                    "BA annual CO2 total output emission rate (lb/MWh)": 1554.253,
                    "BA annual CO2 equivalent total output emission rate (lb/MWh)": 1580.0,
                    "BA total renewables generation percent (resource mix)": 0.150764,
                },
            ]
        ).to_excel(writer, sheet_name="BA21", index=False)
        pd.DataFrame(
            [
                {
                    "Data Year": "YEAR",
                    "U.S. annual CO2 total output emission rate (lb/MWh)": "USCO2RTA",
                    "U.S. annual CO2 equivalent total output emission rate (lb/MWh)": "USC2ERTA",
                    "U.S. total renewables generation percent (resource mix)": "USTRPR",
                },
                {
                    "Data Year": 2021,
                    "U.S. annual CO2 total output emission rate (lb/MWh)": 900.0,
                    "U.S. annual CO2 equivalent total output emission rate (lb/MWh)": 940.0,
                    "U.S. total renewables generation percent (resource mix)": 0.20,
                },
            ]
        ).to_excel(writer, sheet_name="US21", index=False)

    lookup = load_lookup(workbook)
    assert lookup is not None

    fallback = EmissionFactors(co2_lb_per_mwh=800.0, co2e_lb_per_mwh=820.0)
    srl_node = Node(id="n1", cpu=8.0, memory=16.0, gpu=0.0, egrid_subregion="CAMX")
    ba_node = Node(id="n2", cpu=8.0, memory=16.0, gpu=0.0, egrid_ba_code="AZPS")
    unknown_node = Node(id="n3", cpu=8.0, memory=16.0, gpu=0.0, egrid_subregion="UNKNOWN")

    srl = lookup.resolve(node=srl_node, level="srl", fallback=fallback)
    ba = lookup.resolve(node=ba_node, level="ba", fallback=fallback)
    unknown = lookup.resolve(node=unknown_node, level="srl", fallback=fallback)

    assert abs(srl.co2_lb_per_mwh - 531.678) < 1e-9
    assert abs(ba.co2_lb_per_mwh - 1554.253) < 1e-9
    assert abs(unknown.co2_lb_per_mwh - 900.0) < 1e-9


def test_load_lookup_missing_file_returns_none_and_defaults_are_stable() -> None:
    """Missing workbook should gracefully return None and use config defaults."""
    lookup = load_lookup("data/DataSet/_missing_egrid.xlsx")
    assert lookup is None

    factors = default_factors(EnergyConfig())
    assert factors.co2_lb_per_mwh == 855.0
    assert factors.co2e_lb_per_mwh == 900.0


def _workspace_dir(suffix: str) -> Path:
    """Create unique writable test directory under outputs/test-suite."""
    root = Path("outputs") / "test-suite" / f"{suffix}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root
