"""
Liability Regimes and Notice Periods Reference Data — Master Spec §6, §14 (Day 14).

CRITICAL RULES:
- Never hardcode a legal figure in report prose.
- Held as versioned reference data with an effective date.
- Shows figure and source to surveyor; requires explicit confirmation before render.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel


class RegimeReference(BaseModel):
    regime_id: str
    instrument: str
    transport_mode: str               # "SEA" or "AIR"
    effective_date: str
    limit_sdr_per_kg: Optional[Decimal] = None
    limit_sdr_per_package: Optional[Decimal] = None
    damage_notice_days: int
    delay_notice_days: Optional[int] = None
    source_citation: str


# Versioned liability regimes table
REGIMES_2026_01: Dict[str, RegimeReference] = {
    "hague_visby_cogsa": RegimeReference(
        regime_id="hague_visby_cogsa",
        instrument="Hague-Visby Rules / Carriage of Goods by Sea Act (India)",
        transport_mode="SEA",
        effective_date="2026-01-01",
        limit_sdr_per_kg=Decimal("2.00"),
        limit_sdr_per_package=Decimal("666.67"),
        damage_notice_days=3,
        delay_notice_days=None,
        source_citation="Hague-Visby Rules Protocol 1979 Art IV Rule 5; COGSA 1925",
    ),
    "montreal_1999": RegimeReference(
        regime_id="montreal_1999",
        instrument="Montreal Convention 1999 (ICAO / Carriage by Air Act, India)",
        transport_mode="AIR",
        effective_date="2026-01-01",
        limit_sdr_per_kg=Decimal("22.00"),
        limit_sdr_per_package=None,
        damage_notice_days=14,
        delay_notice_days=21,
        source_citation="Montreal Convention 1999 Art 22(3) as revised; Indian Carriage by Air Act Sch III",
    ),
    "hamburg_rules": RegimeReference(
        regime_id="hamburg_rules",
        instrument="Hamburg Rules 1978 (United Nations Convention on the Carriage of Goods by Sea)",
        transport_mode="SEA",
        effective_date="2026-01-01",
        limit_sdr_per_kg=Decimal("2.50"),
        limit_sdr_per_package=Decimal("835.00"),
        damage_notice_days=1,
        delay_notice_days=60,
        source_citation="Hamburg Rules Art 6(1)(a)",
    ),
}


def get_liability_regime(regime_id: str, version: str = "regimes@2026-01") -> Optional[RegimeReference]:
    """Retrieve regime specification by ID."""
    if version == "regimes@2026-01":
        return REGIMES_2026_01.get(regime_id)
    return None


def confirm_regime(
    regime_id: str,
    surveyor_name: str,
    version: str = "regimes@2026-01",
) -> Dict[str, Any]:
    """
    Format regime dictionary for block_state.transport.liability_regime
    with surveyor confirmation metadata.
    """
    ref = get_liability_regime(regime_id, version)
    if not ref:
        raise ValueError(f"Unknown regime {regime_id} for version {version}")

    return {
        "instrument": ref.instrument,
        "limit_basis": "sdr_per_kg" if ref.limit_sdr_per_package is None else "package_or_kg",
        "limit_sdr_per_kg": str(ref.limit_sdr_per_kg) if ref.limit_sdr_per_kg else None,
        "limit_sdr_per_package": str(ref.limit_sdr_per_package) if ref.limit_sdr_per_package else None,
        "notice_period_days": ref.damage_notice_days,
        "delay_notice_days": ref.delay_notice_days,
        "reference_version": version,
        "confirmed_by": surveyor_name,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "source": ref.source_citation,
    }
