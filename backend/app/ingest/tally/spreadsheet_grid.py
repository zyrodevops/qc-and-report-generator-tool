"""
Turn an uploaded CSV or Excel tally into the same grid the workbench checks.

The cold store often sends the tally as a spreadsheet rather than a photograph
of the notebook. That is the easier path — the figures are already typed — but
it is not a safe one by default, because the column headings are whatever the
cold store called them and they will not line up with the fruit's columns.

The import used to guess: for each of the report's defect columns it looked for
a spreadsheet column of the same name, and wrote a zero when it did not find
one. A sheet whose heading read "Rotten Fruits" against a column keyed "rotten"
produced a zero, and a zero is a real count of nothing that changes every
percentage in the report. It also only ever read the first five rows, because
the endpoint returned a five-row preview and the caller treated it as the data.

So: every column is matched where the name allows it, and anything left over is
handed to the surveyor to map or discard. Nothing becomes a zero on its own.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from app.ingest.spreadsheet import parse_spreadsheet
from app.ingest.tally.categories import (
    build_categories,
    is_label_header,
    is_total_header,
    match_header_to_category,
    unit_for,
)
from app.ingest.tally.validation import ValidationEngine

# Headers that identify the row rather than hold a count.
_ROW_LABEL_HINTS = ("count", "size", "caliber", "calibre", "grade", "group",
                    "sample", "item", "variety", "sr", "sr.no", "srno", "s.no")
# Weighed fruit is tallied one line per box, so the box number is the label.
# Matched whole, so a "No. of Boxes" count column is not taken for it.
_ROW_LABEL_EXACT = ("box", "box no", "box no.", "box #", "carton", "carton no", "carton no.")


def _to_figure(raw: Any, unit: str = "pcs") -> Optional[Any]:
    """
    A cell's value: a whole count for pieces, a 3-dp Decimal for kg.
    None when the cell does not hold one.

    Blank stays None rather than becoming zero: the spreadsheet may simply not
    have that column filled in for that row, and guessing changes the totals.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text in ("-", "--", "—", "–") or text.lower() in ("nil", "none", "na", "n/a"):
        return Decimal("0.000") if unit == "kg" else 0

    if unit == "kg":
        # Spreadsheet cells are clean numbers: 0.82, 1.932, 4.226.
        try:
            d = Decimal(text.replace(" ", ""))
        except InvalidOperation:
            return None
        return d.quantize(Decimal("0.001")) if 0 <= d <= 1000 else None

    cleaned = text.replace(",", "").replace(" ", "")
    if re.fullmatch(r"\d+", cleaned):
        return int(cleaned)
    # Spreadsheets often hold counts as floats: 142.0
    if re.fullmatch(r"\d+\.0*", cleaned):
        return int(float(cleaned))
    return None


# Kept for callers that only ever deal in counts.
def _to_int(raw: Any) -> Optional[int]:
    v = _to_figure(raw, "pcs")
    return v if isinstance(v, int) else None


# Words a cold store uses to label a line it worked out rather than counted.
_DERIVED_LABELS = ("percentage", "percent", "%", "total", "grand total", "sum", "average", "avg")


def _is_derived_row(label: str, raw: Dict[str, Any], unit: str = "pcs") -> bool:
    """
    True for a line the spreadsheet computed rather than counted.

    Two signs. The label says so — 'Percentage', 'Total Pcs'. Or the figures are
    fractions where counts belong: a percentage line reads 0.34 / 0.66 / 1, and
    those would import as a sample box of nothing.

    The report computes its own totals and percentages from the counts, so a
    derived line is never wanted. Keeping one would also double the cargo, since
    its figures are the rows above it added up again.
    """
    clean = " ".join(str(label).lower().replace(".", " ").split())
    if clean and any(w in clean for w in _DERIVED_LABELS):
        return True

    numeric: List[float] = []
    for value in raw.values():
        text = str(value).strip().replace(",", "")
        if not text:
            continue
        try:
            numeric.append(float(text))
        except ValueError:
            return False  # free text in the line: judge it by its label alone

    # Every figure below 1 and at least a couple of them: a proportion line.
    # Not for kg sheets — a box of grapes genuinely weighs 0.820 kg, and this
    # test would throw every one of those rows away.
    if unit == "kg":
        return False
    if len(numeric) >= 3 and all(0 <= n <= 1 for n in numeric) and any(0 < n < 1 for n in numeric):
        return True
    return False


def build_mapping(
    headers: List[str],
    categories: List[Dict[str, str]],
) -> Tuple[Dict[str, str], Optional[str], Optional[str], List[str]]:
    """
    Work out what each spreadsheet column is.

    Returns (column -> category key, row-label column, written-total column,
    columns that could not be matched). The unmatched list is the important
    one: those columns are shown to the surveyor to map or drop, rather than
    being quietly ignored.
    """
    mapping: Dict[str, str] = {}
    label_col: Optional[str] = None
    total_col: Optional[str] = None
    unmatched: List[str] = []

    for header in headers:
        # Keyed by the header exactly as the sheet spells it, trailing spaces and
        # all, because that is the key in every parsed row. Matching on a
        # tidied-up copy and then storing the tidy version meant 'Count ' was
        # looked up as 'Count', found nothing, and every row lost its label.
        original = str(header)
        clean = original.strip()
        if not clean:
            continue

        if total_col is None and is_total_header(clean):
            total_col = original
            continue

        lowered = clean.lower()
        if label_col is None and (
            is_label_header(clean)
            or any(h in lowered for h in _ROW_LABEL_HINTS)
            or lowered in _ROW_LABEL_EXACT
        ):
            label_col = original
            continue

        key = match_header_to_category(clean, categories)
        if key:
            mapping[original] = key
        else:
            unmatched.append(original)

    return mapping, label_col, total_col, unmatched


def read_spreadsheet_as_grid(
    file_bytes: bytes,
    filename: str,
    commodity: Optional[str] = None,
    sheet_name: Optional[str] = None,
    column_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parse a tally spreadsheet into the workbench's grid shape.

    column_map, when supplied, is the surveyor's own mapping from the previous
    round of this call and overrides the automatic one. 'DROP' excludes a column.
    """
    parsed = parse_spreadsheet(file_bytes=file_bytes, filename=filename, sheet_name=sheet_name)
    headers: List[str] = [str(h) for h in parsed["headers"]]
    raw_rows: List[Dict[str, Any]] = parsed["rows"]

    categories = build_categories(commodity)
    unit = unit_for(commodity)
    auto_map, label_col, total_col, unmatched = build_mapping(headers, categories)

    if column_map:
        # The surveyor's decisions win, including a decision to drop a column.
        for header, key in column_map.items():
            if key == "DROP":
                auto_map.pop(header, None)
                if header not in unmatched:
                    unmatched.append(header)
            else:
                auto_map[header] = key
                if header in unmatched:
                    unmatched.remove(header)

    # A mapped column the fruit config does not know about still belongs in the
    # grid — it is the surveyor's own column and his counts go with it.
    for key in set(auto_map.values()):
        if not any(c["key"] == key for c in categories):
            label = next((h for h, k in auto_map.items() if k == key), key)
            categories.append({"key": key, "label": str(label).strip().title(), "role": "extra"})

    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(raw_rows):
        values: Dict[str, Any] = {}
        details: Dict[str, Any] = {}

        for header, key in auto_map.items():
            val = _to_figure(raw.get(header), unit)
            if val is None:
                expected = "a weight in kg" if unit == "kg" else "a whole number"
                details[key] = {
                    "normalized_value": None,
                    "review_status": "NEEDS_REVIEW",
                    "source": "spreadsheet",
                    "raw_text": str(raw.get(header, "")),
                    "validation": {
                        "status": "FAILED",
                        "message": f"'{raw.get(header, '')}' in column {header!r} is not {expected}.",
                    },
                }
                continue
            values[key] = val
            details[key] = {
                "normalized_value": val,
                "review_status": "NEEDS_REVIEW",
                "source": "spreadsheet",
                "raw_text": str(raw.get(header, "")),
            }

        if not values:
            continue  # a spacer or notes line, not a data row

        # Cold-store spreadsheets interleave derived lines with the data: a
        # percentage line under each count, and grand totals at the bottom.
        # Importing those as sample boxes would double the cargo and put
        # fractions in a count column. The app derives its own percentages and
        # totals from the counts, so these are dropped rather than shown.
        if _is_derived_row(group_label := str(raw.get(label_col, "")) if label_col else "", raw, unit):
            continue

        stated = _to_figure(raw.get(total_col), unit) if total_col else None
        computed, check = ValidationEngine.validate_row_total(values, stated)
        status = {"PASSED": "OK", "FAILED": "MISMATCH", "SKIPPED": "UNCHECKED"}[check.status]

        group = str(raw.get(label_col, "")).strip() if label_col else ""
        rows.append({
            "group": group or f"Row {idx + 1}",
            "boxes_opened": 1,
            "values": values,
            "stated_total": stated,
            "computed_total": computed,
            "check": {
                "status": status,
                "delta": (computed - stated) if stated is not None else None,
                "message": check.message,
            },
            "cell_details": details,
            "provenance": "spreadsheet",
        })

    return {
        "extraction_status": "OK" if rows else "NO_GRID",
        "engines_available": [],
        "ocr_engine": None,
        "quality": {"score": 1.0, "is_acceptable": True, "warnings": []},
        "headers": {},
        "table": {
            "commodity": commodity,
            "unit": unit_for(commodity),
            "grouping_label": label_col or "Count / Size",
            "categories": categories,
            "rows": rows,
            "column_totals": ValidationEngine.validate_column_totals(
                rows, [c["key"] for c in categories]
            ),
        },
        "image": {"preview": "", "width": 0, "height": 0},
        "filename": filename,
        "raw_text": "",
        "provenance": "spreadsheet",
        "source": "spreadsheet",
        "spreadsheet": {
            "sheet_names": parsed.get("sheet_names", []),
            "active_sheet": parsed.get("active_sheet"),
            "all_headers": headers,
            "column_map": auto_map,
            "label_column": label_col,
            "total_column": total_col,
            # Shown to the surveyor so he can map or dismiss them. These are the
            # columns his counts would silently vanish into otherwise.
            "unmapped_columns": unmatched,
            "row_count": len(raw_rows),
        },
        "reader": {"used": "spreadsheet"},
    }
