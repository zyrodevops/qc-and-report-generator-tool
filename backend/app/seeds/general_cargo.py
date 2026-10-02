"""
General cargo survey report: the client's layout. Final by default, Preliminary when picked.

Built from his own general cargo reports:

  cover particulars
  PARAGRAPH 1: APPLICATION            (+ the attendance table under it)
  PARAGRAPH 2: CIRCUMSTANCES OF LOSS
  PARAGRAPH 2.n: OUR SURVEY ON <date> [AT <place>] [FOR CONTAINER NO. <x>]
                                      (one per container or visit)
  PARAGRAPH 3: CAUSE OF LOSS
  PARAGRAPH 4: NEXT STEP
  PARAGRAPH 5: DOCUMENTATION
  photographs, closing

Paragraph numbers are worked out when the report is made (see
app/render/paragraphs.py), so a section left out does not leave a gap.

He only issues Final reports for general cargo, so there is no preliminary
variant. Everything starts empty or as a visible blank ([Consignees]); no
wording and no figures are put in on his behalf. The wording comes from the
clause cards, the figures from the documents and the surveyor.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

REPORT_KIND = "general_cargo"

# Cargo types, from what the general cargo reports carry (share of reports).
# Kept to a label: nothing in the report is drawn from it but the title.
CARGO_TYPES: List[Dict[str, str]] = [
    {"key": "GENERAL_CARGO", "display": "General cargo", "emoji": "🚢", "color": "blue",
     "description": "Any cargo; pick a type below only if it helps you find the report later"},
    {"key": "STEEL_METALS", "display": "Steel & metal", "emoji": "🔩", "color": "slate",
     "description": "Coils, plates, pipes, wire rods, sheets (19% of reports)"},
    {"key": "MACHINERY_PARTS", "display": "Machinery & equipment", "emoji": "⚙️", "color": "amber",
     "description": "Machines, project cargo, spare parts, transformers (15%)"},
    {"key": "PAPER_PACKAGING", "display": "Paper & pulp", "emoji": "📦", "color": "yellow",
     "description": "Paper reels, pulp bales, kraft, board (13%)"},
    {"key": "BAGGED_FOOD", "display": "Bagged / food commodities", "emoji": "🌾", "color": "green",
     "description": "Rice, sugar, pulses, cashew, fertiliser in bags (13%)"},
    {"key": "CHEMICALS_LIQUIDS", "display": "Chemicals, plastics & liquids", "emoji": "🧪", "color": "teal",
     "description": "Drums, IBCs, resins, granules, flexitank oil (12%)"},
    {"key": "AUTOMOTIVE", "display": "Vehicles & auto parts", "emoji": "🚗", "color": "indigo",
     "description": "Vehicles, CKD kits, tyres, components"},
    {"key": "ELECTRONICS", "display": "Electronics & appliances", "emoji": "🔌", "color": "purple",
     "description": "Electronics, appliances, solar panels"},
]
CARGO_TYPE_KEYS = {c["key"] for c in CARGO_TYPES}
CARGO_LABEL = {c["key"]: c["display"] for c in CARGO_TYPES}

# The cover fields the client's reports start from. Any can be removed and
# others added (OPTIONAL_COVER_FIELDS); his reports each carry a
# different set.
COVER_FIELDS_SEA = [
    "Insurers", "Policy No.", "Insured Value", "Shipper", "Consignees",
    "Invoice No. & Date", "Invoice Value", "Bill of Lading No. & Date", "Container Nos.",
    "Vessel / Voyage", "Port of Loading", "Port of Discharge", "Date of Arrival",
    "Consignment", "Nature of Packing", "Insured Loss Amt.",
]
COVER_FIELDS_AIR = [
    "Insurers", "Policy No.", "Insured Value", "Shipper", "Consignees",
    "Invoice No. & Date", "Invoice Value", "Air Waybill No. & Date", "Flight No. & Date",
    "Airport of Loading", "Airport of Discharge", "Date of Arrival",
    "Consignment", "Nature of Packing", "Insured Loss Amt.",
]
OPTIONAL_COVER_FIELDS = [
    "Certificate No.", "Assured", "Applicant", "Seller / Beneficiary", "Notify Party / Applicant",
    "Commercial Invoice No. & Date", "Damaged Item Inv. No.", "Damaged Item Inv. Value",
    "Total No. of Packages", "Shipping Bill No. & Date", "Bill of Entry No. & Date",
    "Voyage / Route", "Transshipment Vessel", "Discharged Date", "Cargo Departed from CFS",
    "Cargo Arrived at Factory", "Cargo Un-packing Date", "Nature of Packing (as declared)",
    "Nature of Packing (as found)", "Net / Gross Weight", "Place of Survey",
]


def _blank(label: str) -> str:
    return f"[{label.rstrip('.').strip()}]"


def cover_rows(mode: str) -> List[Dict[str, Any]]:
    labels = COVER_FIELDS_AIR if mode == "AIR" else COVER_FIELDS_SEA
    return [{"label": lab, "value": [_blank(lab)]} for lab in labels]


def survey_unit(n: int, container: str = "", survey_date: str = "", place: str = "") -> Dict[str, Any]:
    """One 'OUR SURVEY' paragraph: a visit, or a container's inspection."""
    return {
        "id": f"b_survey_{n}",
        "type": "survey_unit",
        "section": "OUR_SURVEY",
        "survey_date": survey_date,
        "place": place,
        "container": container,
        "additional_text": "",
        "attendance": [],
        "included": True,
    }


def narrative(block_id: str, title: str, section_key: str) -> Dict[str, Any]:
    return {
        "id": block_id,
        "type": "narrative",
        "section": title,
        "clause_section": section_key,
        "numbered": True,
        "additional_text": "",
    }


# The report tables (app/compute/gc_tables.py), and the section each follows.
# Off until the surveyor ticks them in: most reports do not have them.
REPORT_TABLES = [
    ("b_seals", "seals", "b_circumstances"),
    ("b_weather", "weather", "b_cause"),
    ("b_reserve", "reserve", "b_next_step"),
]


def report_table(block_id: str, kind: str) -> Dict[str, Any]:
    return {"id": block_id, "type": "gc_table", "kind": kind, "rows": [], "included": False}


def build_blocks(mode: str, today: Optional[date] = None) -> List[Dict[str, Any]]:
    today_str = (today or date.today()).strftime("%d %B %Y").lstrip("0")
    return [
        {"id": "b_particulars", "type": "particulars", "section": "", "rows": cover_rows(mode),
         "optional_labels": OPTIONAL_COVER_FIELDS},
        narrative("b_application", "APPLICATION", "APPLICATION"),
        # Under Application, as in his reports; the line above the table is the
        # one 214 of the Gladstone cases use.
        {"id": "b_attendance", "type": "attendance", "title": "",
         "intro": "The following persons attended the survey:", "rows": []},
        narrative("b_circumstances", "CIRCUMSTANCES OF LOSS", "CIRCUMSTANCES_OF_LOSS"),
        report_table("b_seals", "seals"),
        survey_unit(1),
        narrative("b_cause", "CAUSE OF LOSS", "CAUSE_OF_LOSS"),
        report_table("b_weather", "weather"),
        narrative("b_next_step", "NEXT STEP", "NEXT_STEP"),
        report_table("b_reserve", "reserve"),
        narrative("b_documentation", "DOCUMENTATION", "DOCUMENTATION"),
        {"id": "b_photos", "type": "photo_plate", "title": "SURVEY PHOTOGRAPHS:", "series_id": "survey",
         "label": "SURVEY PHOTOGRAPHS:", "provenance": "own_survey", "columns": 2, "groups": []},
        {
            "id": "b_closure",
            "type": "fixed_text",
            "title": "CLOSURE",
            # His closing, word for word, from all four general cargo reports.
            "content": (
                "Disclaimer: The information provided in this report is based on the surveyor's current "
                "knowledge and does not affect the legal rights of any involved parties. We reserve the right "
                "to modify or add to this report if additional information comes to light.\n\n"
                "“ISSUED WITHOUT PREJUDICE”\n"
                f"Dated: {today_str}\n"
                "Place: Mumbai, India.\n"
                "ØØØ"
            ),
        },
    ]


def block_state(mode: str, cargo_type: Optional[str] = None, today: Optional[date] = None,
                state: Optional[str] = None) -> Dict[str, Any]:
    key = (cargo_type or "GENERAL_CARGO").upper()
    if key not in CARGO_TYPE_KEYS:
        key = "GENERAL_CARGO"
    # Final by default; Preliminary when picked (same layout, its own title).
    stage = "PRELIMINARY" if (state or "").upper() == "PRELIMINARY" else "FINAL"
    return {
        "report_title": f"{stage} SURVEY REPORT",
        "metadata": {
            "report_kind": REPORT_KIND,
            "family": "SURVEY_REPORT",
            "commodity": "GENERAL_CARGO",
            "cargo_type": key,
            "cargo_label": CARGO_LABEL[key],
            "state": stage,
            "docx_template": "mca-synthetic-v1.docx",
        },
        "transport": {"mode": mode},
        "blocks": build_blocks(mode, today),
    }


# ---------------------------------------------------------------------------
# The damage table of a survey paragraph
#
# A survey paragraph's findings list (what, how many, condition, photos)
# prints as a table, as the client's reports do. Where it goes in the text is
# marked by a line reading "(damage table)"; without one it goes after the
# text (app/compute/gc_tables.py, unit_segments).
# ---------------------------------------------------------------------------

DAMAGE_TABLE_COLUMNS = ["Sr. No.", "Description", "Quantity", "Condition found", "Photo Nos."]


def _clean(v: Any) -> str:
    return " ".join(str(v if v is not None else "").split())


def findings_rows(block: Dict[str, Any]) -> List[List[str]]:
    """The damage table's rows: [Sr. No., description, quantity, condition, photos]."""
    if block.get("findings_table") is False:
        return []
    out = []
    for f in block.get("findings") or []:
        item, total, affected = _clean(f.get("item")), _clean(f.get("total")), _clean(f.get("affected"))
        condition, photos = _clean(f.get("condition")), _clean(f.get("photos"))
        if not (item or affected or condition):
            continue
        qty = f"{affected} of {total}" if affected and total else (affected or total)
        out.append([str(len(out) + 1), item, qty, condition, photos])
    return out


def is_general_cargo(state: Dict[str, Any]) -> bool:
    return (state.get("metadata") or {}).get("report_kind") == REPORT_KIND
