"""
Paragraph numbers of a general cargo report, worked out when it is made.

The client numbers his sections PARAGRAPH 1, 2, 3 … and each survey under
Circumstances as 2.1, 2.2 … (one per container can run past 2.20). The
numbers are not stored: a section left out, or a survey added, renumbers the
rest, so the report never has a gap or a repeat.

Fruit reports keep the numbers written into their section names.
"""

from __future__ import annotations

from typing import Any, Dict

from app.render.inclusion import is_included


def survey_title(block: Dict[str, Any]) -> str:
    """OUR SURVEY ON 22 JUNE 2026 AT THE CFS FOR CONTAINER NO. TSTU1234565:"""
    parts = ["OUR JOINT SURVEY" if block.get("joint") else "OUR SURVEY"]
    d = " ".join(str(block.get("survey_date") or "").split())
    if d:
        parts.append(f"ON {d}")
    place = " ".join(str(block.get("place") or "").split())
    if place:
        parts.append(f"AT {place}")
    cont = " ".join(str(block.get("container") or "").split())
    if cont:
        parts.append(f"FOR CONTAINER NO. {cont}")
    return " ".join(parts).upper() + ":"


def number_paragraphs(state: Dict[str, Any]) -> None:
    """Set `_heading` on the numbered sections and the surveys of a general cargo report."""
    if (state.get("metadata") or {}).get("report_kind") != "general_cargo":
        return
    top = 0
    sub = 0
    for b in state.get("blocks", []) or []:
        if not is_included(b):
            continue
        if b.get("type") == "narrative" and b.get("numbered"):
            top += 1
            sub = 0
            title = str(b.get("section") or "").strip().rstrip(":")
            b["_heading"] = f"PARAGRAPH {top}: {title}:"
        elif b.get("type") == "survey_unit":
            sub += 1
            b["_heading"] = f"PARAGRAPH {max(top, 1)}.{sub}: {survey_title(b)}"
