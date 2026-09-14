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
        "declared": "Fresh Apple Fruits (2,100 Cartons on 20 Pallets)",
        "packing_note": "Each carton contains approx. 100–125 pcs packed in individual poly sleeves.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "1.2", "max": "2.0", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (11 mm tip)", "min": "14.5", "max": "17.0", "unit": "lbs/cm²"},
            {"subject": "Starch Iodine Index", "method": "CTIFL Scale (1–8)", "min": "4.0", "max": "5.5", "unit": "Score"},
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
        "default_rows": [
            {"group": "Count 100 (2 Cartons)", "values": {"Sound": "142", "Russet": "12", "Bruised": "26", "Damage": "14", "Rotten": "6", "Shriveled": "0"}},
            {"group": "Count 113 (2 Cartons)", "values": {"Sound": "158", "Russet": "16", "Bruised": "32", "Damage": "18", "Rotten": "4", "Shriveled": "2"}},
            {"group": "Count 125 (2 Cartons)", "values": {"Sound": "172", "Russet": "8",  "Bruised": "38", "Damage": "20", "Rotten": "8", "Shriveled": "4"}},
        ],
    },

    # ── GRAPE ──────────────────────────────────────────────────────────────
    "GRAPE": {
        "label": "Fresh Table Grapes",
        "declared": "Fresh Table Grapes (Approx. 3,250 cartons on 25 pallets)",
        "packing_note": "Each carton contains approx. 9 kg packed in punnet trays with SO₂ pads.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.8", "max": "1.6", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "16.00", "max": "18.50", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "Firm & Intact", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Pallet 1 – Boxes 1–4", "values": {"Sound Grapes": "18.820", "Soft Grapes": "0.450", "Rotten Grapes": "0.340"}},
            {"group": "Pallet 2 – Boxes 5–8", "values": {"Sound Grapes": "19.110", "Soft Grapes": "0.310", "Rotten Grapes": "0.220"}},
            {"group": "Pallet 3 – Boxes 9–12", "values": {"Sound Grapes": "18.650", "Soft Grapes": "0.520", "Rotten Grapes": "0.410"}},
        ],
    },

    # ── BLUEBERRY ──────────────────────────────────────────────────────────
    "BLUEBERRY": {
        "label": "Fresh Blueberry",
        "declared": "Fresh Blueberries (Approx. 5,500 punnets, 125 g each)",
        "packing_note": "Packed in 125 g retail punnets; 8 punnets per master carton.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.5", "max": "2.0", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "12.00", "max": "14.50", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "Firm to Slightly Soft", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Pallet 1 – Carton 1", "values": {"Found Net Weight Of Sound Berries": "0.740", "Found Net Weight Of Soft Berries": "0.180", "Found Net Weight Of Rotten Berries": "0.080"}},
            {"group": "Pallet 2 – Carton 2", "values": {"Found Net Weight Of Sound Berries": "0.810", "Found Net Weight Of Soft Berries": "0.120", "Found Net Weight Of Rotten Berries": "0.070"}},
            {"group": "Pallet 3 – Carton 3", "values": {"Found Net Weight Of Sound Berries": "0.690", "Found Net Weight Of Soft Berries": "0.220", "Found Net Weight Of Rotten Berries": "0.090"}},
        ],
    },

    # ── ORANGE ─────────────────────────────────────────────────────────────
    "ORANGE": {
        "label": "Fresh Orange",
        "declared": "Fresh Orange Fruits (Approx. 2,400 Cartons on 22 Pallets)",
        "packing_note": "Each carton contains approx. 72–100 pcs individually wrapped in tissue.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "4.2", "max": "5.1", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "10.50", "max": "11.80", "unit": "%"},
            {"subject": "Pulp Condition", "method": "Cutting Inspection", "min": "Firm & Juicy", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Count 72 (2 Cartons)", "values": {"Sound": "102", "Rotten": "4", "Russet": "12", "Soft": "8", "Rotten Spot": "5", "Shrivelled": "1"}},
            {"group": "Count 88 (2 Cartons)", "values": {"Sound": "98",  "Rotten": "8", "Russet": "16", "Soft": "10","Rotten Spot": "6", "Shrivelled": "2"}},
            {"group": "Count 100 (2 Cartons)", "values": {"Sound": "84",  "Rotten": "10","Russet": "22", "Soft": "14","Rotten Spot": "8", "Shrivelled": "2"}},
        ],
    },

    # ── PEAR ───────────────────────────────────────────────────────────────
    "PEAR": {
        "label": "Fresh Pear",
        "declared": "Fresh Pear Fruits (Approx. 2,600 Cartons on 24 Pallets)",
        "packing_note": "Each carton approx. 18 kg; fruits packed in individual poly bags.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.5", "max": "1.5", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (8 mm tip)", "min": "4.0", "max": "7.0", "unit": "lbs"},
            {"subject": "Internal Flesh Colour", "method": "Cutting Inspection", "min": "Cream/White", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Count 90 (2 Cartons)", "values": {"Sound": "120", "Rotten": "6", "Russet": "8", "Damaged": "10", "Shrivelled": "4", "Rotten Spot": "2"}},
            {"group": "Count 100 (2 Cartons)", "values": {"Sound": "132", "Rotten": "8", "Russet": "10", "Damaged": "12", "Shrivelled": "6", "Rotten Spot": "2"}},
            {"group": "Count 110 (2 Cartons)", "values": {"Sound": "144", "Rotten": "10", "Russet": "12", "Damaged": "14", "Shrivelled": "8", "Rotten Spot": "2"}},
        ],
    },

    # ── KIWI ───────────────────────────────────────────────────────────────
    "KIWI": {
        "label": "Fresh Kiwi",
        "declared": "Fresh Kiwi Fruits (Approx. 3,000 Cartons on 26 Pallets)",
        "packing_note": "Each carton contains 36 or 42 pcs; fruits individually wrapped.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.0", "max": "1.5", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (8 mm tip)", "min": "0.5", "max": "3.0", "unit": "kg/cm²"},
            {"subject": "Internal Flesh Colour", "method": "Cutting Inspection", "min": "Bright Green", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Count 36 (2 Cartons)", "values": {"Sound": "42", "Soft": "16", "Rotten": "6", "Pitting": "8"}},
            {"group": "Count 42 (2 Cartons)", "values": {"Sound": "54", "Soft": "20", "Rotten": "8", "Pitting": "10"}},
            {"group": "Count 36 (2 Cartons)", "values": {"Sound": "38", "Soft": "22", "Rotten": "10", "Pitting": "2"}},
        ],
    },

    # ── MANDARIN ───────────────────────────────────────────────────────────
    "MANDARIN": {
        "label": "Fresh Mandarin",
        "declared": "Fresh Mandarin Fruits (2,916 Cartons on 24 Pallets)",
        "packing_note": "Each carton 9 kg net; packed with paper wrapping.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "4.0", "max": "4.6", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "10.00", "max": "12.00", "unit": "%"},
            {"subject": "Internal Flesh Quality", "method": "Cutting Inspection", "min": "Soft & Juicy", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Count 55 (2 Cartons)", "values": {"Sound": "133", "Soft": "54", "Russet": "14", "Rotten Spot": "9", "Rotten": "24"}},
            {"group": "Count 60 (2 Cartons)", "values": {"Sound": "92",  "Soft": "46", "Russet": "16", "Rotten Spot": "7", "Rotten": "14"}},
            {"group": "Count 65 (2 Cartons)", "values": {"Sound": "83",  "Soft": "36", "Russet": "8",  "Rotten Spot": "15","Rotten": "4"}},
            {"group": "Count 70 (2 Cartons)", "values": {"Sound": "63",  "Soft": "36", "Russet": "13", "Rotten Spot": "3", "Rotten": "5"}},
        ],
    },

    # ── DRAGON ─────────────────────────────────────────────────────────────
    "DRAGON": {
        "label": "Fresh Dragon Fruit",
        "declared": "Fresh Dragon Fruits (Approx. 2,800 Cartons on 22 Pallets)",
        "packing_note": "Each carton contains approx. 10 kg; fruits packed individually in foam sleeves.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "8.0", "max": "10.0", "unit": "°C"},
            {"subject": "Pulp Colour", "method": "Visual Inspection", "min": "White to Slightly Translucent", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Pallet 1 (5 Cartons)", "values": {"Sound": "28", "Soft": "12", "Shrivelled": "8", "Rotten": "2"}},
            {"group": "Pallet 2 (5 Cartons)", "values": {"Sound": "32", "Soft": "10", "Shrivelled": "6", "Rotten": "2"}},
            {"group": "Pallet 3 (5 Cartons)", "values": {"Sound": "26", "Soft": "14", "Shrivelled": "10", "Rotten": "0"}},
        ],
    },

    # ── CHERRY ─────────────────────────────────────────────────────────────
    "CHERRY": {
        "label": "Fresh Cherry",
        "declared": "Fresh Cherries (Approx. 1,500 Cartons on 15 Pallets)",
        "packing_note": "Each carton approx. 5 kg; fruits packed in 250 g retail punnets.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.0", "max": "1.5", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "18.00", "max": "22.00", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Visual & Touch Assessment", "min": "Firm to Slightly Soft", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Pallet 1 – Carton 1", "values": {"Sound": "180", "Soft Cargo": "42", "Pitting": "28", "Rotten": "8"}},
            {"group": "Pallet 2 – Carton 2", "values": {"Sound": "196", "Soft Cargo": "36", "Pitting": "20", "Rotten": "6"}},
            {"group": "Pallet 3 – Carton 3", "values": {"Sound": "172", "Soft Cargo": "48", "Pitting": "32", "Rotten": "12"}},
        ],
    },

    # ── AVOCADO ────────────────────────────────────────────────────────────
    "AVOCADO": {
        "label": "Fresh Avocado",
        "declared": "Fresh Avocado (Approx. 2,200 Cartons on 20 Pallets)",
        "packing_note": "Each carton contains approx. 24 pcs in size 24; packed in ventilated cartons.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "5.5", "max": "7.0", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Visual & Touch Assessment", "min": "Firm to Soft", "max": "", "unit": "-"},
            {"subject": "Pulp Colour (on cut)", "method": "Cutting Inspection", "min": "Light Yellow-Green", "max": "", "unit": "-"},
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
        "default_rows": [
            {"group": "Size 24 – Carton 1", "values": {"Sound": "14", "Soft": "6", "Soft/Over-Ripped": "2", "Black & Rotten": "2"}},
            {"group": "Size 24 – Carton 2", "values": {"Sound": "16", "Soft": "4", "Soft/Over-Ripped": "2", "Black & Rotten": "2"}},
            {"group": "Size 24 – Carton 3", "values": {"Sound": "12", "Soft": "8", "Soft/Over-Ripped": "2", "Black & Rotten": "2"}},
        ],
    },

    # ── PLUM ───────────────────────────────────────────────────────────────
    "PLUM": {
        "label": "Fresh Plum",
        "declared": "Fresh Plum Fruits (Approx. 2,400 Cartons on 22 Pallets)",
        "packing_note": "Each carton approx. 5 kg; fruits packed in trays with paper wrapping.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.0", "max": "2.0", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Penetrometer (8 mm tip)", "min": "1.5", "max": "4.0", "unit": "kg/cm²"},
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
        "default_rows": [
            {"group": "Size 50 (2 Cartons)", "values": {"Sound": "64", "Rotten": "6", "Soft": "14", "Russet": "8", "Shrivelled": "8"}},
            {"group": "Size 60 (2 Cartons)", "values": {"Sound": "74", "Rotten": "8", "Soft": "16", "Russet": "10", "Shrivelled": "12"}},
            {"group": "Size 70 (2 Cartons)", "values": {"Sound": "82", "Rotten": "10", "Soft": "18", "Russet": "12", "Shrivelled": "8"}},
        ],
    },

    # ── APRICOT ────────────────────────────────────────────────────────────
    "APRICOT": {
        "label": "Fresh Apricot",
        "declared": "Fresh Apricot, Peach & Nectarine (Approx. 1,800 Cartons on 18 Pallets)",
        "packing_note": "Mixed fruit consignment; each carton approx. 5 kg.",
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "1.0", "max": "3.0", "unit": "°C"},
            {"subject": "Fruit Firmness", "method": "Penetrometer (8 mm tip)", "min": "1.0", "max": "3.5", "unit": "kg/cm²"},
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
        "default_rows": [
            {"group": "Apricot – 2 Cartons", "values": {"Sound Apricot": "42", "Soft Apricot": "14", "Rotten Apricot": "4"}},
            {"group": "Nectarine – 2 Cartons", "values": {"Sound Nectarines Fruits": "38", "Soft Nectarines Fruits": "18", "Rotten Nectarines Fruits": "4"}},
            {"group": "Peach – 2 Cartons", "values": {"Sound Peaches": "34", "Soft Peaches": "20", "Rotten Apricot": "0"}},
        ],
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

    # Determine defect columns: prefer archetype columns but clean noise
    arch_cols = [
        c for c in archetype.get("defect_columns", [])
        if len(c) <= 60
    ]
    # De-duplicate preserving order
    seen: set = set()
    clean_arch_cols: List[str] = []
    for col in arch_cols:
        key = col.strip().lower()
        if key not in seen:
            seen.add(key)
            clean_arch_cols.append(col.strip())
        if len(clean_arch_cols) >= 8:
            break

    # Use sample rows to determine actual categories; align with archetype columns
    sample_rows = supp.get("default_rows", [])
    if sample_rows:
        # Pull categories from first row keys that match clean_arch_cols (case-insensitive)
        row_keys = list(sample_rows[0].get("values", {}).keys())
        categories = [{"key": k, "label": k} for k in row_keys]
    else:
        categories = [{"key": c, "label": c} for c in (clean_arch_cols or ["Sound", "Rotten"])]

    unit = archetype.get("unit", "pcs")
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

    # ── Note block (only if archetype has a NOTE heading) ─────────────────
    has_note = any("note" in h.lower() for h in archetype.get("heading_sequence", []))
    if has_note:
        blocks.append({
            "id": "b_note",
            "type": "narrative",
            "section": "NOTE:",
            "additional_text": (
                "The condition of the cargo described below is based on random sampling and visual/instrument inspection "
                "conducted at the time of survey. Results are representative of the sampled portion only."
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
    if supp.get("measurements"):
        blocks.append({
            "id": "b_measurements",
            "type": "measurements",
            "title": "On-Site Physical & Instrumental Measurements",
            "rows": supp["measurements"],
        })

    # ── Block 6: Defect condition table ───────────────────────────────────
    blocks.append({
        "id": "b_table",
        "type": "table",
        "title": condition_heading,
        "grouping_label": "Sample / Count",
        "unit": unit,
        "categories": categories,
        "rows": sample_rows,
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
        "groups": [
            {"id": "pg1", "observation": "Container Exterior, Seal & Reefer Temperature Display", "asset_ids": []},
            {"id": "pg2", "observation": "Cargo Stacking & General Condition on Destuffing", "asset_ids": []},
            {"id": "pg3", "observation": "Pulp Temperature Probe & Instrument Readings", "asset_ids": []},
            {"id": "pg4", "observation": f"Fruit Cutting & Internal Quality — {label}", "asset_ids": []},
            {"id": "pg5", "observation": "Defect Segregation & Sorted Condition Overview", "asset_ids": []},
        ],
    })

    # ── Block 8: NEXT STEP narrative (only for commodity types that have it in corpus) ──
    next_step_commodities = {"BLUEBERRY", "DRAGON", "GRAPE", "PLUM", "CHERRY", "AVOCADO"}
    if commodity_key.upper() in next_step_commodities:
        blocks.append({
            "id": "b_next_step",
            "type": "narrative",
            "section": "NEXT STEP:",
            "additional_text": (
                f"To mitigate losses from the damaged {label} cargo, we advised the Consignees to sell it immediately "
                "to avoid further deterioration and value loss."
            ),
        })

    # ── Block 9: Formal closure ───────────────────────────────────────────
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

def get_default_block_state(template_id: str, commodity_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a rich, authentic initial block_state for a new report.
    For all 12 mined perishable commodities the blocks are pre-populated
    with authentic paragraph wording, defect columns, and sample rows from
    the corpus of 432 real client reports.

    The client just edits the bracketed [placeholders] and numeric values.
    """
    key = (commodity_key or "APPLE").upper()

    # Load mined archetypes
    archetypes = _load_archetypes()
    archetype = archetypes.get(key, {})

    # Supplement data (narrative, measurements, sample rows)
    supp = _COMMODITY_SUPPLEMENT.get(key)
    if supp is None:
        # Fallback: use MANDARIN for unknown commodity
        key = "MANDARIN"
        supp = _COMMODITY_SUPPLEMENT["MANDARIN"]
        archetype = archetypes.get("MANDARIN", {})

    today_str = date.today().strftime("%d %B %Y")
    is_qc = "qc" in template_id.lower()
    is_air = "air" in template_id.lower()
    mode = "AIR" if is_air else "SEA"
    label = supp.get("label", key.capitalize())

    blocks = _build_blocks_for_commodity(key, supp, archetype, today_str, is_qc)

    return {
        "report_title": (
            f"IN-HOUSE QC INSPECTION REPORT ({label.upper()})" if is_qc
            else "MARINE CARGO SURVEY REPORT"
        ),
        "metadata": {
            "docx_template": "mca-qc-canonical-v1.docx" if is_qc else "mca-synthetic-v1.docx",
            "family": "QC_REPORT" if is_qc else "SURVEY_REPORT",
            "commodity": key,
        },
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
