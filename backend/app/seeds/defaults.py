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
    note_text = ""
    ck = commodity_key.lower()
    if ck in ("apple", "pear"):
        fruit_name = "Pear" if ck == "pear" else "Apple"
        para2_text = (
            f"We were apprised that subsequent to its discharge from the vessel [Vessel Name & Voyage No.] "
            f"at [Port of Discharge], on [Discharge Date], the 40' Reefer container No. [Container No.], "
            f"conveying the subject cargo, was transferred to the designated Container Freight Station (CFS) "
            f"for the purpose of customs formalities and ultimate delivery.\n\n"
            f"Following the culmination of customs procedures, the aforementioned container was loaded onto a "
            f"trailer truck, dispatched, and transported via road. It was reported to have been delivered to the "
            f"consignees' cold storage facility on [Delivery Date], ostensibly in an externally sound condition. "
            f"We were further given to comprehend that during the destuffing and subsequent inspection, the "
            f"consignees' Quality Control Team identified that the {fruit_name} fruits had sustained damage. "
            f"Consequently, we were contacted and formally requested to undertake the survey."
        )
    elif ck in ("mandarin", "mandarins"):
        para2_text = (
            "It was reported to us that after landing from the vessel [Vessel Name & Voyage No.] "
            "at [Port of Discharge] on [Discharge Date], the subject 1x40’ Reefer Container No. [Container No.] "
            "carrying the subject cargo was gated out and shifted to the nominated Container Freight Station (CFS) "
            "for customs formalities and delivery. On completion of custom formalities, the subject container was "
            "loaded onto the trailer truck, dispatched, road transported and was said to have been delivered at "
            "the consignees’ cold storage in an apparently sound condition.\n\n"
            "We were further given to understand that during destuffing and checking, the consignees’ QC team "
            "found mandarin fruits in a damaged condition. Hence, we were contacted and requested to conduct the survey."
        )
        note_text = (
            "Upon our arrival, we noted that the container was no longer available on site. "
            "The consignees advised us that the container was released to avoid detention charges."
        )
    elif ck in ("grape", "grapes"):
        para2_text = (
            "It was reported to us that after discharge from the carrying vessel [Vessel Name & Voyage No.] "
            "at [Port of Discharge] on [Discharge Date], the subject 1x40’ Reefer Container No. [Container No.] "
            "carrying the subject cargo was drayed by truck and received at the inland depot / CFS for customs "
            "formalities and delivery. On completion of customs formalities, the subject container was dispatched, "
            "road transported, and was said to have been delivered at the consignees’ cold storage in an apparently "
            "sound condition on [Delivery Date].\n\n"
            "We were further given to understand that during destuffing and checking, the consignees’ QC team "
            "found fresh grape fruits in a damaged condition. Hence, we were contacted and requested to conduct the survey."
        )
    elif ck in ("plum", "plums"):
        para2_text = (
            "It was reported that following discharge from the vessel [Vessel Name & Voyage No.] "
            "at [Port of Discharge], on [Discharge Date], the 1x40’ High Cube refrigerated container "
            "(No. [Container No.]) carrying the subject cargo was shifted to the nominated Container Freight Station "
            "(CFS) for customs clearance and subsequent delivery. Upon completion of customs formalities, the "
            "container was loaded onto a road trailer, dispatched, and delivered at the Consignee’s nominated cold "
            "storage facility on [Delivery Date] in an externally sound condition.\n\n"
            "We were further informed that during opening the container and initial inspection of the cargo from the "
            "door end, the Consignee’s Quality Control (QC) In-Charge found the fresh plums in a severely deteriorated "
            "condition, exhibiting extensive rotting and fungal decay. Consequently, our attendance was requested to "
            "conduct a survey to ascertain the nature, extent, and cause of the reported damage."
        )
    else:
        para2_text = ""

    blocks.append({
        "id": "b_para2",
        "type": "narrative",
        "section": "PARAGRAPH 2: CIRCUMSTANCES OF LOSS",
        "additional_text": para2_text,
    })

    # ── Note block (Container & site condition) ───────────────────────────
    blocks.append({
        "id": "b_note",
        "type": "narrative",
        "section": "NOTE:",
        "additional_text": note_text,
    })

    # ── Block 4: PARAGRAPH 2.1 — OUR SURVEY ──────────────────────────────
    if ck == "apple":
        para2_1_text = (
            "The consignee's end buyer representative, [Representative Name], presented [Total Boxes] boxes "
            "across [N] counts on various pallets for our survey. These were stored in cold storage room "
            "number [Room No.], where the ambient temperature was recorded as [Room Temp °C].\n\n"
            "THE CONDITION FOUND OF APPLE FRUITS:\n\n"
            "The pulp temperature of the Apple fruits was measured inside the cold room using a digital "
            "thermometer and registered in the range of [Pulp Temp Min °C] to [Pulp Temp Max °C].\n\n"
            "From different locations within the cold room, [Sample Boxes] boxes across [N] counts were randomly "
            "selected and opened for detailed examination. Upon unpacking and inspection, the Apple fruits inside "
            "the cartons exhibited a mixture of conditions, including sound, and various degrees of rotten.\n\n"
            "The pressure of the randomly selected various Apple fruits across [N] counts were measured using a "
            "penetrometer, and the following average values were recorded for the sound apples:\n"
            "• Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].\n\n"
            "The Apple fruits were cut, and the following pulp conditions were observed:\n"
            "• Sound apples: The pulp was consistently hard and white.\n"
            "• Bruised apples: While the overall pulp remained firm, the bruised areas were noted to be soft and brown in colour.\n"
            "• The sugar brix for the aforementioned counts was measured and found to be in the range of [Brix Min %] to [Brix Max %].\n\n"
            "During our inspection, [Sample Boxes] boxes out of the [Total Boxes] boxes (under [N] counts) were separated into the following categories. "
            "The details for each category are provided below:"
        )
    elif ck == "pear":
        para2_1_text = (
            "The consignee's representative, [Representative Name], presented [Total Boxes] boxes across available "
            "[N] counts for our survey. These were stored in cold storage room number [Room No.], where the "
            "ambient temperature was recorded as [Room Temp °C].\n\n"
            "THE CONDITION FOUND OF PEAR FRUITS:\n\n"
            "The pulp temperature of the Pear fruits was measured inside the cold room using a digital "
            "thermometer and registered in the range of [Pulp Temp Min °C] to [Pulp Temp Max °C].\n\n"
            "From different locations within the cold room, [Sample Boxes] boxes across [N] counts were randomly "
            "selected and opened for detailed examination. Upon unpacking and inspection, the Pear fruits inside "
            "the cartons exhibited a mixture of conditions, including sound and in a rotten condition in various degrees.\n\n"
            "The pressure of the Pear fruits under [N] counts was measured using a penetrometer, and the following "
            "average values were recorded for the sound Pears:\n"
            "• Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].\n\n"
            "The Pear fruits were cut, and the following pulp conditions were observed:\n"
            "• Sound Pears: The pulp was consistently hard.\n"
            "• The sugar brix for the above counts was measured and found to be in the range of [Brix Min %] to [Brix Max %].\n\n"
            "During our inspection, [Sample Boxes] boxes out of the [Total Boxes] boxes (under [N] counts) were separated "
            "into the following categories. The details for each category are provided below:"
        )
    elif ck in ("mandarin", "mandarins"):
        para2_1_text = (
            "The consignees’ representative [Representative Name], produced before us the [Total Cartons] cartons "
            "under [N] sizes for our survey, stored inside the cold storage no. [Room No.]. Cold room display "
            "temperature was found maintained at [Room Temp °C].\n\n"
            "The pulp temperature of the fresh mandarin fruits was checked by means of a digital thermometer inside "
            "the cold room and was found in the range of [Pulp Temp Min °C] to [Pulp Temp Max °C].\n\n"
            "Thereafter, a total of [Sample Boxes] cartons was randomly selected from various pallets / different "
            "locations inside the cold room and were opened for our detailed survey, when we found the mandarin fruits "
            "inside the cartons with mixture of sound, soft/pressed, mechanical injury, rotten spot, and in a rotten "
            "condition in various degrees.\n\n"
            "• Upon cutting the mandarin fruits, the pulp was found juicy.\n"
            "• Brix was checked and was found in the range of [Brix Min %] to [Brix Max %].\n\n"
            "Based on our survey findings, upon segregation of mandarin fruits from the [Sample Boxes] cardboard boxes, "
            "we can conclude that the mandarin fruits were found with the following defects:"
        )
    elif ck in ("grape", "grapes"):
        para2_1_text = (
            "The consignee’s representative, [Representative Name], presented for inspection the [Total Boxes] boxes "
            "stored inside cold room No. [Room No.]. The cold room's temperature display indicated [Room Temp °C].\n\n"
            "The pulp temperature of the grapes was checked using a digital probe thermometer inside the cold room "
            "within the boxes, whereby the temperature was recorded in the range of [Pulp Temp Min °C] to [Pulp Temp Max °C].\n\n"
            "Thereafter, a total of [Sample Boxes] boxes from the cold room were randomly selected from various stacks "
            "at different locations of the cold room and were opened for our survey when we found the grapes inside the "
            "boxes with a mixture of sound, soft, and in a rotten condition in varying degrees.\n\n"
            "• Upon cutting the sound berries, the pulp was found hard and partially white.\n"
            "• Upon cutting the soft berries, the pulp was found soft and dark in colour.\n"
            "• The average sugar brix of the grapes was checked and found in the range of [Brix Min %] to [Brix Max %].\n"
            "• Grape’s berries size was checked using a vernier caliper and was found in the range of [Berry Size Min mm] to [Berry Size Max mm].\n\n"
            "During our inspection, [Sample Boxes] boxes out of the [Total Boxes] boxes were segregated into the following "
            "categories. The category wise details are given below:"
        )
    elif ck in ("plum", "plums"):
        para2_1_text = (
            "The Consignees’ representative [Representative Name] produced before us the subject 40’ Reefer Container "
            "No. [Container No.] for our survey. Upon checking the same, the details noted are as follows:\n\n"
            "• The refrigerated container [Container No.], laden with fresh plums, was inspected at the cold storage "
            "unloading ramp and was found structurally sound with standard wear and tear, fully plugged into the electrical "
            "main, and actively powered on.\n"
            "• Reefer operational parameters registered a set point of [Set Temp °C], supply air temperature of [Supply Temp °C], "
            "and return air temperature of [Return Temp °C].\n"
            "• Pulp temperatures drawn inside the container across different locations using a digital probe thermometer "
            "ranged from [Pulp Temp Min °C] to [Pulp Temp Max °C].\n"
            "• Under continuous surveyor supervision, 100% destuffing of the consignment comprising [Total Cartons] cartons "
            "was completed and transferred directly into the cold storage facility.\n"
            "• A representative sample of [Sample Boxes] cartons was drawn across the stow for detailed segregation and "
            "defect classification.\n\n"
            "Pulp condition after cutting & the Taste:\n"
            "• Cross-sectional cutting of representative fruit specimens revealed internal breakdown, water-soaking, and deep flesh browning.\n"
            "• Organoleptic evaluation indicated severe textural degradation; the pulp was mushy, lacked characteristic varietal firmness, and had acquired an offensive, fermented taste."
        )
    else:
        para2_1_text = ""

    blocks.append({
        "id": "b_para2_1",
        "type": "narrative",
        "section": "PARAGRAPH 2.1: OUR SURVEY",
        "additional_text": para2_1_text,
    })

    # ── Block 5: On-site Measurements ─────────────────────────────────────
    #
    # The client's 470 reports measure exactly three things: pulp temperature
    # (445 reports), brix (345) and pressure by penetrometer (208). Rows like
    # "Starch Iodine Index" and "Berry Firmness" that used to be seeded here
    # appear in none of them, so they are gone. Brix and pressure start ticked
    # or unticked by fruit, and the surveyor can change either.
    # For curated fruits (apple, pear, mandarin, grapes, plum), these measurements
    # are integrated directly into Paragraph 2.1 narrative prose per client practice,
    # so the standalone table starts unticked (included=False) for preview/DOCX.
    from app.ingest.tally.categories import lookup_fruit

    fruit = lookup_fruit(commodity_key) or {}
    measurements_included = ck not in ("apple", "pear", "mandarin", "mandarins", "grape", "grapes", "plum", "plums")
    blocks.append({
        "id": "b_measurements",
        "type": "measurements",
        "title": "On-Site Physical & Instrumental Measurements",
        "included": measurements_included,
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
