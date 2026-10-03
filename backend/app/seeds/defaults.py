"""
Authentic Report Defaults — driven by corpus mining from 432 real client reports.
Commodity presets are loaded from tools/perishable_fruits_output/template_archetypes.json
so new commodities from future mining runs are picked up automatically.

CRITICAL-RULES §8 compliant: placeholder shipper / consignee names, real arithmetic.
"""

from __future__ import annotations

import json
import pathlib
from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Load mined archetype data
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # backend/app/seeds -> repo root
_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "template_archetypes.json"
_FALLBACK_FILE = pathlib.Path(__file__).resolve().parent / "template_archetypes.json"


@lru_cache(maxsize=1)
def _load_archetypes() -> Dict[str, Any]:
    for path in (_ARCHETYPES_FILE, _FALLBACK_FILE):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Per-commodity labels.
#
# This used to carry a paragraph of narrative per section per fruit, written by
# a model and presented as report wording — with figures in it ("pulp
# temperature ... found in the range of 1.2°C to 2.0°C") that no surveyor had
# measured. The narrative sections now start empty and are written from the
# client's own clauses (app/seeds/clause_library.py) or typed.
# ---------------------------------------------------------------------------

_COMMODITY_SUPPLEMENT: Dict[str, Dict[str, Any]] = {
    # ── APPLE ──────────────────────────────────────────────────────────────
    "APPLE": {
        "label": "Fresh Apple",
        "declared": "Fresh Apple Fruits — [quantity and packing from the invoice]",
    },

    # ── GRAPE ──────────────────────────────────────────────────────────────
    "GRAPE": {
        "label": "Fresh Table Grapes",
        "declared": "Fresh Table Grapes — [quantity and packing from the invoice]",
    },

    # ── BLUEBERRY ──────────────────────────────────────────────────────────
    "BLUEBERRY": {
        "label": "Fresh Blueberry",
        "declared": "Fresh Blueberries — [quantity and packing from the invoice]",
    },

    # ── ORANGE ─────────────────────────────────────────────────────────────
    "ORANGE": {
        "label": "Fresh Orange",
        "declared": "Fresh Orange Fruits — [quantity and packing from the invoice]",
    },

    # ── PEAR ───────────────────────────────────────────────────────────────
    "PEAR": {
        "label": "Fresh Pear",
        "declared": "Fresh Pear Fruits — [quantity and packing from the invoice]",
    },

    # ── KIWI ───────────────────────────────────────────────────────────────
    "KIWI": {
        "label": "Fresh Kiwi",
        "declared": "Fresh Kiwi Fruits — [quantity and packing from the invoice]",
    },

    # ── MANDARIN ───────────────────────────────────────────────────────────
    "MANDARIN": {
        "label": "Fresh Mandarin",
        "declared": "Fresh Mandarin Fruits — [quantity and packing from the invoice]",
    },

    # ── DRAGON ─────────────────────────────────────────────────────────────
    "DRAGON": {
        "label": "Fresh Dragon Fruit",
        "declared": "Fresh Dragon Fruits — [quantity and packing from the invoice]",
    },

    # ── CHERRY ─────────────────────────────────────────────────────────────
    "CHERRY": {
        "label": "Fresh Cherry",
        "declared": "Fresh Cherries — [quantity and packing from the invoice]",
    },

    # ── AVOCADO ────────────────────────────────────────────────────────────
    "AVOCADO": {
        "label": "Fresh Avocado",
        "declared": "Fresh Avocado — [quantity and packing from the invoice]",
    },

    # ── PLUM ───────────────────────────────────────────────────────────────
    "PLUM": {
        "label": "Fresh Plum",
        "declared": "Fresh Plum Fruits — [quantity and packing from the invoice]",
    },

    # ── APRICOT ────────────────────────────────────────────────────────────
    "APRICOT": {
        "label": "Fresh Apricot",
        "declared": "Fresh Apricot, Peach & Nectarine — [quantity and packing from the invoice]",
    },
}


# ---------------------------------------------------------------------------
# Helper: build blocks for a commodity from supplement data + archetype
# ---------------------------------------------------------------------------

def _table_block(commodity_key: str, archetype: Dict[str, Any], block_id: str) -> Dict[str, Any]:
    """
    The empty condition-found table for one fruit: its own columns, unit,
    heading and starting ticks. A cargo of two fruits gets one of these each.

    Columns come from the same place the Verification Workbench gets them, so
    the grid on the form and the grid the tally sheet is read into are the
    same shape. The heading is the fruit's "condition found" heading, not a
    graph heading.
    """
    from app.ingest.tally.categories import build_categories, lookup_fruit, unit_for

    fruit = lookup_fruit(commodity_key) or {}
    _seq = archetype.get("heading_sequence", [])
    heading = next(
        (h for h in _seq if "condition" in h.lower() and "graph" not in h.lower()),
        None,
    ) or f"CONDITION FOUND OF {commodity_key} FRUITS:"
    return {
        "id": block_id,
        "type": "table",
        "commodity": commodity_key,
        "title": heading,
        "grouping_label": "Sample / Count",
        "unit": unit_for(commodity_key) or archetype.get("unit", "pcs"),
        "categories": [{"key": c["key"], "label": c["label"]} for c in build_categories(commodity_key)],
        "rows": [],
        "show_title": bool(fruit.get("show_condition_found", True)),
        "show_chart": bool(fruit.get("show_chart", False)),
    }


def fruit_table_block(commodity: str, block_id: str) -> Dict[str, Any]:
    """A condition-found table for another fruit in the same cargo."""
    key = fruit_key(commodity)
    return _table_block(key, _load_archetypes().get(key, {}), block_id)


def _build_blocks_for_commodity(
    commodity_key: str,
    supp: Dict[str, Any],
    archetype: Dict[str, Any],
    today_str: str,
    is_qc: bool,
) -> List[Dict[str, Any]]:
    """Build the complete list of blocks for a given commodity."""
    label = supp.get("label", commodity_key.capitalize())

    blocks: List[Dict[str, Any]] = []

    # ── Block 1: PARTICULARS ───────────────────────────────────────────────
    packing_defaults = {
        "apple": "Fresh Apples packed in slotted cardboard trays; such 4/5 trays packed inside the ventilated polyethylene sheet and further packed into a ventilated 3-ply corrugated cardboard box. Such boxes were reportedly stuffed inside a 40' Reefer container.",
        "pear": "Fresh Pear fruits packed in slotted EPS trays; such 4 trays packed inside the ventilated polyethylene sheet and further packed into a ventilated 3-ply corrugated cardboard box. Such boxes reportedly placed onto pallets and corners protected with cardboard sheet and fastened with nylon straps at equal intervals.",
        "mandarin": "Fresh Mandarin fruits packed in a open top ventilated corrugated cardboard box. Such cartons were reportedly placed on wooden pallets and secured with plastic straps. Such various pallets stuffed inside 40' Reefer container.",
        "orange": "Fresh Orange fruits packed in a open top ventilated corrugated cardboard box. Such cartons were reportedly placed on wooden pallets and secured with plastic straps. Such various pallets stuffed inside 40' Reefer container.",
        "citrus": "Fresh Citrus fruits packed in ventilated corrugated cardboard box, placed on pallets and secured with straps inside 40' Reefer container.",
        "grapes": "Bunch of fresh grapes packed in non-woven bag (Uvasys-used to prevent post-harvest fungal decay during transportation and storage), such bag packed inside ventilated plastic box. Such boxes were reportedly placed inside 40' Reefer container.",
        "plum": "Fresh Plum packed in plastic crate / boxes, stuffed inside 40' High Cube Reefer Containers.",
        "kiwi": "Fresh Kiwi fruits packed in corrugated boxes placed on pallets and secured with straps inside 40' Reefer container.",
    }
    packing_desc = packing_defaults.get(commodity_key.lower(), f"Fresh {label} fruits packed in standard export packaging, stuffed inside 40' Reefer container.")

    blocks.append({
        "id": "b_particulars",
        "type": "particulars",
        "section": "",
        "title": "PARTICULARS",
        "rows": [
            {"label": "Policy No.", "value": ["Information not furnished"]},
            {"label": "Insurer", "value": ["Information not furnished"]},
            {"label": "Sum Insured", "value": ["Information not furnished"]},
            {"label": "Shipper", "value": ["[Shipper Name, Address, Country]"]},
            {"label": "Consignees", "value": ["[Consignee Name, Address, City, India]"]},
            {"label": "Comm. Invoice No.", "value": ["Information not furnished"]},
            {"label": "Invoice Value", "value": ["Information not furnished"]},
            {"label": "Bill of Lading No.", "value": ["[B/L No. dated Date]"]},
            {"label": "Vessel Name", "value": ["[Vessel Name] Voyage No. [Voyage]"]},
            {"label": "Voyage as per B/L", "value": ["[Port of Loading] to [Port of Discharge]"]},
            {"label": "Date of arrival", "value": ["[Date of arrival at Terminal]"]},
            {"label": "Container Nos.", "value": ["[Container No.] (1x40' Reefer / 40RH)"]},
            {
                "label": "Consignment",
                "type": "table",
                "headers": [f"Fresh {label} Variety", "Count / Size", "Total Boxes"],
                "rows": [
                    {"col1": f"Fresh {label}", "col2": "[Count / Size]", "col3": "[Boxes]"}
                ],
                "footer": "Total: [Total Boxes] Gross Weight: [Weight] kg"
            },
            {"label": "Nature of Packing", "value": [packing_desc]},
        ],
    })

    # ── Narrative sections: standard application text for all fruits ──
    standard_application_text = (
        "Pursuant to the Consignee's request and subsequent appointment, we attended the Consignee's "
        "nominated cold storage facility, M/s [Cold Storage Name] ([Cold Storage Address]), "
        "on [Survey Date], to carry out an inspection of the subject consignment."
    )

    from app.seeds.staff_lookup import get_default_attendance

    # ── Block 2: PARAGRAPH 1 — APPLICATION ────────────────────────────────
    blocks.append({
        "id": "b_para1",
        "type": "narrative",
        "section": "PARAGRAPH 1: APPLICATION",
        "additional_text": standard_application_text,
        "attendance_intro": "The following persons attended the survey:",
        "attendance": get_default_attendance(),
    })

    # ── Block 3: PARAGRAPH 2 — CIRCUMSTANCES OF LOSS ──────────────────────
    blocks.append({
        "id": "b_para2",
        "type": "narrative",
        "section": "PARAGRAPH 2: CIRCUMSTANCES OF LOSS",
        "additional_text": "",
    })

    # ── Note block (Container & site condition) ───────────────────────────
    blocks.append({
        "id": "b_note",
        "type": "narrative",
        "section": "NOTE:",
        "additional_text": "",
    })

    # ── Block 4: PARAGRAPH 2.1 — OUR SURVEY ──────────────────────────────
    blocks.append({
        "id": "b_para2_1",
        "type": "narrative",
        "section": "PARAGRAPH 2.1: OUR SURVEY",
        "additional_text": "",
    })

    # ── Block 5: On-site Measurements ─────────────────────────────────────
    #
    # The client's 470 reports measure exactly three things: pulp temperature
    # (445 reports), brix (345) and pressure by penetrometer (208). Rows like
    # "Starch Iodine Index" and "Berry Firmness" that used to be seeded here
    # appear in none of them, so they are gone. Brix and pressure start ticked
    # or unticked by fruit, and the surveyor can change either.
    from app.ingest.tally.categories import lookup_fruit

    fruit = lookup_fruit(commodity_key) or {}
    blocks.append({
        "id": "b_measurements",
        "type": "measurements",
        "title": "On-Site Physical & Instrumental Measurements",
        "rows": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer",
             "min": "", "max": "", "unit": "°C", "included": True},
            {"subject": "Brix", "method": "",
             "min": "", "max": "", "unit": "%", "included": bool(fruit.get("show_brix", True))},
            {"subject": "Fruit Pressure", "method": "Penetrometer",
             "min": "", "max": "", "unit": "LBS", "included": bool(fruit.get("show_penetrometer", False))},
        ],
    })

    # ── Block 6: Defect condition table ───────────────────────────────────
    #
    # Starts empty. It used to be seeded with three rows of made-up counts
    # (Count 100: 142 sound, 12 russet, 26 bruised…) which appeared in every new
    # report before the surveyor had uploaded anything. They totalled and
    # percentaged like real figures, so a report could be finished and signed
    # with numbers that came from this file. The counts belong to the tally
    # sheet, and nowhere else.
    # show_title / show_chart only set the starting ticks. Grapes reports put
    # the table straight under Our Survey without a "Condition found of…"
    # heading, and most apple reports have no chart — but either can be ticked.
    blocks.append(_table_block(commodity_key, archetype, "b_table"))

    # ── Block 7: Survey Photographs ───────────────────────────────────────
    blocks.append({
        "id": "b_photos",
        "type": "photo_plate",
        "title": "SURVEY PHOTOGRAPHS:",
        "series_id": "survey",
        "label": "Survey",
        "provenance": "own_survey",
        "columns": 2,
        # Starts empty. Five placeholder groups used to be seeded here, and a
        # group with no photos in it fails the render assertion, so preview and
        # download broke on every report until the surveyor had filled all five.
        # The groups he actually needs come from the photos he uploads.
        "groups": [],
    })

    # ── Block 8: PARAGRAPH 3 — CAUSE OF LOSS ──────────────────────────────
    blocks.append({
        "id": "b_cause",
        "type": "narrative",
        "section": "PARAGRAPH 3: CAUSE OF LOSS",
        "additional_text": "",
    })

    # ── Block 9: PARAGRAPH 4 — NEXT STEP ──────────────────────────────────
    blocks.append({
        "id": "b_next_step",
        "type": "narrative",
        "section": "PARAGRAPH 4: NEXT STEP",
        "additional_text": "",
    })

    # ── Block 10: PARAGRAPH 5 — DOCUMENTATION ──────────────────────────────
    blocks.append({
        "id": "b_doc",
        "type": "narrative",
        "section": "PARAGRAPH 5: DOCUMENTATION",
        "additional_text": "",
    })

    # ── Block 11: Formal closure ──────────────────────────────────────────
    disclaimer = next(
        (c for c in archetype.get("top_narrative_clauses", []) if "without prejudice" in c.lower() or "reserve the right" in c.lower()),
        "We reserve the right to modify or add to this report if additional information comes to light.",
    )
    blocks.append({
        "id": "b_closure",
        "type": "fixed_text",
        "title": "CLOSURE",
        "content": (
            f"{disclaimer}\n\n"
            "Consignees are requested to pursue any claims-related matter directly with the responsible parties.\n\n"
            "These photos are in JPG format.\n\n"
            "\u201cISSUED WITHOUT PREJUDICE\u201d\n"
            f"Dated: {today_str}\n"
            "Marine Cargo Agencies Pvt. Ltd.\n"
            "\u00d8\u00d8\u00d8"
        ),
    })

    return blocks



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

from app.seeds.general_cargo import CARGO_TYPE_KEYS as _GC_KEYS  # noqa: E402


class UnknownCommodity(ValueError):
    """The report was asked for with a fruit this module has no layout for."""


def fruit_key(commodity: Optional[str]) -> str:
    """
    The key a fruit is filed under here, whichever way it was spelt.

    The New Report screen lists fruits from FRUIT_CONFIG, which files some of
    them plural (GRAPES, MANDARINS); this module files them singular. The
    mismatch used to fall through to a silent default, so every grapes report
    made from the screen was created as a Mandarin report — mandarin columns,
    counted in pieces — and a grapes tally, weighed in kg, could not go into it.
    An unknown or missing fruit is now refused rather than guessed.
    """
    raw = " ".join((commodity or "").strip().upper().replace("-", " ").split()).replace(" ", "_")
    if not raw:
        raise UnknownCommodity("No commodity was chosen for this report.")
    candidates = [raw]
    if raw.endswith("IES"):
        candidates.append(raw[:-3] + "Y")   # CHERRIES -> CHERRY
    if raw.endswith("S"):
        candidates.append(raw[:-1])          # GRAPES -> GRAPE
    candidates.append(raw + "S")
    for c in candidates:
        if c in _COMMODITY_SUPPLEMENT:
            return c
    raise UnknownCommodity(
        f"'{commodity}' is not a fruit this app has a report layout for. "
        f"Known: {', '.join(sorted(_COMMODITY_SUPPLEMENT))}."
    )


def get_default_block_state(
    template_id: str,
    commodity_key: Optional[str] = None,
    state: Optional[str] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Returns a rich, authentic initial block_state for a new report.
    Supports:
    1. All 12 mined perishable commodities (prefilled with authentic wording, defect columns, sample rows).
    2. General Cargo templates & subcategories (Steel, Machinery, Automotive, Chemicals, Paper, General Merchandise).
    3. State differentiation: PRELIMINARY (PLA with claim reserve) vs FINAL (full adjustment).
    4. Customizable block section selection.
    """
    commodity_upper = (commodity_key or "").upper()
    is_general = "general" in template_id.lower() or commodity_upper in _GC_KEYS
    is_qc = "qc" in template_id.lower()
    is_air = "air" in template_id.lower()
    is_preliminary = (state or "").upper() == "PRELIMINARY" or "preliminary" in template_id.lower()
    mode = "AIR" if is_air else "SEA"
    today_str = date.today().strftime("%d %B %Y")

    if is_general:
        # The client's general cargo layout; he issues Final reports only.
        from app.seeds import general_cargo

        gc = general_cargo.block_state(mode, cargo_type=commodity_upper or None, state=state)
        gc["transport"] = {
            "mode": mode,
            "container_no": "",
            "vessel": "",
            "voyage": "",
            "origin": "",
            "destination": "",
            "document": {"kind": "BILL_OF_LADING" if mode == "SEA" else "AIR_WAYBILL", "number": ""},
        }
        return gc
    else:
        key = fruit_key(commodity_key)
        archetypes = _load_archetypes()
        archetype = archetypes.get(key, {})
        supp = _COMMODITY_SUPPLEMENT[key]

        label = supp.get("label", key.capitalize())
        blocks = _build_blocks_for_commodity(key, supp, archetype, today_str, is_qc)

        if is_qc:
            report_title = f"IN-HOUSE QC INSPECTION REPORT ({label.upper()})"
        elif is_preliminary:
            report_title = f"PRELIMINARY MARINE CARGO SURVEY REPORT (PLA) — {label.upper()}"
        else:
            report_title = f"FINAL MARINE CARGO SURVEY REPORT — {label.upper()}"

        metadata = {
            "docx_template": "mca-qc-canonical-v1.docx" if is_qc else "mca-synthetic-v1.docx",
            "family": "QC_REPORT" if is_qc else "SURVEY_REPORT",
            "commodity": key,
            "state": "PRELIMINARY" if is_preliminary else "FINAL",
        }

    return {
        "report_title": report_title,
        "metadata": metadata,
        "transport": {
            "mode": mode,
            "container_no": "[CONTAINER NO.]",
            "vessel": "[VESSEL NAME]" if mode == "SEA" else "[FLIGHT NO.]",
            "voyage": "[VOYAGE NO.]" if mode == "SEA" else "[AWB NO.]",
            "origin": "[Port of Loading / Origin]",
            "destination": "[Port of Discharge]",
            "document": {
                "kind": "BILL_OF_LADING" if mode == "SEA" else "AIR_WAYBILL",
                "number": "[B/L or AWB Number]",
            },
        },
        "weights": {
            "manifest_kg": "[GROSS WEIGHT FROM B/L]",
            "gross_kg": "",
            "tare_kg": "",
            "net_kg": "",
        },
        "blocks": blocks,
    }
