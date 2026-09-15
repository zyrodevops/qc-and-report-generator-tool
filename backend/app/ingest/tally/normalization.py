"""
Numeric Normalization Module — OCR_IMPLEMENTATION.md §10.

Constrained type normalization for table values:
- Integer counts (SOUND, RUSSET, SOFT, ROTTEN, COUNT, etc.)
- Decimal measurements (TEMPS, BRIX, PRESSURE, WEIGHT)
Handles common OCR digit confusions (O->0, I/l->1, S->5) without blind replacement.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple


class NumericNormalizer:
    """Normalizes raw OCR text into verified typed values."""

    @staticmethod
    def normalize_integer(raw_text: str) -> Tuple[Optional[int], bool, bool]:
        """
        Normalizes a string expected to be a positive integer count.
        Returns: (normalized_val, normalization_applied, is_ambiguous)
        """
        cleaned = raw_text.strip()
        if not cleaned or cleaned in ["-", "--", "—", "nil", "NIL", "none", "None"]:
            return 0, False, False

        # Check if already a pure integer
        if cleaned.isdigit():
            return int(cleaned), False, False

        # Apply constrained character fixes
        norm = cleaned.upper()
        # Common OCR digit confusions
        norm = norm.replace("O", "0").replace("D", "0").replace("Q", "0")
        norm = norm.replace("I", "1").replace("L", "1").replace("|", "1").replace("!", "1")
        norm = norm.replace("Z", "2")
        norm = norm.replace("S", "5")
        norm = norm.replace("B", "8")
        norm = norm.replace("G", "6")

        # Strip spaces and accidental punctuation like periods or commas in integer cells
        digits_only = re.sub(r"[^\d]", "", norm)
        if digits_only.isdigit():
            val = int(digits_only)
            return val, True, False

        # If it contains ambiguous characters or cannot be resolved
        return None, False, True

    @staticmethod
    def normalize_decimal(raw_text: str) -> Tuple[Optional[Decimal], bool, bool]:
        """
        Normalizes a string expected to be a decimal measurement.
        Returns: (normalized_val, normalization_applied, is_ambiguous)
        """
        cleaned = raw_text.strip()
        if not cleaned:
            return None, False, False

        # Fix comma used as decimal separator, e.g. "4,85" -> "4.85"
        norm = cleaned.replace(",", ".")
        norm = norm.upper().replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5")

        # Extract decimal number
        m = re.search(r"[-+]?\d*\.?\d+", norm)
        if m:
            try:
                dec = Decimal(m.group(0))
                applied = norm != cleaned
                return dec, applied, False
            except (InvalidOperation, ValueError):
                pass

        return None, False, True

    @staticmethod
    def normalize_range(raw_text: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Parses ranges like '3.3 to 4.5', '0.8 - 1.4', '15.03 to 17.59'."""
        cleaned = raw_text.strip().replace(",", ".")
        # Match "min to max" or "min - max"
        m = re.search(r"([-+]?\d*\.?\d+)\s*(?:to|-|–|—)\s*([-+]?\d*\.?\d+)", cleaned, re.IGNORECASE)
        if m:
            try:
                val1 = Decimal(m.group(1))
                val2 = Decimal(m.group(2))
                return min(val1, val2), max(val1, val2)
            except Exception:
                pass

        # Single number
        m_single = re.search(r"[-+]?\d*\.?\d+", cleaned)
        if m_single:
            try:
                d = Decimal(m_single.group(0))
                return d, d
            except Exception:
                pass

        return None, None

    @staticmethod
    def normalize_caliber_label(raw_text: str, fallback_idx: int = 0) -> str:
        """
        Decodes fruit counts (calibers: 20-200) and export quality grades (XF, PR, CAT 1, etc.)
        from physical tally sheets (DEVELOPER_WORKFLOW_AND_INSTRUCTIONS.md §3).
        E.g.:
          '30 XF' -> 'Count 30 XF'
          '33 PR' -> 'Count 33 PR'
          '30XF'  -> 'Count 30 XF'
          'Count 36' -> 'Count 36'
          '72' -> 'Count 72'
        """
        cleaned = raw_text.strip()
        if not cleaned:
            return f"Sample Box #{fallback_idx + 1}"

        # Match count number + optional grade (XF, PR, CAT 1, FANCY, PREMIUM, EXTRA FANCY)
        m = re.search(
            r"(?:(?:count|size|ct)\.?\s*)?(\d{2,3})\s*([A-Za-z]+(?:\s*\d)?)?",
            cleaned,
            re.IGNORECASE,
        )
        if m:
            cnt = m.group(1)
            grade_raw = (m.group(2) or "").strip().upper()
            grade = ""
            if "XF" in grade_raw or "EXTRA" in grade_raw:
                grade = " XF"
            elif "PR" in grade_raw or "PREM" in grade_raw:
                grade = " PR"
            elif "CAT" in grade_raw:
                grade = f" {grade_raw}"
            elif grade_raw:
                grade = f" {grade_raw}"
            return f"Count {cnt}{grade}"

        return cleaned

