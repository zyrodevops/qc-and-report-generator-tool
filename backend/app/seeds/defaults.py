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
# Per-commodity supplementary data (measurements, narrative wording, sample rows)
# These are written from domain knowledge + real report patterns found in the corpus.
# ---------------------------------------------------------------------------

_COMMODITY_SUPPLEMENT: Dict[str, Dict[str, Any]] = {
    # ── APPLE ──────────────────────────────────────────────────────────────
    "APPLE": {
        "label": "Fresh Apple",
        "declared": "Fresh Apple Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains approx. 100–125 pcs packed in individual poly sleeves.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (11 mm tip)", "min": "", "max": "", "unit": "lbs/cm²"},
            {"subject": "Starch Iodine Index", "method": "CTIFL Scale (1–8)", "min": "", "max": "", "unit": "Score"},
        ],
        "para1_text": (
            "We the undersigned surveyors were appointed to conduct survey of the subject consignment. "
            "We attended at the consignee's nominated cold storage facility upon container destuffing and "
            "conducted a joint inspection in the presence of the consignee's representative and the CHA. "
            "The container exterior, seal condition, and reefer temperature display were verified prior to door opening."
        ),
        "para2_text": (
            "Upon opening the container doors, cargo stowage was found uniform on pallets. "
            "No evidence of transit condensation, water ingress, or crushing to carton exteriors was noted. "
            "Reefer set point was verified and pulp temperatures were spot-checked across top, middle, and bottom tiers."
        ),
        "survey_text": (
            "Randomly selected cartons from different pallet tiers and locations were opened for detailed inspection. "
            "Apple fruits inside the cartons were found with a mixture of sound, bruised, mechanically injured, and rotten condition "
            "in varying degrees. The condition found of Apple fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• The pulp temperature of the fresh Apple fruits was checked by means of a digital probe thermometer inside the cold room "
            "and was found in the range of 1.2°C to 2.0°C.\n"
            "• The pressure of randomly selected Apple fruits was checked with a fruit pressure tester and recorded between 14.5 "
            "and 17.0 lbs/cm².\n"
            "• Upon cutting the sound apples, the pulp was found firm and white; bruised fruits showed brownish discoloration "
            "below the epidermal layer."
        ),
    },

    # ── GRAPE ──────────────────────────────────────────────────────────────
    "GRAPE": {
        "label": "Fresh Table Grapes",
        "declared": "Fresh Table Grapes — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains approx. 9 kg packed in punnet trays with SO₂ pads.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "", "max": "", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the subject consignment of fresh table grapes upon destuffing. The cold room temperature was noted "
            "from the display as per observations recorded below."
        ),
        "para2_text": (
            "Container exterior was inspected; seal was found intact and verified in the presence of the attending parties. "
            "Upon door opening, cargo was stacked on pallets in an orderly manner. No evidence of reefer malfunction or "
            "carton collapse was noted. SO₂ pads were present and partially consumed, consistent with normal transit."
        ),
        "survey_text": (
            "Cartons from multiple pallet tiers were selected for 100% net weight segregation of grape berries by condition. "
            "The condition found of Fresh Table Grapes is presented in the table below in kilograms. (See Survey Photographs)\n\n"
            "• Pulp temperature was checked using a digital probe thermometer and found in the range of 0.8°C to 1.6°C.\n"
            "• Stems were predominantly green to slightly amber; bunch attachment was largely normal.\n"
            "• Brix (soluble solids) was checked via digital refractometer and found between 16.00% and 18.50%.\n"
            "• Soft and rotten grapes emitted a characteristic fermented odour; shatter berries were loose at carton base."
        ),
    },

    # ── BLUEBERRY ──────────────────────────────────────────────────────────
    "BLUEBERRY": {
        "label": "Fresh Blueberry",
        "declared": "Fresh Blueberries — [quantity and packing from the invoice]",
        "packing_note": "Packed in 125 g retail punnets; 8 punnets per master carton.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "", "max": "", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the blueberry consignment. The cold room temperature was recorded from the display. "
            "Representative cartons from different pallet positions and heights were selected for inspection."
        ),
        "para2_text": (
            "Container exterior, door gaskets, and seal were checked and found intact. "
            "Upon opening the container, blueberry cartons were stacked uniformly on pallets. "
            "Some cartons at the base of pallets showed minor compression marks but no moisture damage."
        ),
        "survey_text": (
            "Selected punnets were examined and weighed. Blueberries were segregated by condition — sound, soft, and rotten — "
            "and net weights recorded in kilograms per sampled carton. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 0.5°C to 2.0°C.\n"
            "• Soft berries were translucent, lacking firmness, and showed signs of early fungal activity on skin surface.\n"
            "• Rotten berries were collapsed with visible mould colonisation.\n"
            "• To mitigate further losses from the damaged blueberry fruits, we advised the Consignees to sell them immediately."
        ),
    },

    # ── ORANGE ─────────────────────────────────────────────────────────────
    "ORANGE": {
        "label": "Fresh Orange",
        "declared": "Fresh Orange Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains approx. 72–100 pcs individually wrapped in tissue.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "", "max": "", "unit": "%"},
            {"subject": "Pulp Condition", "method": "Cutting Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage facility to conduct a joint inspection "
            "of the subject consignment of fresh oranges. The reefer display temperature was noted. "
            "Cartons were randomly selected from different pallet positions for detailed examination."
        ),
        "para2_text": (
            "Container exterior and customs bottle seal were checked and found intact in the presence of the attending parties. "
            "Upon door opening, cartons were stacked on pallets in a uniform manner. "
            "Minor carton surface softening was noted on the outer layer but no structural carton collapse."
        ),
        "survey_text": (
            "Opened cartons were inspected fruit by fruit; oranges were sorted into sound, rotten, russet, and soft categories. "
            "The condition found of Fresh Orange Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 4.2°C to 5.1°C.\n"
            "• Upon cutting, pulp was found firm and juicy with normal internal coloration.\n"
            "• Russet fruits showed superficial skin browning; internal quality was acceptable in most cases.\n"
            "• Rotten fruits exhibited collapsed pulp with a fermented odour."
        ),
    },

    # ── PEAR ───────────────────────────────────────────────────────────────
    "PEAR": {
        "label": "Fresh Pear",
        "declared": "Fresh Pear Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton approx. 18 kg; fruits packed in individual poly bags.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (8 mm tip)", "min": "", "max": "", "unit": "lbs"},
            {"subject": "Internal Flesh Colour", "method": "Cutting Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to carry out a joint inspection "
            "of the subject pear consignment upon container destuffing. Cartons were selected randomly across pallet tiers."
        ),
        "para2_text": (
            "Container exterior, door seals, and customs seal were verified and found intact. "
            "Upon door opening, cargo was stacked uniformly on wooden pallets. "
            "Reefer temperature display and set point were verified and recorded."
        ),
        "survey_text": (
            "Selected cartons were opened and pear fruits were inspected piece by piece, sorted by condition. "
            "The condition found of Pear Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 0.5°C to 1.5°C.\n"
            "• Pressure readings using a penetrometer were found between 4.0 and 7.0 lbs indicating softening in parts.\n"
            "• Upon cutting, flesh of sound fruits was cream-coloured and firm; soft fruits showed brown discolouration progressing from core outward.\n"
            "• Shrivelled fruits had lost significant moisture; skin was wrinkled and fruit weight was noticeably reduced."
        ),
    },

    # ── KIWI ───────────────────────────────────────────────────────────────
    "KIWI": {
        "label": "Fresh Kiwi",
        "declared": "Fresh Kiwi Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains 36 or 42 pcs; fruits individually wrapped.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (8 mm tip)", "min": "", "max": "", "unit": "kg/cm²"},
            {"subject": "Internal Flesh Colour", "method": "Cutting Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the kiwi consignment upon container destuffing. The container was shifted to the nominated CFS "
            "for customs formalities and delivery prior to our inspection."
        ),
        "para2_text": (
            "Container exterior and customs seal were verified and found intact. "
            "Upon door opening, kiwi cartons were stacked uniformly on pallets. "
            "The cold room temperature was noted from the display as per the records below."
        ),
        "survey_text": (
            "Randomly selected cartons were opened for 100% piece-by-piece inspection. "
            "The condition found of Kiwi Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature of kiwi fruits was checked by means of a digital thermometer inside the cold room "
            "and was found in the range of 0.0°C to 1.5°C.\n"
            "• Upon cutting the soft/ripen kiwis, the pulp was found soft and juicy in varying degrees with pale yellow "
            "colour. A strong foul odour, unpleasant smell was noticed in all the soft kiwis — a clear indicator that "
            "the soft kiwis are no longer fit for human consumption.\n"
            "• Sound fruits were firm with bright green flesh and no internal discolouration."
        ),
    },

    # ── MANDARIN ───────────────────────────────────────────────────────────
    "MANDARIN": {
        "label": "Fresh Mandarin",
        "declared": "Fresh Mandarin Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton 9 kg net; packed with paper wrapping.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "", "max": "", "unit": "%"},
            {"subject": "Internal Flesh Quality", "method": "Cutting Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the cold storage to conduct a joint survey upon container destuffing. "
            "The containers carrying the subject cargo were shifted to the nominated CFS for customs formalities and delivery."
        ),
        "para2_text": (
            "Container exterior and customs seal were verified. Seal was found intact and cut in the presence of all parties. "
            "Reefer set point and temperature display were verified and recorded. "
            "Cartons were stacked on pallets in an orderly manner with no evidence of collapse or structural damage."
        ),
        "survey_text": (
            "Randomly selected cartons from different pallet locations were opened for detailed inspection. "
            "Mandarin fruits inside the cartons were found with a mixture of sound, soft, russet, rotten spot, and rotten condition "
            "in various degrees. The condition found of Mandarin Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was checked by means of a digital probe thermometer inside the cold room "
            "and was found in the range of 4.0°C to 4.6°C.\n"
            "• Brix was checked and found in the range of 10.00% to 12.00%.\n"
            "• Upon cutting, the pulp was found soft and juicy; rotten spot fruits showed brown necrotic patches on the peel and flesh."
        ),
    },

    # ── DRAGON ─────────────────────────────────────────────────────────────
    "DRAGON": {
        "label": "Fresh Dragon Fruit",
        "declared": "Fresh Dragon Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains approx. 10 kg; fruits packed individually in foam sleeves.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Pulp Colour", "method": "Visual Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the dragon fruit consignment upon container destuffing."
        ),
        "para2_text": (
            "Container exterior and customs seal were verified and found intact. "
            "Upon door opening, cargo was stacked on pallets uniformly. "
            "Reefer set point temperature was verified and recorded."
        ),
        "survey_text": (
            "Randomly selected cartons were opened and dragon fruits inspected piece by piece. "
            "The condition found of Dragon Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was checked inside the cold room and found in the range of 8.0°C to 10.0°C.\n"
            "• Sound fruits were firm with bright pink skin and scales intact.\n"
            "• Soft fruits showed indentation under light finger pressure; shrivelled fruits had lost moisture with wrinkled skin.\n"
            "• To mitigate further losses from the damaged dragon fruits, we advised the Consignees to sell them immediately."
        ),
    },

    # ── CHERRY ─────────────────────────────────────────────────────────────
    "CHERRY": {
        "label": "Fresh Cherry",
        "declared": "Fresh Cherries — [quantity and packing from the invoice]",
        "packing_note": "Each carton approx. 5 kg; fruits packed in 250 g retail punnets.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "", "max": "", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the cherry consignment. Representative cartons from different pallet positions were selected."
        ),
        "para2_text": (
            "Container exterior, door gaskets, and customs seal were checked and found intact. "
            "Upon door opening, cherry cartons were stacked uniformly on pallets. "
            "The reefer set point and temperature display were verified."
        ),
        "survey_text": (
            "Selected cartons and punnets were examined. Cherries were sorted into sound, soft, pitting, and rotten categories "
            "by piece count. The condition found of Cherry Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 0.0°C to 1.5°C.\n"
            "• Brix was checked and found between 18.00% and 22.00%, indicating good sugar content in sound fruits.\n"
            "• Soft cherries were translucent with slight indentation; pitting marks were surface-level circular depressions.\n"
            "• Rotten cherries showed collapsed flesh with mould on the skin surface."
        ),
    },

    # ── AVOCADO ────────────────────────────────────────────────────────────
    "AVOCADO": {
        "label": "Fresh Avocado",
        "declared": "Fresh Avocado — [quantity and packing from the invoice]",
        "packing_note": "Each carton contains approx. 24 pcs in size 24; packed in ventilated cartons.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Visual & Touch Assessment", "min": "", "max": "", "unit": "-"},
            {"subject": "Pulp Colour (on cut)", "method": "Cutting Inspection", "min": "", "max": "", "unit": "-"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the avocado consignment. The container was shifted to the CFS for customs formalities."
        ),
        "para2_text": (
            "Container exterior and seal were verified and found intact. "
            "Upon opening, avocado cartons were stacked uniformly on pallets. "
            "Cold room temperature was noted and reefer set point verified."
        ),
        "survey_text": (
            "Representative cartons were opened and avocados inspected piece by piece. "
            "The condition found of Avocado Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 5.5°C to 7.0°C.\n"
            "• Sound fruits were firm; soft fruits yielded under moderate finger pressure — consistent with partial ripening.\n"
            "• Soft-over-ripe fruits had black-streaked pulp; black & rotten fruits showed putrefaction and offensive odour.\n"
            "• Consignees are requested to sell sound and soft cargo immediately to mitigate further deterioration."
        ),
    },

    # ── PLUM ───────────────────────────────────────────────────────────────
    "PLUM": {
        "label": "Fresh Plum",
        "declared": "Fresh Plum Fruits — [quantity and packing from the invoice]",
        "packing_note": "Each carton approx. 5 kg; fruits packed in trays with paper wrapping.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Penetrometer (8 mm tip)", "min": "", "max": "", "unit": "kg/cm²"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the consignee's cold storage to conduct a joint survey "
            "of the subject plum consignment upon container destuffing."
        ),
        "para2_text": (
            "Container seal was verified and found intact in the presence of all attending representatives. "
            "Upon door opening, cargo was found stacked uniformly on pallets. "
            "Cold room temperature and reefer set point were verified."
        ),
        "survey_text": (
            "Selected cartons were opened and plum fruits inspected by piece. "
            "The category-wise details are as follows. The condition found of Plum Fruits is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 0.0°C to 2.0°C.\n"
            "• Sound fruits were firm with normal skin colour; russet fruits showed surface skin browning without pulp damage.\n"
            "• Soft fruits had lost firmness with internal browning; rotten fruits showed collapsed pulp and offensive odour.\n"
            "• To reduce the losses, we advised the consignees to sell the damaged plum fruits immediately."
        ),
    },

    # ── APRICOT ────────────────────────────────────────────────────────────
    "APRICOT": {
        "label": "Fresh Apricot",
        "declared": "Fresh Apricot, Peach & Nectarine — [quantity and packing from the invoice]",
        "packing_note": "Mixed fruit consignment; each carton approx. 5 kg.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "", "max": "", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Penetrometer (8 mm tip)", "min": "", "max": "", "unit": "kg/cm²"},
        ],
        "para1_text": (
            "We the undersigned surveyors attended at the cold storage to conduct a joint survey of the subject mixed stone "
            "fruit consignment upon container destuffing. The original pallets were dismantled prior to our visit."
        ),
        "para2_text": (
            "Container seal and exterior were verified. Upon opening, fruits were found stacked on pallets in cardboard cartons "
            "protected with cardboard sheets, stretched, wrapped, and fastened with nylon straps. "
            "Cold room temperature and reefer set point were verified."
        ),
        "survey_text": (
            "Selected cartons were opened and fruits inspected piece by piece, segregated by variety and condition. "
            "The condition found of Apricot, Peach & Nectarine is detailed in the table below. (See Survey Photographs)\n\n"
            "• Pulp temperature was found in the range of 1.0°C to 3.0°C.\n"
            "• Sound apricots were firm with good skin colour; soft apricots showed early ripening softness.\n"
            "• Rotten fruits showed collapsed flesh and offensive odour.\n"
            "• Consignees are requested to pursue any claims related matter directly with the responsible parties."
        ),
    },
}


# ---------------------------------------------------------------------------
# Helper: build blocks for a commodity from supplement data + archetype
# ---------------------------------------------------------------------------

def _build_blocks_for_commodity(
    commodity_key: str,
    supp: Dict[str, Any],
    archetype: Dict[str, Any],
    today_str: str,
    is_qc: bool,
) -> List[Dict[str, Any]]:
    """Build the complete list of blocks for a given commodity."""

    # Columns come from the same place the Verification Workbench gets them, so
    # the grid on the form and the grid the tally sheet is read into are the
    # same shape. They used to be taken from the keys of the sample rows below,
    # which is why the form showed six columns while the workbench offered the
    # eleven this fruit is actually graded on.
    from app.ingest.tally.categories import build_categories, unit_for

    categories = [{"key": c["key"], "label": c["label"]} for c in build_categories(commodity_key)]
    unit = unit_for(commodity_key) or archetype.get("unit", "pcs")
    label = supp.get("label", commodity_key.capitalize())

    # Determine heading label for the defect condition section
    # Prefer headings with "condition" that are NOT about graphs/charts
    _seq = archetype.get("heading_sequence", [])
    condition_heading = next(
        (h for h in _seq if "condition" in h.lower() and "graph" not in h.lower()),
        None,
    )
    if not condition_heading:
        # Fallback: the commodity label itself as heading
        condition_heading = f"CONDITION FOUND OF {commodity_key} FRUITS:"

    blocks: List[Dict[str, Any]] = []

    # ── Block 1: PARTICULARS ───────────────────────────────────────────────
    declared = supp.get("declared", f"Fresh {label}")
    blocks.append({
        "id": "b_particulars",
        "type": "particulars",
        "title": "PARTICULARS",
        "rows": [
            {"label": "Exporter / Shipper", "value": ["[Shipper Name, Country]"]},
            {"label": "Consignee", "value": ["[Consignee Name, City, India]"]},
            {"label": "Bill of Lading / AWB No.", "value": ["[B/L or AWB Number]"]},
            {"label": "Invoice No.", "value": ["[Invoice Number]"]},
            {"label": "Container / Carriage Unit", "value": ["[Container No.] (40' HC Reefer)"]},
            {"label": "Seal No.", "value": ["[Seal No.] (Found Intact)"]},
            {"label": "Carrying Vessel / Flight", "value": ["[Vessel Name / Flight No.]"]},
            {"label": "Port of Loading", "value": ["[Port of Loading]"]},
            {"label": "Port of Discharge", "value": ["Nhava Sheva (JNPT), India"]},
            {"label": "Cargo Declared", "value": [declared]},
            {"label": "Survey Date", "value": [today_str]},
            {"label": "Survey Location", "value": ["[Cold Storage Name & Address]"]},
        ],
    })

    # ── Block 2: PARAGRAPH 1 — APPLICATION ────────────────────────────────
    blocks.append({
        "id": "b_para1",
        "type": "narrative",
        "section": "PARAGRAPH 1: APPLICATION",
        "additional_text": supp.get("para1_text", ""),
    })

    # ── Block 3: PARAGRAPH 2 — CIRCUMSTANCES OF LOSS ──────────────────────
    blocks.append({
        "id": "b_para2",
        "type": "narrative",
        "section": "PARAGRAPH 2: CIRCUMSTANCES OF LOSS",
        "additional_text": supp.get("para2_text", ""),
    })

    # ── Note block (Container & site condition) ───────────────────────────
    blocks.append({
        "id": "b_note",
        "type": "narrative",
        "section": "NOTE:",
        "additional_text": (
            "NOTE: Upon our arrival, we observed that the container was no longer available on site. "
            "The Consignees informed us that the container had been destuffed and released back to the shipping line "
            "to avoid detention charges. As a result, container settings and initial door-opening stowage could not be physically verified."
        ),
    })

    # ── Block 4: PARAGRAPH 2.1 — OUR SURVEY ──────────────────────────────
    blocks.append({
        "id": "b_para2_1",
        "type": "narrative",
        "section": "PARAGRAPH 2.1: OUR SURVEY",
        "additional_text": supp.get("survey_text", ""),
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
    blocks.append({
        "id": "b_table",
        "type": "table",
        "title": condition_heading,
        "grouping_label": "Sample / Count",
        "unit": unit,
        "categories": categories,
        "rows": [],
        "show_title": bool(fruit.get("show_condition_found", True)),
        "show_chart": bool(fruit.get("show_chart", False)),
    })

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
        "additional_text": (
            f"According to the Bill of Lading, the requested carrying temperature for this shipment of fresh {label} fruits was "
            f"[SET POINT TEMP]. During our investigation, temperature recorder downloads were reviewed.\n\n"
            f"Based on our physical survey findings and cargo condition, the observed deterioration is consistent with "
            f"temperature variations and transit delays. Pressure bruising on sampled fruits points to harvesting and packing line sorting operations at origin."
        ),
    })

    # ── Block 9: PARAGRAPH 4 — NEXT STEP ──────────────────────────────────
    blocks.append({
        "id": "b_next_step",
        "type": "narrative",
        "section": "PARAGRAPH 4: NEXT STEP",
        "additional_text": (
            f"1. To mitigate losses from the damaged {label} fruits cargo, we advised the Consignees to sell the consignment immediately at best realizable price to avoid further commercial deterioration.\n\n"
            f"2. Consignees are requested to lodge a formal Notice of Claim against the Ocean Carrier / Shipping Line within statutory time limits, holding them liable for transit losses.\n\n"
            f"3. We reserve the right to issue a Final Survey Report upon receipt and examination of complete temperature recorder downloads and salvage sale invoices."
        ),
    })

    # ── Block 10: PARAGRAPH 5 — DOCUMENTATION ──────────────────────────────
    blocks.append({
        "id": "b_doc",
        "type": "narrative",
        "section": "PARAGRAPH 5: DOCUMENTATION",
        "additional_text": (
            "Documentation secured and reviewed during our enquiries and site attendance includes:\n"
            "• Ocean Bill of Lading\n"
            "• Commercial Invoice & Packing List\n"
            "• Portable Temperature Recorder (Data Logger) Download Report\n"
            "• Container Equipment Interchange Receipt (EIR) / CFS Gate Pass\n"
            "• Survey Photographs (Photo Plates attached hereto)"
        ),
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
# General Cargo Block Builder (Gladstone & MCA Format)
# ---------------------------------------------------------------------------

_GC_COMMODITY_CONFIG: Dict[str, Dict[str, Any]] = {
    "STEEL_METALS": {
        "label": "Steel & Metal Products",
        "cargo_desc": "Prime Hot Rolled / Cold Rolled Steel Coils / Pipe Bundles in export seaworthy packing",
        "survey_findings": (
            "1. STRUCTURAL CONDITION OF CONTAINER:\n"
            "External inspection revealed the container panels to be structurally sound without visible perforations. "
            "Door rubber gaskets were inspected and found in pliable, weather-tight condition. Visual light testing inside the "
            "closed container showed no daylight penetration from the roof or side panels.\n\n"
            "2. CARGO STOWAGE & LASHINGS:\n"
            "Coils were stowed on heavy wooden cradles/dunnage chocks and secured with high-tensile steel straps and wire rope "
            "lashings connected with turnbuckles. Certain coils located in forward bay exhibited longitudinal displacement, "
            "scuffing against side walls, and loosened strapping.\n\n"
            "3. CHEMICAL TESTING (SILVER NITRATE):\n"
            "Silver nitrate solution (2% AgNO3) chemical testing was conducted on oxidized surfaces of the coils. No milky precipitate "
            "or white cloudiness was observed, confirming the absence of sea water chlorides (fresh water / atmospheric oxidation)."
        ),
        "cause_of_loss": (
            "Based on our physical inspection, the observed physical impact and edge deformations are attributed to "
            "excessive motion, longitudinal acceleration, and heavy rolling of the carrying vessel during sea transit, causing coils "
            "to strain against lashings. There was no evidence of sea water ingress (AgNO3 test negative). "
            "Carrier liability is formally reserved and consignees have lodged a formal Notice of Claim."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Coils"},
            {"key": "surface_rust", "label": "Surface Rust (Grade B)"},
            {"key": "heavy_rust", "label": "Heavy Rust / Pitted"},
            {"key": "dented_bent", "label": "Dented / Deformed Edges"},
            {"key": "telescoped", "label": "Telescoped / Oval Coils"},
            {"key": "shortage", "label": "Shortage / Missing"},
        ],
        "rows": [
            {
                "group": "Coil Lot #1 (Coils 01-05)",
                "boxes_opened": 5,
                "values": {"sound": 4, "surface_rust": 1, "heavy_rust": 0, "dented_bent": 0, "telescoped": 0, "shortage": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Coil Lot #2 (Coils 06-12)",
                "boxes_opened": 7,
                "values": {"sound": 5, "surface_rust": 1, "heavy_rust": 0, "dented_bent": 1, "telescoped": 0, "shortage": 0},
                "provenance": "user_declared",
            },
        ],
    },
    "MACHINERY_PARTS": {
        "label": "Machinery & Equipment",
        "cargo_desc": "Industrial Machinery, Assemblies & Mechanical Equipment Components in Wooden Crates",
        "survey_findings": (
            "1. PACKAGING & EXTERNAL CONDITION:\n"
            "Inspection of the wooden crates revealed heavy impact marks, splintered wooden battens, and skid displacements "
            "on certain packages. Tilt/drop impact indicators attached to crate exterior were inspected.\n\n"
            "2. PHYSICAL EXAMINATION OF MACHINERY:\n"
            "Upon uncrating in the presence of technical engineers, localized mechanical damages including fractured castings, "
            "bent mounting brackets, and sheared bolts were observed. Internal anti-rust VCI film was torn on affected units."
        ),
        "cause_of_loss": (
            "The physical damage sustained was attributable to sudden impact and rough handling during transhipment / shore crane "
            "operations. Shock sensors indicated acceleration exceeding design limits. Notice of claim issued against bailees."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Packages"},
            {"key": "broken_cracked", "label": "Broken / Cracked Castings"},
            {"key": "dented_deformed", "label": "Dented Panels / Bent Frame"},
            {"key": "scratched", "label": "Scratched / Scuffed"},
            {"key": "missing_parts", "label": "Missing Components"},
            {"key": "moisture", "label": "Moisture Affected"},
        ],
        "rows": [
            {
                "group": "Crate Lot #1 (Main Units)",
                "boxes_opened": 3,
                "values": {"sound": 2, "broken_cracked": 1, "dented_deformed": 0, "scratched": 0, "missing_parts": 0, "moisture": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Crate Lot #2 (Accessories & Spares)",
                "boxes_opened": 8,
                "values": {"sound": 6, "broken_cracked": 0, "dented_deformed": 1, "scratched": 1, "missing_parts": 0, "moisture": 0},
                "provenance": "user_declared",
            },
        ],
    },
    "AUTOMOTIVE": {
        "label": "Automotive & Parts",
        "cargo_desc": "Automotive Components, Assemblies & Spare Parts in Palletized Cartons",
        "survey_findings": (
            "1. PACKAGING & EXTERNAL CONDITION:\n"
            "Cartons were stowed on wooden pallets shrink-wrapped with stretch film. Pallets in doorway exhibited crushed corners "
            "and torn wrapping from forklift handling.\n\n"
            "2. INTERNAL EXAMINATION:\n"
            "Component parts inside affected cartons showed surface abrasions, scuffing, and minor panel deformations."
        ),
        "cause_of_loss": (
            "Damage resulted from excessive stacking pressure and rough forklift handling during container stuffing/destuffing operations."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Cartons"},
            {"key": "dented_impact", "label": "Dented / Impacted"},
            {"key": "scratched", "label": "Scratched / Scuffed"},
            {"key": "torn_pkg", "label": "Torn / Crushed Packaging"},
            {"key": "corrosion", "label": "Rust / Corrosion"},
            {"key": "shortage", "label": "Shortage / Pilfered"},
        ],
        "rows": [
            {
                "group": "Pallet 01 - Body Panels",
                "boxes_opened": 20,
                "values": {"sound": 17, "dented_impact": 2, "scratched": 1, "torn_pkg": 0, "corrosion": 0, "shortage": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Pallet 02 - Trim & Fixtures",
                "boxes_opened": 25,
                "values": {"sound": 22, "dented_impact": 0, "scratched": 1, "torn_pkg": 2, "corrosion": 0, "shortage": 0},
                "provenance": "user_declared",
            },
        ],
    },
    "CHEMICALS_LIQUIDS": {
        "label": "Chemicals & Liquids",
        "cargo_desc": "Industrial Chemicals / Liquid Cargo in Tight-head Steel Drums & Composite IBC Tanks",
        "survey_findings": (
            "1. CONTAINER & DRUM CONDITION:\n"
            "Upon opening container doors, chemical odor was noted. Several steel drums in lower tier exhibited dented chimes, "
            "rim deformation, and product seepage over floor panels.\n\n"
            "2. LEAKAGE QUANTIFICATION:\n"
            "Affected drums were weighed individually to determine ullage and net product loss against standard tare weights."
        ),
        "cause_of_loss": (
            "Puncture and rim deformation sustained due to inadequate vertical bracing and shifting during sudden vessel maneuvers in transit."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Drums / IBCs"},
            {"key": "leaking", "label": "Leaking / Punctured"},
            {"key": "dented_chimes", "label": "Dented Rims & Chimes"},
            {"key": "bulged", "label": "Bulged / Deformed"},
            {"key": "contaminated", "label": "Contaminated"},
            {"key": "empty_shortage", "label": "Empty / Shortage"},
        ],
        "rows": [
            {
                "group": "Tier 1 - Steel Drums 01-40",
                "boxes_opened": 40,
                "values": {"sound": 36, "leaking": 2, "dented_chimes": 2, "bulged": 0, "contaminated": 0, "empty_shortage": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Tier 2 - Steel Drums 41-80",
                "boxes_opened": 40,
                "values": {"sound": 39, "leaking": 0, "dented_chimes": 1, "bulged": 0, "contaminated": 0, "empty_shortage": 0},
                "provenance": "user_declared",
            },
        ],
    },
    "PAPER_PACKAGING": {
        "label": "Paper & Packaging",
        "cargo_desc": "Paper Reels / Packaging Kraft Board in Export Bundles with Moisture Barriers",
        "survey_findings": (
            "1. REEL CONDITION & PACKAGING:\n"
            "Reels were stowed on end. Several reels showed gouged edges, torn outer wrapper layers, and clamp indentation marks.\n\n"
            "2. MOISTURE READINGS:\n"
            "Moisture meter readings on outer paper plies showed normal moisture content (6-8%), confirming physical handling damage."
        ),
        "cause_of_loss": (
            "Edge gouging and clamp marks caused by improper clamp truck handling and contact with container side walls in transit."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Reels"},
            {"key": "clamp_damage", "label": "Clamp Impact Damage"},
            {"key": "torn_wrapper", "label": "Torn Outer Wrapper"},
            {"key": "edge_gouged", "label": "Edge Gouged / Chipped"},
            {"key": "wet_moisture", "label": "Wet / Moisture"},
            {"key": "crushed_core", "label": "Crushed / Deformed Core"},
        ],
        "rows": [
            {
                "group": "Reel Lot A (Reels 01-10)",
                "boxes_opened": 10,
                "values": {"sound": 8, "clamp_damage": 1, "torn_wrapper": 0, "edge_gouged": 1, "wet_moisture": 0, "crushed_core": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Reel Lot B (Reels 11-24)",
                "boxes_opened": 14,
                "values": {"sound": 12, "clamp_damage": 1, "torn_wrapper": 1, "edge_gouged": 0, "wet_moisture": 0, "crushed_core": 0},
                "provenance": "user_declared",
            },
        ],
    },
    "GENERAL_CARGO": {
        "label": "General Merchandise & Breakbulk",
        "cargo_desc": "General Breakbulk Merchandise & Manufactured Products in Export Packing",
        "survey_findings": (
            "1. STRUCTURAL CONDITION OF THE CONTAINER:\n"
            "External inspection revealed the container panels to be structurally sound without visible perforations or punctures. "
            "Door rubber gaskets were inspected and found in pliable, weather-tight condition. Visual light testing inside the closed container "
            "showed no daylight penetration from the roof or side panels.\n\n"
            "2. CARGO STOWAGE & SECURING:\n"
            "Upon opening the doors, cargo packages were observed stacked inside the container. Securing lashing polyester straps and wooden dunnage "
            "chocks were inspected. Certain packages located in doorway exhibited displacement, impact creases, and shifting during transit."
        ),
        "cause_of_loss": (
            "Based on our physical inspection, the observed physical impact and exterior case deformations are attributed to "
            "excessive motion, longitudinal acceleration, and heavy impact sustained during handling and intermodal sea/road transit. "
            "Carrier and stevedore liabilities are formally reserved."
        ),
        "categories": [
            {"key": "sound", "label": "Sound Units"},
            {"key": "dented_crushed", "label": "Dented / Crushed"},
            {"key": "torn_cut", "label": "Torn / Cut Bags"},
            {"key": "wet_moisture", "label": "Wet / Moisture Affected"},
            {"key": "rust_moisture", "label": "Rust / Oxidation"},
            {"key": "shortage", "label": "Shortage / Missing"},
        ],
        "rows": [
            {
                "group": "Item Lot #1 (Cases 01-10)",
                "boxes_opened": 10,
                "values": {"sound": 8, "dented_crushed": 2, "torn_cut": 0, "wet_moisture": 0, "rust_moisture": 0, "shortage": 0},
                "provenance": "user_declared",
            },
            {
                "group": "Item Lot #2 (Cases 11-25)",
                "boxes_opened": 15,
                "values": {"sound": 12, "dented_crushed": 1, "torn_cut": 2, "wet_moisture": 0, "rust_moisture": 0, "shortage": 0},
                "provenance": "user_declared",
            },
        ],
    },
}


def _build_blocks_for_general_cargo(
    is_air: bool,
    is_preliminary: bool,
    today_str: str,
    commodity_key: Optional[str] = None,
    selected_sections: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Builds authentic block sequence for General Cargo reports (Gladstone / MCA format),
    tailored to the specific cargo subcategory (Steel, Machinery, Automotive, Chemicals, Paper, General).
    Supports client section selection.
    """
    cat_key = (commodity_key or "GENERAL_CARGO").upper()
    cfg = _GC_COMMODITY_CONFIG.get(cat_key, _GC_COMMODITY_CONFIG["GENERAL_CARGO"])

    disclaimer = (
        "This preliminary survey report is issued based on observations made at the time of inspection "
        "and without prejudice to liability, terms, and conditions of applicable insurance policies and carrier contracts."
        if is_preliminary
        else "This survey report is issued without prejudice to the liability of any party and is subject to the terms, conditions, and exceptions of the governing policy of insurance."
    )

    all_blocks: List[Tuple[str, Dict[str, Any]]] = []

    # 1. Particulars
    all_blocks.append(("particulars", {
        "id": "b_particulars",
        "type": "particulars",
        "title": "CONSIGNMENT PARTICULARS",
        "rows": [
            {"label": "Vessel / Voyage" if not is_air else "Flight / Date", "value": "[VESSEL / FLIGHT]", "provenance": "user_declared"},
            {"label": "Bill of Lading / AWB No." if not is_air else "Air Waybill No.", "value": "[B/L or AWB NUMBER]", "provenance": "user_declared"},
            {"label": "Container No. & Seal No.", "value": "[CONTAINER NO.] / [SEAL NO.]", "provenance": "user_declared"},
            {"label": "Shipper", "value": "[SHIPPER NAME & ADDRESS]", "provenance": "user_declared"},
            {"label": "Consignee", "value": "[CONSIGNEE NAME & ADDRESS]", "provenance": "user_declared"},
            {"label": "Cargo Description", "value": cfg["cargo_desc"], "provenance": "user_declared"},
            {"label": "Declared B/L Gross Weight", "value": "[DECLARED GROSS WT (KG)]", "provenance": "user_declared"},
            {"label": "Port of Loading", "value": "[PORT OF LOADING]", "provenance": "user_declared"},
            {"label": "Port of Discharge", "value": "Nhava Sheva (JNPT), India" if not is_air else "Mumbai Air Cargo Complex", "provenance": "user_declared"},
            {"label": "Place & Date of Survey", "value": f"Consignee's CFS / Warehouse, {today_str}", "provenance": "user_declared"},
        ],
    }))

    # 2. Attendance
    all_blocks.append(("attendance", {
        "id": "b_attendance",
        "type": "attendance",
        "title": "ATTENDANCE REGISTER",
        "rows": [
            {"name": "Mr. [SURVEYOR NAME]", "representing": "Marine Cargo Agencies Pvt. Ltd. (Independent Surveyors)"},
            {"name": "Mr. [CONSIGNEE REP]", "representing": "Consignee / Importer Representative"},
            {"name": "Mr. [CFS / CARRIER REP]", "representing": "CFS Logistics / Shipping Line Representative"},
        ],
    }))

    # 3. Circumstances of Loss
    all_blocks.append(("narrative_circ", {
        "id": "b_narrative_circ",
        "type": "narrative",
        "section": "CIRCUMSTANCES OF LOSS & INSTRUCTIONS",
        "additional_text": (
            f"Under instructions received from the Underwriters / Instructing Principals, we attended the joint survey on {today_str} "
            f"at the Consignee's premises to ascertain the nature, cause, and extent of alleged loss/damage to the subject consignment of {cfg['label']}. "
            f"The container was reported to have arrived on board the carrier and was discharged at the port prior to destuffing. "
            f"The original bolt seal was verified intact prior to cutting and opening in the presence of attending representatives."
        ),
    }))

    # 4. Our Survey (Container Condition & Cargo Inspection)
    all_blocks.append(("narrative_survey", {
        "id": "b_narrative_survey",
        "type": "narrative",
        "section": "OUR SURVEY & FINDINGS",
        "additional_text": cfg["survey_findings"],
    }))

    # 5. Damage Table
    all_blocks.append(("table", {
        "id": "b_table",
        "type": "table",
        "title": f"{cfg['label'].upper()} DAMAGE INVENTORY & RECONCILIATION",
        "grouping_label": "Package Item / Lot",
        "unit": "pcs",
        "categories": cfg["categories"],
        "rows": cfg["rows"],
    }))

    # 6. Cause of Loss & Liability
    all_blocks.append(("narrative_cause", {
        "id": "b_narrative_cause",
        "type": "narrative",
        "section": "CAUSE OF LOSS & LIABILITY OBSERVATIONS",
        "additional_text": cfg["cause_of_loss"],
    }))

    # 7. Claim Reserve (Preliminary) or Final Claim (Final)
    if is_preliminary:
        all_blocks.append(("narrative_reserve", {
            "id": "b_narrative_reserve",
            "type": "narrative",
            "section": "CLAIM RESERVE & ESTIMATE",
            "additional_text": (
                "CLAIM RESERVE (PRELIMINARY):\n"
                "Pending final testing, repair quotation, and commercial invoice quantification from the Consignees, "
                f"an initial claim reserve of INR [ESTIMATED RESERVE] / USD [RESERVE USD] is recommended against this {cfg['label']} consignment. "
                "This reserve is provisional and subject to adjustment upon production of salvage proceeds and documentary evidence."
            ),
        }))
    else:
        all_blocks.append(("narrative_reserve", {
            "id": "b_narrative_final_claim",
            "type": "narrative",
            "section": "FINAL LOSS ADJUSTMENT & QUANTIFICATION",
            "additional_text": (
                "FINAL QUANTIFICATION:\n"
                "The loss has been adjusted on the basis of verified CIF commercial values and agreed depreciation/repair costs: "
                "Gross Assessed Loss: INR [AMOUNT] less Agreed Salvage Retention: INR [SALVAGE], resulting in Net Adjusted Loss of INR [NET AMOUNT]. "
                "Adjusted without prejudice to terms, conditions, and deductibles of the policy."
            ),
        }))

    # 8. Survey Photographs
    all_blocks.append(("photos", {
        "id": "b_photos",
        "type": "photo_plate",
        "title": "SURVEY PHOTOGRAPHS",
        "series_id": "survey",
        "label": "Survey",
        "provenance": "own_survey",
        "columns": 2,
        # Empty for the same reason as the perishable plate above.
        "groups": [],
    }))

    # 9. Documentation / List of Enclosures
    all_blocks.append(("enclosures", {
        "id": "b_enclosures",
        "type": "fixed_text",
        "title": "DOCUMENTATION & ANNEXURES SCHEDULE",
        "content": (
            "1. Copy of Ocean Bill of Lading / Air Waybill\n"
            "2. Copy of Commercial Invoice and Packing List\n"
            "3. Copy of Weighbridge Slip / Delivery Order\n"
            "4. Container Destuffing Tally / Gate Pass\n"
            "5. Consignee Letter of Protest / Notice of Claim to Carrier\n"
            "6. Survey Photographic Annexure Sheet"
        ),
    }))

    # 10. Closure
    all_blocks.append(("closure", {
        "id": "b_closure",
        "type": "fixed_text",
        "title": "CLOSURE",
        "content": (
            f"{disclaimer}\n\n"
            "Consignees are requested to pursue any claims-related matter directly with the responsible carrier/parties.\n\n"
            "“ISSUED WITHOUT PREJUDICE”\n"
            f"Dated: {today_str}\n"
            "Marine Cargo Agencies Pvt. Ltd.\n"
            "ØØØ"
        ),
    }))

    # Filter blocks if client selected specific sections
    if selected_sections and len(selected_sections) > 0:
        sel_set = set(selected_sections)
        blocks = [blk for sec_id, blk in all_blocks if sec_id in sel_set]
        # Always guarantee at least particulars
        if not blocks:
            blocks = [blk for sec_id, blk in all_blocks if sec_id == "particulars"]
    else:
        blocks = [blk for _, blk in all_blocks]

    return blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_GC_KEYS = {"STEEL_METALS", "MACHINERY_PARTS", "AUTOMOTIVE", "CHEMICALS_LIQUIDS", "PAPER_PACKAGING", "GENERAL_CARGO"}


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
        commodity_val = commodity_upper if commodity_upper in _GC_KEYS else "GENERAL_CARGO"
        cfg = _GC_COMMODITY_CONFIG.get(commodity_val, _GC_COMMODITY_CONFIG["GENERAL_CARGO"])
        blocks = _build_blocks_for_general_cargo(
            is_air=is_air,
            is_preliminary=is_preliminary,
            today_str=today_str,
            commodity_key=commodity_val,
            selected_sections=selected_sections,
        )
        report_title = (
            f"PRELIMINARY GENERAL CARGO SURVEY REPORT (PLA) — {cfg['label'].upper()}" if is_preliminary
            else f"FINAL GENERAL CARGO SURVEY REPORT — {cfg['label'].upper()}"
        )
        metadata = {
            "docx_template": "mca-general-canonical-v1.docx",
            "family": "SURVEY_REPORT",
            "commodity": commodity_val,
            "state": "PRELIMINARY" if is_preliminary else "FINAL",
        }
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
            "destination": "Nhava Sheva, India" if mode == "SEA" else "Mumbai Airport, India",
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
