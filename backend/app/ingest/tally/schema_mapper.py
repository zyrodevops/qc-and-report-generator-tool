"""
Schema Mapping and Header Normalization Module — OCR_IMPLEMENTATION.md §8.

Maps printed and handwritten table headers to canonical defect categories:
- sound, soft, russet, rotten, puffed, green_patch, silver_scurf, oil_spot, mech, bruised, shriveled, etc.
Extracts and normalizes metadata headers:
- container_number, party_name, dates, room_no, environmental QC readings.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


CANONICAL_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "sound": {"label": "Sound", "aliases": ["sound", "sd", "sound fruit", "sound fruit count"]},
    "soft": {"label": "Soft", "aliases": ["soft", "sft", "soft fruit"]},
    "russet": {"label": "Russet", "aliases": ["russet", "rst", "russeting", "russetting"]},
    "rotten": {"label": "Rotten", "aliases": ["rotten", "rot", "decay", "fungal", "fungus"]},
    "puffed": {"label": "Puffed Fruit", "aliases": ["puffed", "puffed fruit", "puff"]},
    "green_patch": {"label": "Green Patch", "aliases": ["green patch", "green", "greenish", "grn patch"]},
    "silver_scurf": {"label": "Silver Scurf", "aliases": ["silver scurf", "silver", "scurf", "slv scurf"]},
    "oil_spot": {"label": "Oil Spot", "aliases": ["oil spot", "oil spots", "oleocellosis"]},
    "mech": {"label": "Mechanical Injury", "aliases": ["mech", "mechanical", "mech injury", "cut", "scratch"]},
    "bruised": {"label": "Bruised", "aliases": ["bruised", "bruise", "bruising", "impact"]},
    "shriveled": {"label": "Shriveled", "aliases": ["shriveled", "shrivelled", "shrivel", "wilting"]},
    "lemon_colour": {"label": "Lemon Colour", "aliases": ["lemon colour", "lemon color", "yellowish"]},
    "stem_crack": {"label": "Stem Crack", "aliases": ["stem crack", "crack", "split"]},
    "pitted": {"label": "Pitted", "aliases": ["pitted", "pitting"]},
}


class SchemaMapper:
    """Matches text labels to canonical report fields and categories."""

    @classmethod
    def match_category(cls, raw_header: str) -> Optional[Tuple[str, str]]:
        """
        Matches a raw header string to (canonical_key, display_label).
        Returns None if not a recognized defect category (e.g. 'Count', 'Total', 'Sr').
        """
        clean = re.sub(r"[^a-zA-Z\s]", " ", raw_header).strip().lower()
        if not clean:
            return None

        # Check exact and substring aliases
        for key, info in CANONICAL_CATEGORIES.items():
            for alias in info["aliases"]:
                if clean == alias or (len(alias) > 3 and alias in clean):
                    return key, info["label"]

        return None

    @staticmethod
    def is_count_header(raw_header: str) -> bool:
        clean = raw_header.strip().lower()
        return any(k in clean for k in ["count", "size", "cnt", "grade", "group", "item"])

    @staticmethod
    def is_total_header(raw_header: str) -> bool:
        clean = raw_header.strip().lower()
        return any(k in clean for k in ["total", "tot", "sum"])

    @staticmethod
    def clean_container_number(s: str) -> Optional[str]:
        """Extracts and formats ISO 6346 container number (4 letters + 7 digits)."""
        cleaned = re.sub(r"(?<=\d)[.\-_](?=\d)", "", s)
        m = re.search(r"\b([A-Za-z]{4})[\s.\-_]*([0-9SOIZL]{7})\b", cleaned, re.IGNORECASE)
        if not m:
            m = re.search(r"([A-Za-z]{4})[\s.\-_]*([0-9SOIZL]{6,7})", cleaned, re.IGNORECASE)
        if not m:
            return None
        pfx = m.group(1).upper()
        digits = m.group(2).upper()
        digits = digits.replace("S", "5").replace("O", "0").replace("I", "1").replace("Z", "2").replace("L", "1")
        return pfx + digits

    @staticmethod
    def clean_date(s: str) -> Optional[str]:
        """Converts DD/MM/YYYY, DD-MM-YYYY, or DD MM YYYY to ISO YYYY-MM-DD."""
        s_norm = s.replace("|", "/").replace("\\", "/")
        s_norm = re.sub(r"(?<=\d)\s+(?=\d)", "/", s_norm)
        m = re.search(r"\b(0?[1-9]|[12]\d|3[01])[./\-]0?([1-9]|1[012])[./\-](\d{2,4})\b", s_norm)
        if not m:
            return None
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def clean_room_number(s: str) -> Optional[str]:
        """Extracts room identifier e.g. '05', 'C5-10', 'C5-11 & C5-20'."""
        m = re.search(r"(?:ROOM\s*(?:NO\.?|NUMBER)?\s*[:\-_]?\s*)([A-Z0-9\-&\s]{1,15})", s, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Avoid picking up full sentences
            val = re.split(r"[\n\r]|(?:\b(?:TEMP|TEMPERATURE|DATE|TIME)\b)", val, flags=re.IGNORECASE)[0].strip()
            if val and val.upper() not in ["NO", "NUMBER", "ROOM"]:
                return val
        return None

