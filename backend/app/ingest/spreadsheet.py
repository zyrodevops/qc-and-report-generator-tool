"""
Spreadsheet Ingest — Master Spec §10.4.

Primary path for table, reconciliation, and inventory blocks.
CSV/xlsx upload → column mapping → table block rows.

CRITICAL RULES:
- Formula cells are read as VALUES, never re-evaluated.
- Column mapping is saved per template (not re-asked each time).
- The surveyor confirms any column merges/drops — never inferred.
- No float in the output; all numeric values stored as strings for Decimal conversion.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import openpyxl
from openpyxl import load_workbook


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_spreadsheet(
    file_bytes: bytes,
    filename: str,
    sheet_name: Optional[str] = None,
    column_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parse a .csv or .xlsx file into rows consumable by a table block.

    Args:
        file_bytes: Raw file content.
        filename:   Original filename (used to detect format).
        sheet_name: For xlsx, which sheet to read (None = active sheet).
        column_map: {sheet_column_header: category_key} mapping.
                    If None, returns raw headers for the column-mapping UI.

    Returns:
        {
          "headers":      [str, ...],      # sheet column names
          "rows":         [dict, ...],     # raw rows {header: value_str}
          "mapped_rows":  [dict, ...] | None,  # if column_map provided: {category_key: value_str}
          "sheet_names":  [str, ...],      # xlsx only
          "active_sheet": str,
        }

    Notes:
        - Formula cells (=SUM(...)) are read as their cached VALUE.
          openpyxl data_only=True is the mechanism.
        - All numeric values are returned as strings to preserve precision.
          The caller converts to Decimal at compute time.
    """
    fname_lower = filename.lower()

    if fname_lower.endswith(".csv"):
        return _parse_csv(file_bytes, column_map)
    elif fname_lower.endswith((".xlsx", ".xlsm", ".xls")):
        return _parse_xlsx(file_bytes, sheet_name, column_map)
    else:
        raise ValueError(f"Unsupported file format: {filename!r}. Use .csv or .xlsx")


def _parse_csv(
    file_bytes: bytes,
    column_map: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    """Parse CSV. Returns rows with string values (no Decimal conversion here)."""
    buf = io.StringIO(file_bytes.decode("utf-8-sig"))  # utf-8-sig strips BOM
    df = pd.read_csv(buf, dtype=str, keep_default_na=False)
    headers = list(df.columns)
    raw_rows = df.to_dict(orient="records")

    mapped_rows = _apply_column_map(raw_rows, column_map) if column_map else None

    return {
        "headers": headers,
        "rows": raw_rows,
        "mapped_rows": mapped_rows,
        "sheet_names": [],
        "active_sheet": "csv",
    }


def _parse_xlsx(
    file_bytes: bytes,
    sheet_name: Optional[str],
    column_map: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Parse xlsx.
    data_only=True ensures formula cells yield their cached value, not the formula string.
    CRITICAL: This is how `=SUM(B2:D2)` becomes the number 6.23, not the string "=SUM(B2:D2)".
    """
    buf = io.BytesIO(file_bytes)
    # data_only=True reads cached formula results — this is the CRITICAL setting
    wb = load_workbook(buf, data_only=True, read_only=True)

    sheet_names = wb.sheetnames
    active_name = sheet_name if (sheet_name and sheet_name in sheet_names) else wb.active.title
    ws = wb[active_name]

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return {
            "headers": [],
            "rows": [],
            "mapped_rows": [],
            "sheet_names": sheet_names,
            "active_sheet": active_name,
        }

    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(header_row)]

    raw_rows: List[Dict[str, str]] = []
    for row in rows_iter:
        row_dict: Dict[str, str] = {}
        for header, cell_value in zip(headers, row):
            # Convert every value to string; preserves numeric precision for Decimal parsing
            if cell_value is None:
                row_dict[header] = ""
            else:
                row_dict[header] = str(cell_value)
        # Skip completely empty rows
        if any(v.strip() for v in row_dict.values()):
            raw_rows.append(row_dict)

    mapped_rows = _apply_column_map(raw_rows, column_map) if column_map else None

    wb.close()
    return {
        "headers": headers,
        "rows": raw_rows,
        "mapped_rows": mapped_rows,
        "sheet_names": sheet_names,
        "active_sheet": active_name,
    }


def _apply_column_map(
    raw_rows: List[Dict[str, str]],
    column_map: Dict[str, str],
) -> List[Dict[str, str]]:
    """
    Apply a column mapping {sheet_header -> category_key}.
    Columns absent from the map are silently dropped (surveyor's decision, not automatic).
    """
    mapped: List[Dict[str, str]] = []
    for row in raw_rows:
        m: Dict[str, str] = {}
        for sheet_col, cat_key in column_map.items():
            if cat_key == "DROPPED":
                continue
            val = row.get(sheet_col, "")
            m[cat_key] = val
        if any(v.strip() for v in m.values()):
            mapped.append(m)
    return mapped


# ---------------------------------------------------------------------------
# Column mapping helpers
# ---------------------------------------------------------------------------

def build_column_mapping_preview(
    headers: List[str],
    saved_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns a list of {header, suggested_key, status} for the column-mapping UI.
    saved_map: Previously saved mapping for this template (pre-fills the UI).
    """
    result = []
    for h in headers:
        entry: Dict[str, Any] = {"header": h, "suggested_key": None, "status": "unmapped"}
        if saved_map and h in saved_map:
            entry["suggested_key"] = saved_map[h]
            entry["status"] = "dropped" if saved_map[h] == "DROPPED" else "mapped"
        result.append(entry)
    return result

