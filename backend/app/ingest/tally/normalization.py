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

    # Marks a surveyor writes to mean "none of this defect in this box".
    _EXPLICIT_NIL = {"-", "--", "---", "—", "–", "0", "nil", "none", "x", "/"}

    # Letters OCR routinely returns in place of these digits on handwriting.
    _CONFUSIONS = {
        "O": "0", "D": "0", "Q": "0",
        "I": "1", "L": "1", "|": "1", "!": "1",
        "Z": "2", "S": "5", "B": "8", "G": "6",
    }

    @classmethod
    def normalize_integer(cls, raw_text: str) -> Tuple[Optional[int], bool, bool]:
        """
        Normalise a cell expected to hold a count.

        Returns (value, normalisation_applied, is_ambiguous), where a value of
        None means the cell could not be read and must be filled in by hand.

        A cell OCR returned nothing for is NOT treated as zero. On a tally sheet
        a blank usually does mean none, but OCR returns the same empty string
        when it fails on a cell that had a number in it, and the two cannot be
        told apart from the text alone. Guessing zero would silently move every
        percentage in the finished report. An explicit nil mark the surveyor
        wrote — a dash, a stroke, the word nil — is unambiguous and is read as
        zero.
        """
        cleaned = raw_text.strip()

        if not cleaned:
            return None, False, True

        if cleaned.lower() in cls._EXPLICIT_NIL:
            return 0, False, False

        if cleaned.isdigit():
            # Counts are per sampled box. A reading this long is far more likely
            # to be two adjacent cells run together than a real count, and
            # accepting it would wreck the row total in a way that looks like a
            # data-entry error rather than a misread.
            if len(cleaned) > 4:
                return None, False, True
            return int(cleaned), False, False

        # Only attempt digit repair when every character is either a digit, a
        # letter OCR is known to confuse for one, or separator noise. Otherwise
        # a genuine word gets mangled into a number: without this guard 'ABC'
        # normalises to 8, because B maps to 8 and the rest is stripped away.
        upper = cleaned.upper()
        allowed = set(cls._CONFUSIONS) | set("0123456789") | set(" .,'\"")
        if any(ch not in allowed for ch in upper):
            return None, False, True

        norm = "".join(cls._CONFUSIONS.get(ch, ch) for ch in upper)
        digits_only = re.sub(r"[^\d]", "", norm)
        if not digits_only:
            return None, False, True

        # Counts on a tally sheet are per sampled box; a five-digit reading is
        # far more likely to be two cells run together than a real count.
        if len(digits_only) > 4:
            return None, False, True

        return int(digits_only), True, False

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

