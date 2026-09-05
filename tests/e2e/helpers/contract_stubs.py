"""
Contract inspection, reference algorithms, and progressive capability detection.
Enables tests to run opaque-box verification against the backend implementations as they arrive,
with reference oracle functions for differential validation.
"""

from decimal import Decimal, ROUND_HALF_UP
import importlib
import math
from typing import Dict, Any, List, Optional, Tuple, Callable


# ---------------------------------------------------------------------------
# Dynamic Capability Detection (Progressive Testability)
# ---------------------------------------------------------------------------

def try_import(module_path: str):
    """Safely attempts to import a backend module; returns module or None."""
    import sys
    from pathlib import Path
    backend_root = str(Path(__file__).resolve().parent.parent.parent.parent / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    candidates = [module_path]
    if module_path.startswith("backend.app."):
        candidates.insert(0, module_path.replace("backend.app.", "app.", 1))
    elif module_path == "backend.app":
        candidates.insert(0, "app")

    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            if mod_name.startswith("app"):
                sys.modules.setdefault("backend." + mod_name, mod)
            return mod
        except (ImportError, ModuleNotFoundError):
            continue
    return None


def get_backend_compute():
    """Returns backend compute function or None."""
    mod = try_import("backend.app.compute.engine") or try_import("backend.app.compute.arithmetic")
    if mod and hasattr(mod, "compute"):
        return mod.compute
    return None


def get_photo_ranges_fn():
    """Returns backend photo_ranges function or None."""
    mod = try_import("backend.app.compute.photo_ranges")
    if mod and hasattr(mod, "compute_photo_ranges"):
        return mod.compute_photo_ranges
    return None


def get_spreadsheet_parser():
    """Returns backend spreadsheet ingest function or None."""
    mod = try_import("backend.app.ingest.spreadsheet")
    if mod and hasattr(mod, "parse_spreadsheet"):
        return mod.parse_spreadsheet
    return None


def get_docx_renderer():
    """Returns backend docx renderer or None."""
    mod = try_import("backend.app.render.docx.engine") or try_import("backend.app.render.docx")
    if mod and hasattr(mod, "render_docx"):
        return mod.render_docx
    return None


def get_traceability_gate():
    """Returns backend numeric traceability gate or None."""
    mod = try_import("backend.app.render.gate")
    if mod and hasattr(mod, "verify_numeric_traceability"):
        return mod.verify_numeric_traceability
    return None


# ---------------------------------------------------------------------------
# Authoritative Reference Algorithms (Test Oracle)
# ---------------------------------------------------------------------------

def hare_niemeyer_balance(exact_pcts: List[Decimal], target_sum: Decimal = Decimal("100.00")) -> List[Decimal]:
    """
    Hare-Niemeyer (Largest Remainder Method / Hamilton Method) for percentage balancing.
    Guarantees that rounded percentage components sum exactly to 100.00%.
    1. Floor each percentage to 2 decimal places.
    2. Compute the deficit = target_sum - sum(floors).
    3. Distribute +0.01 to components with the largest fractional remainders (exact - floor).
    """
    from decimal import ROUND_FLOOR
    floors = [p.quantize(Decimal("0.01"), rounding=ROUND_FLOOR) for p in exact_pcts]
    total_floor = sum(floors)
    deficit = int(((target_sum - total_floor) * 100).to_integral_value())

    if deficit <= 0:
        return floors

    # Compute fractional remainders: exact - floor
    remainders = [(exact_pcts[i] - floors[i], i) for i in range(len(exact_pcts))]
    # Sort descending by remainder; break ties by original index
    remainders.sort(key=lambda x: (-x[0], x[1]))

    for j in range(min(deficit, len(floors))):
        idx = remainders[j][1]
        floors[idx] += Decimal("0.01")

    return floors


def reference_compute_table(
    rows: List[Dict[str, Any]],
    categories: List[str],
    precision: str = "0.01"
) -> Dict[str, Any]:
    """
    Pure reference implementation of table calculations per Master-Spec §10.4 & §10.8.
    All calculations strictly use Decimal and ROUND_HALF_UP.
    """
    quantizer = Decimal(precision)
    row_totals: List[Decimal] = []
    row_pcts: List[List[Decimal]] = []
    col_totals: Dict[str, Decimal] = {cat: Decimal("0") for cat in categories}

    for row in rows:
        row_sum = Decimal("0")
        cat_vals: List[Decimal] = []
        for cat in categories:
            val_raw = row.get("values", {}).get(cat, 0)
            val = Decimal(str(val_raw))
            cat_vals.append(val)
            row_sum += val
            col_totals[cat] += val

        row_totals.append(row_sum)
        if row_sum > Decimal("0"):
            raw_row_pcts = [(v / row_sum) * Decimal("100") for v in cat_vals]
            balanced_row_pcts = hare_niemeyer_balance(raw_row_pcts)
        else:
            balanced_row_pcts = [Decimal("0.00") for _ in categories]
        row_pcts.append(balanced_row_pcts)

    grand_total = sum(col_totals.values())
    if grand_total > Decimal("0"):
        raw_col_pcts = [(col_totals[cat] / grand_total) * Decimal("100") for cat in categories]
        balanced_col_pcts = hare_niemeyer_balance(raw_col_pcts)
    else:
        balanced_col_pcts = [Decimal("0.00") for _ in categories]

    return {
        "row_totals": row_totals,
        "row_percentages": row_pcts,
        "column_totals": col_totals,
        "grand_total": grand_total,
        "column_percentages": {cat: balanced_col_pcts[i] for i, cat in enumerate(categories)}
    }


def reference_photo_ranges(groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pure reference implementation of photo_ranges.py per Master-Spec §10.2 & ORIGINAL_REQUEST §R5.
    Output: single -> '(Photo No. 50)', pair -> '(Photo Nos. 39 & 40)', range -> '(Photo Nos. 55 to 59)'
    Asserts: contiguity, exhaustiveness, no empty groups, no duplicate photos across groups.
    """
    all_seen = set()
    current_number = 1
    group_results = {}

    for g in groups:
        gid = g["id"]
        assets = g.get("asset_ids", [])
        if not assets:
            raise AssertionError(f"Photo group {gid} is empty; every group must contain at least 1 photo.")
        
        group_photos = []
        for aid in assets:
            if aid in all_seen:
                raise AssertionError(f"Photo {aid} appears in multiple photo groups; duplicate found.")
            all_seen.add(aid)
            group_photos.append(current_number)
            current_number += 1

        start_no = group_photos[0]
        end_no = group_photos[-1]
        count = len(group_photos)

        if count == 1:
            label = f"(Photo No. {start_no})"
        elif count == 2:
            label = f"(Photo Nos. {start_no} & {end_no})"
        else:
            label = f"(Photo Nos. {start_no} to {end_no})"

        group_results[gid] = {
            "start": start_no,
            "end": end_no,
            "count": count,
            "photo_numbers": group_photos,
            "label": label
        }

    return group_results


def reference_air_weights(
    length_cm: float,
    width_cm: float,
    height_cm: float,
    actual_gross_kg: Decimal,
    pieces: int = 1,
    divisor: int = 6000
) -> Tuple[Decimal, Decimal]:
    """
    IATA Volumetric and Chargeable Weight calculation.
    volumetric = (L * W * H * pieces) / 6000 cm³/kg
    chargeable = max(actual, volumetric)
    """
    vol_cm3 = Decimal(str(length_cm)) * Decimal(str(width_cm)) * Decimal(str(height_cm)) * Decimal(str(pieces))
    volumetric_kg = (vol_cm3 / Decimal(str(divisor))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    chargeable_kg = max(actual_gross_kg, volumetric_kg)
    return volumetric_kg, chargeable_kg


def reference_cfs_reconciliation(
    gross_kg: Decimal,
    container_tare_kg: Decimal,
    trailer_tare_kg: Optional[Decimal],
    formula: str,
    declared_net_kg: Decimal
) -> Dict[str, Any]:
    """
    CFS weighbridge reconciliation formulas per Master-Spec §10.4.
    Formula 1: GROSS_MINUS_COMBINED_TARE -> gross - (trailer + container tare)
    Formula 2: GROSS_MINUS_TRAILER_MINUS_CONTAINER -> gross - trailer_tare - container_tare
    Formula 3: GROSS_MINUS_CONTAINER_TARE -> gross - container_tare
    """
    if formula == "GROSS_MINUS_CONTAINER_TARE":
        found_net = gross_kg - container_tare_kg
    elif formula == "GROSS_MINUS_COMBINED_TARE":
        if trailer_tare_kg is None:
            raise ValueError("Trailer tare required for GROSS_MINUS_COMBINED_TARE")
        found_net = gross_kg - (trailer_tare_kg + container_tare_kg)
    elif formula == "GROSS_MINUS_TRAILER_MINUS_CONTAINER":
        if trailer_tare_kg is None:
            raise ValueError("Trailer tare required for GROSS_MINUS_TRAILER_MINUS_CONTAINER")
        found_net = gross_kg - trailer_tare_kg - container_tare_kg
    else:
        raise ValueError(f"Unknown reconciliation formula: {formula}")

    diff = found_net - declared_net_kg
    direction = "EXCESS" if diff > 0 else ("SHORTAGE" if diff < 0 else "TIED")

    return {
        "found_net_kg": found_net,
        "difference_kg": abs(diff),
        "direction": direction,
        "is_discrepancy": diff != Decimal("0")
    }
