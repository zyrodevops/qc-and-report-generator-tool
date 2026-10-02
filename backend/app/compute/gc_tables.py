"""
General cargo tables: what the surveyor enters, and what is worked out from it.

In a survey paragraph (one container or visit):
  - weighbridge: gross weight of truck + container + cargo, less the truck's
    and the container's tare, is the cargo's found weight; less the weight as
    per the B/L (or packing list), the shortage or excess.
  - tally: quantity as per the document, found sound, found damaged; the
    shortage or excess.
  - damage table: see general_cargo.findings_rows.
For the report:
  - WEIGHT FINAL SUMMARY: each weighed container's weights and the totals,
    after the last survey paragraph, when two or more were weighed.
  - containers and seals: the seal number as per the B/L against the one
    found; whether they tally.
  - weather: place, date, rainfall, temperature.
  - SUMMARY OF RESERVE: the items and their invoice values, and the total.

The layout of each (its rows and columns) is from the client's and the
archive's reports. The figures are formatted once here, and the same strings
are printed, so the check on printed numbers finds each of them in the report.
Nothing is filled in that the surveyor did not enter or that is not worked
out from what he entered.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple


def num(v: Any) -> Optional[Decimal]:
    s = str(v if v is not None else "").replace(",", "").replace(" ", "").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def fmt(d: Decimal) -> str:
    """12345.5 -> "12,345.5"; whole numbers without decimals; at most 3 decimals."""
    q = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    s = f"{q:,.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def signed(d: Decimal) -> str:
    return ("+" if d > 0 else "") + fmt(d)


def _clean(v: Any) -> str:
    return " ".join(str(v if v is not None else "").split())


# ---------------------------------------------------------------------------
# Weighbridge (a survey paragraph)
# ---------------------------------------------------------------------------

WEIGHT_COLUMNS = ["Particulars", "Weight (kg)"]
# The document the weight is compared with, named in full in the table.
BASIS_NAMES = {"B/L": "Bill of Lading"}


def weighbridge(unit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The weighbridge table's rows and the found / declared / difference figures; None when nothing was weighed."""
    w = unit.get("weights") or {}
    if w.get("included") is False:
        return None
    gross, tare_truck, tare_cont, declared = (num(w.get(k)) for k in ("gross", "tare_truck", "tare_container", "declared"))
    if gross is None and declared is None:
        return None
    basis = _clean(w.get("basis")) or "B/L"
    rows: List[List[str]] = []
    # The rows as the client's reports word them.
    if _clean(w.get("weighbridge")):
        rows.append(["Weighbridge", _clean(w.get("weighbridge"))])
    slip = " dated ".join(x for x in (_clean(w.get("slip_no")), _clean(w.get("date"))) if x)
    if slip:
        rows.append(["Weight Slip No. and date", slip])
    found = None
    if gross is not None:
        what = ("container + cargo + trailer" if tare_truck is not None
                else "container + cargo" if tare_cont is not None else "cargo")
        rows.append([f"Gross weight found of {what}", fmt(gross)])
        if tare_truck is not None:
            rows.append(["Less: Tare weight of trailer", fmt(tare_truck)])
        if tare_cont is not None:
            rows.append(["Less: Marked tare weight of container", fmt(tare_cont)])
        found = gross - (tare_truck or 0) - (tare_cont or 0)
        if tare_truck is not None or tare_cont is not None:
            rows.append(["Found gross weight of cargo", fmt(found)])
    if declared is not None:
        rows.append([f"Less: Gross weight of cargo as per {BASIS_NAMES.get(basis, basis)}", fmt(declared)])
    diff = found - declared if found is not None and declared is not None else None
    if diff is not None:
        label = "Difference (shortage)" if diff < 0 else "Difference (excess)" if diff > 0 else "Difference"
        rows.append([label, fmt(abs(diff))])
    return {"rows": rows, "found": found, "declared": declared, "diff": diff, "basis": basis}


# ---------------------------------------------------------------------------
# Tally (a survey paragraph)
# ---------------------------------------------------------------------------

def tally(unit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Quantity as per the document against what was found; None when there is no tally."""
    t = unit.get("tally") or {}
    if t.get("included") is False:
        return None
    basis = _clean(t.get("basis")) or "Packing List"
    columns = ["Description", f"As per {basis}", "Found sound", "Found damaged", "Shortage (-) / excess (+)"]
    rows: List[List[str]] = []
    totals = [Decimal(0)] * 4
    counted = [False] * 4
    for r in t.get("rows") or []:
        item = _clean(r.get("item"))
        vals = [num(r.get(k)) for k in ("document", "sound", "damaged")]
        if not item and all(v is None for v in vals):
            continue
        doc, sound, damaged = vals
        diff = (sound or 0) + (damaged or 0) - doc if doc is not None and (sound is not None or damaged is not None) else None
        cells = [item] + [fmt(v) if v is not None else "" for v in vals] + [signed(diff) if diff is not None else ""]
        rows.append(cells)
        for i, v in enumerate(vals + [diff]):
            if v is not None:
                totals[i] += v
                counted[i] = True
    if not rows:
        return None
    if len(rows) > 1:
        rows.append(["Total"] + [(signed(v) if i == 3 else fmt(v)) if counted[i] else "" for i, v in enumerate(totals)])
    return {"columns": columns, "rows": rows, "total": len(rows) > 1}


# ---------------------------------------------------------------------------
# WEIGHT FINAL SUMMARY (the report)
# ---------------------------------------------------------------------------

def weight_summary(blocks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Each weighed container's weights and the totals; None unless two or more were weighed."""
    items: List[Tuple[str, Decimal, Decimal]] = []
    basis = "B/L"
    units = [b for b in blocks if b.get("type") == "survey_unit" and b.get("included") is not False]
    for n, u in enumerate(units, start=1):
        w = weighbridge(u)
        if not w or w["found"] is None or w["declared"] is None:
            continue
        basis = w["basis"]
        items.append((_clean(u.get("container")) or f"Survey {n}", w["declared"], w["found"]))
    if len(items) < 2:
        return None
    # In the client's order: the weight ascertained, the weight as per the document, the difference.
    columns = ["Container No.", "Ascertained weight (kg)", f"Weight as per {basis} (kg)", "Shortage (-) / excess (+) (kg)"]
    rows = [[label, fmt(found), fmt(dec), signed(found - dec)] for label, dec, found in items]
    tot_dec = sum((d for _l, d, _f in items), Decimal(0))
    tot_found = sum((f for _l, _d, f in items), Decimal(0))
    rows.append(["Total", fmt(tot_found), fmt(tot_dec), signed(tot_found - tot_dec)])
    return {"title": "WEIGHT FINAL SUMMARY", "columns": columns, "rows": rows}


# ---------------------------------------------------------------------------
# Report tables: containers & seals, weather, summary of reserve
# ---------------------------------------------------------------------------

TABLE_KINDS = ("seals", "weather", "reserve")


def _norm_seal(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


def report_table(block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A report table's title (or none), columns and rows as printed; None when it has no rows."""
    kind = block.get("kind")
    rows_in = block.get("rows") or []
    title = ""
    if kind == "seals":
        columns = ["Container No.", "Size / Type", "Seal No. as per B/L", "Seal No. found", "Tallies"]
        rows = []
        for r in rows_in:
            cells = [_clean(r.get(k)) for k in ("container", "size", "seal_doc", "seal_found")]
            if not any(cells):
                continue
            doc, found = cells[2], cells[3]
            tallies = ("Yes" if _norm_seal(doc) == _norm_seal(found) else "No") if doc and found else ""
            rows.append(cells + [tallies])
    elif kind == "weather":
        columns = ["Place", "Date", "Rainfall", "Max / Min temperature"]
        rows = [c for c in ([_clean(r.get(k)) for k in ("place", "date", "rainfall", "temperature")] for r in rows_in) if any(c)]
    elif kind == "reserve":
        title = "SUMMARY OF RESERVE"
        currency = _clean(block.get("currency"))
        columns = ["Description", "Quantity", f"Invoice value ({currency})" if currency else "Invoice value"]
        rows = []
        total = Decimal(0)
        any_value = False
        for r in rows_in:
            desc, qty = _clean(r.get("description")), _clean(r.get("quantity"))
            value = num(r.get("value"))
            if not desc and not qty and value is None:
                continue
            rows.append([desc, qty, fmt(value) if value is not None else _clean(r.get("value"))])
            if value is not None:
                total += value
                any_value = True
        if rows and any_value:
            rows.append(["Total", "", fmt(total)])
    else:
        return None
    if not rows:
        return None
    return {"title": title, "columns": columns, "rows": rows, "total": kind == "reserve" and rows[-1][0] == "Total"}


# ---------------------------------------------------------------------------
# Where the tables go in a survey paragraph's text
# ---------------------------------------------------------------------------

# A line holding one of these marks puts that table there; a table with no
# mark goes after the text, in this order.
UNIT_TABLE_MARKS = {"(damage table)": "damage", "(tally table)": "tally", "(weight table)": "weights"}
UNIT_TABLE_ORDER = ("damage", "tally", "weights")


def unit_segments(text: str) -> List[Tuple[str, str]]:
    """The paragraph's text as [("text", ...), ("table", key), ...], every table placed once."""
    out: List[Tuple[str, str]] = []
    buf: List[str] = []
    placed = set()
    for line in (text or "").split("\n"):
        key = UNIT_TABLE_MARKS.get(line.strip().lower())
        if key and key not in placed:
            out.append(("text", "\n".join(buf).strip("\n")))
            out.append(("table", key))
            placed.add(key)
            buf = []
        else:
            buf.append(line)
    out.append(("text", "\n".join(buf).strip("\n")))
    out += [("table", k) for k in UNIT_TABLE_ORDER if k not in placed]
    return out


def unit_table(unit: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """One of a survey paragraph's tables as printed: {"columns", "rows", "total"}; None when empty."""
    if key == "damage":
        from app.seeds.general_cargo import DAMAGE_TABLE_COLUMNS, findings_rows
        rows = findings_rows(unit)
        return {"columns": DAMAGE_TABLE_COLUMNS, "rows": rows, "total": False} if rows else None
    if key == "tally":
        return tally(unit)
    if key == "weights":
        w = weighbridge(unit)
        return {"columns": WEIGHT_COLUMNS, "rows": w["rows"], "total": False} if w and w["rows"] else None
    return None
