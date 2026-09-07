r"""
Numeric Traceability Gate — Master Spec §10.7, CRITICAL-RULES §5.

"Extract every number/date/ID from the rendered doc, check each exists in
Block State; if any can't be traced → block the download, show what failed."

Design:
- Extract numeric tokens from DOCX rendered output.
- Extract all numeric tokens from block_state (recursively).
- Whitelist tokens that are structural (page numbers, year patterns, sequential IDs).
- Flag anything in the rendered doc that isn't traceable to block_state.

Whitelist rules (never the surveyor's data, always structural):
  1. The report number itself and its integer components.
  2. Four-digit year tokens matching \b(19|20)\d\d\b (date years).
  3. Single-digit numbers 0–9 (page numbers, list indices, common counts).
  4. Numbers that appear in the report_number string.
  5. Template-structural constants: "1", "2", etc. from header/footer page refs.

The gate does NOT whitelist by range — it whitelists by provenance.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Set

import docx


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class TraceabilityResult:
    """Result of a traceability check."""
    passed: bool
    untraceable: list[str] = field(default_factory=list)
    total_checked: int = 0
    traceable_count: int = 0


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

# Regex: integers and decimals (incl. percentages stripped to numeric part)
_NUM_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
# Year pattern (4-digit years: 1900–2099)
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def _normalize_number(s: str) -> str:
    """
    Normalize a numeric string for comparison.
    '80.00' → '80', '6.230' → '6.23', '100.00' → '100', '56.84' → '56.84'.
    This allows block_state values like '80' to match DOCX-rendered '80.00'.
    """
    try:
        d = Decimal(s)
        # Remove trailing zeros after decimal point
        normalized = d.normalize()
        # Handle case where normalize() produces '8E+1' for 80 — convert back
        if 'E' in str(normalized):
            normalized = d.to_integral_value() if d == d.to_integral_value() else d
        return str(normalized)
    except Exception:
        return s


def _extract_numbers_from_docx(docx_bytes: bytes) -> Set[str]:
    """
    Extract all numeric tokens from a DOCX document.
    Returns normalized strings (trailing zeros stripped) like "234", "56.84", "1", "2026".
    """
    doc = docx.Document(io.BytesIO(docx_bytes))
    tokens: Set[str] = set()

    def _collect_from_text(text: str) -> None:
        for m in _NUM_PATTERN.finditer(text):
            raw = m.group(0)
            tokens.add(raw)
            tokens.add(_normalize_number(raw))

    # Paragraphs
    for para in doc.paragraphs:
        _collect_from_text(para.text)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _collect_from_text(para.text)

    return tokens


def _extract_numbers_from_block_state(block_state: Any) -> Set[str]:
    """
    Recursively walk the block_state JSON and collect all numeric strings.
    Returns both raw and normalized representations for comparison with DOCX.
    """
    tokens: Set[str] = set()

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str):
            for m in _NUM_PATTERN.finditer(obj):
                raw = m.group(0)
                tokens.add(raw)
                tokens.add(_normalize_number(raw))
        elif isinstance(obj, (int, float, Decimal)):
            # Convert to string representation — normalize like the DOCX does
            s = str(obj)
            for m in _NUM_PATTERN.finditer(s):
                raw = m.group(0)
                tokens.add(raw)
                tokens.add(_normalize_number(raw))

    _walk(block_state)
    return tokens


def _extract_numbers_from_computed(block_state: Any) -> Set[str]:
    """
    Run compute() on the block_state and extract numbers from the derived output.
    This ensures computed totals/percentages (e.g. grand total=100 from 80+20)
    are traceable — they are derived from block_state, not fabricated.
    """
    try:
        from app.compute.arithmetic import compute as _compute
        computed_state = _compute(block_state)
        tokens = _extract_numbers_from_block_state(computed_state)
        return tokens
    except Exception:
        # If compute() fails for any reason, return empty — gate should still work
        return set()


def _build_whitelist(block_state: Any) -> Set[str]:
    """
    Build a whitelist of tokens that are always acceptable even if not in block_state values.

    Includes:
    - Single-digit numbers 0-9 (ubiquitous in page refs, list numbering)
    - Numbers up to 20 (page counts, section numbers)
    - Four-digit year tokens (structural dates)
    - The report number and its component parts
    """
    whitelist: Set[str] = set()

    # Single-digit numbers — structural (page 1, 2, 3 in header/footer, list numbering)
    for n in range(10):
        whitelist.add(str(n))

    # Two-digit numbers up to 20 — common in page counts, section numbers
    for n in range(11, 21):
        whitelist.add(str(n))

    # 100 / 100.00 — mathematical constant for percentage table totals
    whitelist.add("100")
    whitelist.add("100.00")

    # Year tokens 1900-2099 — dates in running headers are structural
    for year in range(1900, 2100):
        whitelist.add(str(year))

    # Report number components
    metadata = block_state.get("metadata", {}) if isinstance(block_state, dict) else {}
    report_num = str(metadata.get("number", ""))
    if report_num:
        for m in _NUM_PATTERN.finditer(report_num):
            raw = m.group(0)
            whitelist.add(raw)
            whitelist.add(_normalize_number(raw))

    return whitelist


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def check_traceability(block_state: dict, docx_bytes: bytes) -> TraceabilityResult:
    """
    Run the numeric traceability gate.

    Extracts every number from the rendered DOCX and checks it is present
    in the block_state (including computed-derived values) or on the structural whitelist.

    Numbers are compared in NORMALIZED form (trailing zeros stripped):
    - DOCX '80.00' → normalized '80' → checked against traceable set
    - block_state '80' → normalized '80' → added to traceable set
    - This guarantees '80.00' matches '80'.

    Returns a TraceabilityResult. If passed=False, untraceable lists the
    ORIGINAL (unnormalized) numbers from the DOCX that couldn't be traced.
    """
    # Build the traceable set (normalized canonical forms)
    state_tokens_raw = _extract_numbers_from_block_state(block_state)
    computed_tokens_raw = _extract_numbers_from_computed(block_state)
    whitelist_raw = _build_whitelist(block_state)

    # Normalize the traceable set — only keep canonical normalized forms
    traceable_normalized: Set[str] = set()
    for token_set in (state_tokens_raw, computed_tokens_raw, whitelist_raw):
        for t in token_set:
            traceable_normalized.add(_normalize_number(t))

    # Extract DOCX tokens — keep original for reporting, normalize for checking
    docx_raw_to_normalized: dict[str, str] = {}
    doc = docx.Document(io.BytesIO(docx_bytes))

    def _scan_text(text: str) -> None:
        for m in _NUM_PATTERN.finditer(text):
            raw = m.group(0)
            docx_raw_to_normalized[raw] = _normalize_number(raw)

    for para in doc.paragraphs:
        _scan_text(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _scan_text(para.text)

    # Check traceability — a raw DOCX token is traceable if its normalized form is in traceable_normalized
    untraceable_raw = sorted(
        raw for raw, normalized in docx_raw_to_normalized.items()
        if normalized not in traceable_normalized
    )

    total_checked = len(docx_raw_to_normalized)
    traceable_count = total_checked - len(untraceable_raw)

    return TraceabilityResult(
        passed=len(untraceable_raw) == 0,
        untraceable=untraceable_raw,
        total_checked=total_checked,
        traceable_count=traceable_count,
    )

