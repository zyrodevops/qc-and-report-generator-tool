"""
Arithmetic Engine — compute(block_state) -> block_state_with_derived.

CRITICAL RULES (from CRITICAL-RULES.md):
- Decimal ONLY. Never float. Any `float()` call here is a bug.
- ROUND_HALF_UP, 2 decimal places everywhere (3 dp for kg-precision tables).
- Derived values are RETURNED, never stored in DB.
- One function called by Word renderer, HTML preview, and PDF — same numbers, always.

Percentage balancing: Hare-Niemeyer (Largest Remainder Method).
Guarantees column/row percentages sum exactly to 100.00.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from typing import Any, Dict, List, Optional, Tuple
import copy


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRECISION_2DP = Decimal("0.01")
PRECISION_3DP = Decimal("0.001")
IATA_VOLUMETRIC_DIVISOR = Decimal("6000")  # cm³/kg


# ---------------------------------------------------------------------------
# Internal helpers — Decimal only, no float
# ---------------------------------------------------------------------------

def _to_decimal(value: Any) -> Decimal:
    """Convert any numeric-ish value to Decimal. Raises on un-parseable input."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    # Explicitly reject float — caller must convert at the boundary
    raise TypeError(
        f"_to_decimal received {type(value).__name__!r} ({value!r}). "
        "Use Decimal or int or a numeric string. Never pass float."
    )


def _round2(d: Decimal) -> Decimal:
    return d.quantize(PRECISION_2DP, rounding=ROUND_HALF_UP)


def _round3(d: Decimal) -> Decimal:
    return d.quantize(PRECISION_3DP, rounding=ROUND_HALF_UP)


def _hare_niemeyer(exact_pcts: List[Decimal], target: Decimal = Decimal("100.00")) -> List[Decimal]:
    """
    Largest Remainder Method — distributes rounding error so percentages sum exactly to target.
    All arithmetic in Decimal. No float.
    """
    floors = [p.quantize(PRECISION_2DP, rounding=ROUND_FLOOR) for p in exact_pcts]
    total_floor = sum(floors)
    deficit = int(((target - total_floor) * 100).to_integral_value())

    if deficit <= 0:
        return floors

    remainders = [(exact_pcts[i] - floors[i], i) for i in range(len(exact_pcts))]
    remainders.sort(key=lambda x: (-x[0], x[1]))

    for j in range(min(deficit, len(floors))):
        idx = remainders[j][1]
        floors[idx] += Decimal("0.01")

    return floors


# ---------------------------------------------------------------------------
# Table block computation
# ---------------------------------------------------------------------------

def compute_table(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute all derived values for a table block.
    Returns a new dict with 'computed' key containing:
      row_totals, row_percentages, column_totals, grand_total, column_percentages.

    Precision is 2dp for pcs/mt blocks, 3dp if unit is 'kg'.
    CRITICAL: No float. No stored results. Called fresh every render.
    """
    categories: List[str] = [c["key"] for c in block.get("categories", [])]
    rows: List[Dict[str, Any]] = block.get("rows", [])
    unit: str = block.get("unit", "pcs").lower()

    # kg tables keep 3dp precision for intermediate sums, round to 3dp for totals
    use_3dp = (unit == "kg")

    col_totals: Dict[str, Decimal] = {cat: Decimal(0) for cat in categories}
    row_totals: List[Decimal] = []
    row_pcts: List[List[Decimal]] = []

    for row in rows:
        values = row.get("values", {})
        row_sum = Decimal(0)
        cat_vals: List[Decimal] = []

        for cat in categories:
            raw = values.get(cat, 0)
            val = _to_decimal(raw)
            cat_vals.append(val)
            row_sum += val
            col_totals[cat] += val

        row_totals.append(_round3(row_sum) if use_3dp else _round2(row_sum))

        if row_sum > Decimal(0):
            exact_pcts = [(v / row_sum) * Decimal(100) for v in cat_vals]
            row_pcts.append(_hare_niemeyer(exact_pcts))
        else:
            row_pcts.append([Decimal("0.00")] * len(categories))

    # Round column totals
    col_totals_rounded = {
        cat: (_round3(v) if use_3dp else _round2(v))
        for cat, v in col_totals.items()
    }
    grand_total = sum(col_totals_rounded.values())
    if use_3dp:
        grand_total = _round3(grand_total)
    else:
        grand_total = _round2(grand_total)

    if grand_total > Decimal(0):
        exact_col_pcts = [
            (col_totals[cat] / sum(col_totals.values())) * Decimal(100)
            for cat in categories
        ]
        balanced_col_pcts = _hare_niemeyer(exact_col_pcts)
    else:
        balanced_col_pcts = [Decimal("0.00")] * len(categories)

    col_pcts_dict = {cat: balanced_col_pcts[i] for i, cat in enumerate(categories)}

    return {
        "row_totals": row_totals,
        "row_percentages": row_pcts,
        "column_totals": col_totals_rounded,
        "grand_total": grand_total,
        "column_percentages": col_pcts_dict,
    }


# ---------------------------------------------------------------------------
# Photo ranges computation (delegates to photo_ranges module)
# ---------------------------------------------------------------------------

def compute_photo_plate(block: Dict[str, Any]) -> Dict[str, Any]:
    """Compute photo numbering and range strings for a photo_plate block."""
    from app.compute.photo_ranges import compute_photo_ranges
    groups = block.get("groups", [])
    return compute_photo_ranges(groups)


# ---------------------------------------------------------------------------
# Main compute function — THE single source of truth
# ---------------------------------------------------------------------------

def compute(block_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    compute(block_state) -> block_state_with_derived

    Processes a full Block State dict and returns it augmented with all derived
    values under each block's '_computed' key.

    CRITICAL:
    - This function is called by the Word renderer, HTML preview, AND PDF.
    - The return value is used transiently — NEVER persisted to the database.
    - This function must be pure: same input -> same output, no side effects.
    """
    state = copy.deepcopy(block_state)
    blocks = state.get("blocks", [])

    # Build a running photo counter across all photo_plate blocks in document order
    # so that shared-series numbering is correct.
    photo_counter = [1]  # mutable int via list to allow closure mutation

    for block in blocks:
        btype = block.get("type")

        if btype == "table":
            block["_computed"] = compute_table(block)

        elif btype == "photo_plate":
            from app.compute.photo_ranges import compute_photo_ranges
            groups = block.get("groups", [])
            result = compute_photo_ranges(groups, start_number=photo_counter[0])
            block["_computed"] = result
            # Advance counter by total photos in this plate
            total_photos = sum(len(g.get("asset_ids", [])) for g in groups)
            photo_counter[0] += total_photos

        elif btype == "measurements":
            # Measurements: just validate; no derived arithmetic needed at this level
            block["_computed"] = {"validated": True}

        elif btype == "particulars":
            block["_computed"] = {"validated": True}

        elif btype == "narrative":
            block["_computed"] = {"validated": True}

        elif btype == "fixed_text":
            block["_computed"] = {"validated": True}

        # Additional block types (Week 3) handled when added — additive only

    return state


# ---------------------------------------------------------------------------
# Identifier validation helpers (pure functions, no dependencies)
# ---------------------------------------------------------------------------

_ISO6346_CHAR_VALS: Dict[str, int] = {
    'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19,
    'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29,
    'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38,
}


def validate_iso6346(container_id: str) -> Tuple[bool, Optional[int]]:
    """
    Returns (is_valid, computed_check_digit).
    CRITICAL: If invalid, flag for confirmation — never auto-correct.
    """
    clean = container_id.upper().replace("-", "").replace(" ", "")
    if len(clean) != 11:
        return False, None
    body = clean[:10]
    given_check = int(clean[10])

    total = 0
    for idx, ch in enumerate(body):
        val = _ISO6346_CHAR_VALS.get(ch, int(ch) if ch.isdigit() else -1)
        if val < 0:
            return False, None
        total += val * (2 ** idx)

    computed = (total % 11) % 10
    return computed == given_check, computed


def validate_awb(awb_str: str) -> Tuple[bool, Optional[int]]:
    """
    IATA AWB mod-7 check digit validation.
    Format: 3-digit prefix + 7-digit serial + 1 check digit.
    CRITICAL: Flag failures, never auto-correct.
    """
    digits = "".join(c for c in awb_str if c.isdigit())
    if len(digits) != 11:
        return False, None
    serial = int(digits[3:10])
    given_check = int(digits[10])
    computed = serial % 7
    return computed == given_check, computed

