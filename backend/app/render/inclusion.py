"""
What the surveyor has ticked in or out of the report.

Every text section has a tick box on the form. Unticking leaves the section out
of the preview and the Word/PDF, without deleting what was written in it, so it
can be ticked back in at any time.

The fruit settings only choose the starting ticks on a new report — whether the
defect chart is drawn, whether the table carries its own "Condition found of…"
heading, whether the pressure and brix rows are measured. The surveyor can
change any of them; a rare report that needs a chart for apples gets one.

A flag that is missing means "in", so reports created before these flags
existed render exactly as they did. Used by both the HTML and DOCX engines so
the two stay identical.
"""

from __future__ import annotations

from typing import Any, Dict, List


def is_included(block: Dict[str, Any]) -> bool:
    return block.get("included", True) is not False


def included_rows(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in (block.get("rows") or []) if r.get("included", True) is not False]


def shows_table_title(block: Dict[str, Any]) -> bool:
    return block.get("show_title", True) is not False


def shows_chart(block: Dict[str, Any]) -> bool:
    return block.get("show_chart", True) is not False
