"""
Which defect columns a report table actually shows.

A fruit's column list is the full set it is ever graded on — eleven for apple.
Any one sheet uses fewer; the apple sheet WA0076 has nothing in Pressure, Soft
or Lenticels. Printing those empty columns pushed the defect table off the
right edge of an A4 page, and the client's own reports only list the defects
that were counted.

So a column appears in the report when at least one row has a value in it.
A zero is a value — a surveyor who types 0 has said "none found", and that
column is kept. Only a column left entirely blank is dropped.

Both the HTML and DOCX engines use this, so the two stay cell-for-cell alike.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _has_value(v: Any) -> bool:
    return v is not None and str(v).strip() != ""


def visible_columns(block: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    """
    (original index, category) for each column worth printing.

    The original index is kept because the computed per-row percentages are
    positional against the full category list.
    """
    categories = block.get("categories", []) or []
    rows = block.get("rows", []) or []
    if not rows:
        return list(enumerate(categories))

    shown = [
        (i, cat)
        for i, cat in enumerate(categories)
        if any(_has_value((r.get("values") or {}).get(cat.get("key"))) for r in rows)
    ]
    # A table whose every cell is empty still needs its headings.
    return shown or list(enumerate(categories))
