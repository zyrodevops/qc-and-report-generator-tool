"""
Cold Chain Instruments Ingestion — Master Spec §11.1, Week 2 R5.

Parses plain text / PDF extracts from cold storage temperature loggers
(DeltaTrak, Escavox, Sensitech).
Extracts min, max, average temperatures and readings without hardcoded
arbitrary 'spike' heuristics (CRITICAL-RULES §3: never auto-correct or auto-interpret).
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional


_TEMP_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?\s*(?:°C|deg\s*C|°F|deg\s*F|C|F)?\b")


def parse_temperature_log(raw_text: str) -> Dict[str, Any]:
    """
    Parses temperature readings from raw text report (page 1 text / OCR text).
    Extracts summary statistics (min, max, average) using Decimal arithmetic.
    Does NOT infer 'temperature spikes' or liability (Master Spec §11.1).
    """
    # Look for explicit summary markers first
    min_match = re.search(r"(?:min(?:imum)?|lowest)[:\s]+([-+]?\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)
    max_match = re.search(r"(?:max(?:imum)?|highest)[:\s]+([-+]?\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)
    avg_match = re.search(r"(?:avg|average|mean)[:\s]+([-+]?\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)

    unit = "°C"
    if "°F" in raw_text or "deg F" in raw_text:
        unit = "°F"

    min_val = Decimal(min_match.group(1)) if min_match else None
    max_val = Decimal(max_match.group(1)) if max_match else None
    avg_val = Decimal(avg_match.group(1)) if avg_match else None

    # Fallback: parse all temperature float/decimal tokens if summary markers not present
    if min_val is None or max_val is None:
        readings = []
        for m in re.finditer(r"([-+]?\d+\.\d+)\s*(?:°C|C)?", raw_text):
            try:
                readings.append(Decimal(m.group(1)))
            except Exception:
                pass
        if readings:
            min_val = min(readings)
            max_val = max(readings)
            if avg_val is None:
                avg_val = (sum(readings) / Decimal(len(readings))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

    return {
        "unit": unit,
        "min_temperature": str(min_val) if min_val is not None else None,
        "max_temperature": str(max_val) if max_val is not None else None,
        "average_temperature": str(avg_val) if avg_val is not None else None,
        "excursion_flagged": False,  # Never auto-flag spikes; surveyor interprets
    }


def parse_deltrak(raw_text: str) -> Dict[str, Any]:
    """DeltaTrak specific adapter calling parse_temperature_log."""
    return parse_temperature_log(raw_text)

