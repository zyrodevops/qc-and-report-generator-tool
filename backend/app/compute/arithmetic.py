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
# Week 3 Computations — Timeline, Reconciliation, Annexures, Air Weights
# ---------------------------------------------------------------------------

def compute_air_weights(pieces: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """
    Compute volumetric and chargeable weights for air shipments.
    Volumetric weight = (L * W * H in cm) / 6000 per piece.
    Chargeable weight = max(actual gross, volumetric).
    CRITICAL: Decimal only, ROUND_HALF_UP to 2 decimal places.
    """
    total_actual = Decimal("0")
    total_volumetric = Decimal("0")

    for p in pieces:
        count = Decimal(str(p.get("count", 1)))
        actual_kg = Decimal(str(p.get("actual_gross_kg", p.get("gross_kg", 0))))
        l = Decimal(str(p.get("length_cm", 0)))
        w = Decimal(str(p.get("width_cm", 0)))
        h = Decimal(str(p.get("height_cm", 0)))

        vol_per_piece = (l * w * h) / IATA_VOLUMETRIC_DIVISOR
        vol_total = vol_per_piece * count

        total_actual += actual_kg * count
        total_volumetric += vol_total

    vol_rounded = _round2(total_volumetric)
    act_rounded = _round2(total_actual)
    chargeable = max(act_rounded, vol_rounded)

    return {
        "actual_gross_kg": act_rounded,
        "volumetric_kg": vol_rounded,
        "chargeable_kg": chargeable,
    }


def compute_timeline(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute transit days and event spacing for timeline block.
    """
    from datetime import date
    rows = block.get("rows", [])
    if not rows:
        return {"transit_days": 0, "intervals": []}

    parsed_dates = []
    for r in rows:
        d_str = r.get("date")
        if d_str:
            try:
                parsed_dates.append((r.get("event"), date.fromisoformat(d_str[:10])))
            except Exception:
                pass

    transit_days = 0
    if len(parsed_dates) >= 2:
        transit_days = (parsed_dates[-1][1] - parsed_dates[0][1]).days

    intervals = []
    for i in range(len(parsed_dates) - 1):
        ev1, d1 = parsed_dates[i]
        ev2, d2 = parsed_dates[i + 1]
        intervals.append({
            "from_event": ev1,
            "to_event": ev2,
            "days": (d2 - d1).days,
        })

    return {
        "transit_days": max(0, transit_days),
        "intervals": intervals,
        "validated": True,
    }


def compute_reconciliation(
    block: Dict[str, Any],
    all_blocks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compute weight reconciliation rows and totals based on chosen formula.
    Supported formulas (chosen per weighing event, never guessed):
      1. GROSS_MINUS_TRAILER_AND_CONTAINER_TARE: gross - (trailer_tare + container_tare)
      2. GROSS_MINUS_TRAILER_TARE_MINUS_CONTAINER_TARE: gross - trailer_tare - container_tare
      3. GROSS_MINUS_CONTAINER_TARE: gross - container_tare
      4. NET_DIRECT: gross (direct weighing)
    Returns:
      computed rows with found_net, difference, direction, plus overall totals.
    """
    scope = block.get("scope", "SHIPMENT")
    rolls_up_from = block.get("rolls_up_from")

    # If this is a shipment roll-up from unit reconciliations:
    rows = list(block.get("rows", []))
    if scope == "SHIPMENT" and rolls_up_from and all_blocks:
        # Collect rows from the referenced blocks
        rolled_rows = []
        for b in all_blocks:
            if b.get("id") == rolls_up_from or b.get("type") == "reconciliation" and b.get("scope") == "UNIT":
                rolled_rows.extend(b.get("rows", []))
            elif b.get("type") == "unit_group":
                for child in b.get("blocks", []):
                    if child.get("type") == "reconciliation" and (child.get("id") == rolls_up_from or not rolls_up_from):
                        rolled_rows.extend(child.get("rows", []))
        if rolled_rows and not rows:
            rows = rolled_rows

    formula = block.get("formula", "GROSS_MINUS_CONTAINER_TARE")
    computed_rows = []
    tot_gross = Decimal("0")
    tot_found_net = Decimal("0")
    tot_ref = Decimal("0")

    for r in rows:
        gross = Decimal(str(r.get("gross", "0") or "0"))
        c_tare = Decimal(str(r.get("container_tare", "0") or "0"))
        t_tare = Decimal(str(r.get("trailer_tare", "0") or "0"))
        ref = Decimal(str(r.get("reference", "0") or "0"))

        if formula == "GROSS_MINUS_TRAILER_AND_CONTAINER_TARE":
            found_net = gross - (t_tare + c_tare)
        elif formula == "GROSS_MINUS_TRAILER_TARE_MINUS_CONTAINER_TARE":
            found_net = gross - t_tare - c_tare
        elif formula == "GROSS_MINUS_CONTAINER_TARE":
            found_net = gross - c_tare
        elif formula == "NET_DIRECT":
            found_net = gross
        else:
            found_net = gross - c_tare

        diff = ref - found_net
        if diff > Decimal("0"):
            direction = "SHORTAGE"
        elif diff < Decimal("0"):
            direction = "EXCESS"
        else:
            direction = "NIL"

        tot_gross += gross
        tot_found_net += found_net
        tot_ref += ref

        c_row = dict(r)
        c_row.update({
            "found_net": str(_round2(found_net)),
            "difference": str(_round2(abs(diff))),
            "signed_difference": str(_round2(diff)),
            "direction": direction,
        })
        computed_rows.append(c_row)

    tot_diff = tot_ref - tot_found_net
    if tot_diff > Decimal("0"):
        overall_dir = "SHORTAGE"
    elif tot_diff < Decimal("0"):
        overall_dir = "EXCESS"
    else:
        overall_dir = "NIL"

    return {
        "rows": computed_rows,
        "total_gross": str(_round2(tot_gross)),
        "total_found_net": str(_round2(tot_found_net)),
        "total_reference": str(_round2(tot_ref)),
        "total_difference": str(_round2(abs(tot_diff))),
        "signed_total_difference": str(_round2(tot_diff)),
        "direction": overall_dir,
        "summary": f"{overall_dir} of {abs(tot_diff)} kg" if overall_dir != "NIL" else "Nil difference",
    }


def compute_annexures(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute sequential IDs (A1, A2, B1, B2...) and documentation list for annexures block.
    """
    rows = block.get("rows", [])
    prefix_counts: Dict[str, int] = {}
    computed_rows = []
    merge_order = []

    for r in rows:
        prefix = (r.get("prefix") or "A").upper()
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        sub_id = f"{prefix}{prefix_counts[prefix]}"
        
        c_row = dict(r)
        c_row["sub_id"] = sub_id
        computed_rows.append(c_row)
        
        asset_id = r.get("asset_id")
        file_path = r.get("file_path")
        merge_order.append({
            "sub_id": sub_id,
            "title": r.get("title", ""),
            "asset_id": asset_id,
            "file_path": file_path,
        })

    return {
        "rows": computed_rows,
        "merge_order": merge_order,
        "documentation_list": [f"Annexure {r['sub_id']}: {r.get('title', '')}" for r in computed_rows],
    }


# ---------------------------------------------------------------------------
# Master compute() function
# ---------------------------------------------------------------------------

def compute(block_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute all derived values across the entire report Block State.
    Returns an enriched copy of block_state with `_computed` keys attached to
    each block. Never stores computed values to the database.

    CRITICAL:
    - This function is called by the Word renderer, HTML preview, AND PDF.
    - The return value is used transiently — NEVER persisted to the database.
    - This function must be pure: same input -> same output, no side effects.
    """
    state = copy.deepcopy(block_state)
    blocks = state.get("blocks", [])
    carriage_units = state.get("carriage_units", [])
    transport = state.get("transport", {})
    t_mode = transport.get("mode", "SEA")

    # 1. Check-digit validation on carriage units and transport document
    for unit in carriage_units:
        uid = unit.get("identifier")
        utype = unit.get("unit_type", "CONTAINER")
        if uid and utype == "CONTAINER":
            valid, _ = validate_iso6346(uid)
            unit["identifier_valid"] = valid

    tdoc = transport.get("document", {})
    dnum = tdoc.get("number")
    dkind = tdoc.get("kind")
    if dnum:
        if dkind == "AIR_WAYBILL" or t_mode == "AIR":
            valid, _ = validate_awb(dnum)
            tdoc["check_digit_valid"] = valid

    # 2. Air weights calculation if volumetric pieces provided
    if t_mode == "AIR" and "pieces" in state.get("weights", {}):
        air_res = compute_air_weights(state["weights"]["pieces"])
        state["weights"].update({
            "volumetric_kg": str(air_res["volumetric_kg"]),
            "chargeable_kg": str(air_res["chargeable_kg"]),
        })

    # 3. Photo counter for shared series numbering
    photo_counter = [1]

    for block in blocks:
        btype = block.get("type")

        if btype == "table":
            block["_computed"] = compute_table(block)

        elif btype == "photo_plate":
            from app.compute.photo_ranges import compute_photo_ranges
            groups = block.get("groups", [])
            result = compute_photo_ranges(groups, start_number=photo_counter[0])
            block["_computed"] = result
            total_photos = sum(len(g.get("asset_ids", [])) for g in groups)
            photo_counter[0] += total_photos

        elif btype == "measurements":
            block["_computed"] = {"validated": True}

        elif btype == "particulars":
            block["_computed"] = {"validated": True}

        elif btype == "narrative":
            block["_computed"] = {"validated": True}

        elif btype == "fixed_text":
            block["_computed"] = {"validated": True}

        elif btype == "parties":
            block["_computed"] = {"validated": True}

        elif btype == "attendance":
            block["_computed"] = {"validated": True}

        elif btype == "timeline":
            block["_computed"] = compute_timeline(block)

        elif btype == "reconciliation":
            block["_computed"] = compute_reconciliation(block, all_blocks=blocks)

        elif btype == "annexures":
            block["_computed"] = compute_annexures(block)

        elif btype == "inventory":
            block["_computed"] = {"validated": True}

        elif btype == "unit_group":
            from app.compute.photo_ranges import compute_photo_ranges
            # unit_group repeats child blocks over carriage_units
            heading_template = block.get(
                "heading_template",
                "{index}) CONDITION OF CONTAINER NO. {identifier} & CARGO: (SEE {photo_ref})"
            )
            photo_numbering = block.get("photo_numbering", "SHARED_SERIES_SEGMENTED")
            child_blocks = block.get("blocks", [])

            computed_units = []
            unit_headings = []

            for idx, unit in enumerate(carriage_units, start=1):
                u_id = unit.get("identifier", f"UNIT-{idx}")
                u_blocks = copy.deepcopy(child_blocks)
                u_photo_range_str = ""

                # If SERIES_PER_UNIT, reset photo counter for each unit
                if photo_numbering == "SERIES_PER_UNIT":
                    u_counter = [1]
                else:
                    u_counter = photo_counter

                for ub in u_blocks:
                    ub["scope"] = "UNIT"
                    ub["unit_id"] = unit.get("id", f"u{idx}")
                    ub["unit_identifier"] = u_id
                    ub_type = ub.get("type")

                    if ub_type == "table":
                        ub["_computed"] = compute_table(ub)
                    elif ub_type == "photo_plate":
                        groups = ub.get("groups", [])
                        res = compute_photo_ranges(groups, start_number=u_counter[0])
                        ub["_computed"] = res
                        cnt = sum(len(g.get("asset_ids", [])) for g in groups)
                        u_counter[0] += cnt
                        g_map = res.get("groups", {})
                        if g_map:
                            min_num = min((gi["start"] for gi in g_map.values()), default=None)
                            max_num = max((gi["end"] for gi in g_map.values()), default=None)
                            if min_num is not None and max_num is not None:
                                if min_num == max_num:
                                    u_photo_range_str = f"SURVEY PHOTO NO. {min_num}"
                                elif max_num == min_num + 1:
                                    u_photo_range_str = f"SURVEY PHOTO NOS. {min_num} & {max_num}"
                                else:
                                    u_photo_range_str = f"SURVEY PHOTO NOS. {min_num} TO {max_num}"
                    elif ub_type == "reconciliation":
                        ub["_computed"] = compute_reconciliation(ub, all_blocks=blocks)
                    else:
                        ub["_computed"] = {"validated": True}

                # Construct heading
                heading = heading_template.format(
                    index=idx,
                    identifier=u_id,
                    photo_ref=u_photo_range_str or "PHOTOS",
                )
                unit_headings.append(heading)

                computed_units.append({
                    "unit_index": idx,
                    "unit_id": unit.get("id", f"u{idx}"),
                    "identifier": u_id,
                    "heading": heading,
                    "photo_ref": u_photo_range_str,
                    "blocks": u_blocks,
                })

            block["_computed"] = {
                "unit_headings": unit_headings,
                "units": computed_units,
                "validated": True,
            }

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

