"""
Authentic Report Defaults and Commodity Presets.
Mined from the 241-report client archive (CRITICAL-RULES §8 compliant - synthetic identifiers).
"""

from typing import Any, Dict, List, Optional
from datetime import date


COMMODITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "mandarin": {
        "label": "Fresh Mandarin",
        "unit": "pcs",
        "categories": [
            {"key": "sound", "label": "Sound (Pcs)"},
            {"key": "soft", "label": "Soft (Pcs)"},
            {"key": "russet", "label": "Russet (Pcs)"},
            {"key": "mechanical_injury", "label": "Mechanical Injury (Pcs)"},
            {"key": "rotten", "label": "Rotten (Pcs)"},
        ],
        "default_rows": [
            {"group": "Count 55 (2 Boxes)", "values": {"sound": "133", "soft": "54", "russet": "14", "mechanical_injury": "24", "rotten": "9"}},
            {"group": "Count 60 (2 Boxes)", "values": {"sound": "92", "soft": "46", "russet": "16", "mechanical_injury": "14", "rotten": "7"}},
            {"group": "Count 65 (2 Boxes)", "values": {"sound": "83", "soft": "36", "russet": "8", "mechanical_injury": "4", "rotten": "15"}},
            {"group": "Count 70 (2 Boxes)", "values": {"sound": "63", "soft": "36", "russet": "13", "mechanical_injury": "5", "rotten": "3"}},
        ],
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "4.0", "max": "4.6", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "10.00", "max": "12.00", "unit": "%"},
            {"subject": "Internal Flesh Quality", "method": "Cutting Inspection", "min": "Soft & Juicy", "max": "", "unit": "-"},
        ],
        "narrative_sections": {
            "SUMMARY": (
                "Total of 8 cartons under 4 counts were randomly selected from different locations from the "
                "Container and was opened for our detailed QC-Inspection, when we found the mandarin fruits "
                "inside the cartons with mixture of sound, soft, russet, mechanical injury, and in a rotten "
                "condition in various extend. (See Photos 1 to 11)"
            ),
            "THERMAL_AND_INTERNAL": (
                "The pulp temperature of the fresh mandarin fruits was checked by means of a digital probe "
                "thermometer inside the cold room and was found in the range of 4.0°C to 4.6°C. (See Photos 12 & 13)\n\n"
                "• Upon cutting the Mandarin fruits, the pulp was found soft and juicy. (See Photos 14 to 16)\n"
                "• Brix was checked and was found in the range of 10.00% to 12.00%. (See Photos 17 & 18)\n\n"
                "Based on QC-Inspection findings, upon segregation of mandarin fruits from the 8 cardboard boxes "
                "under 4 counts, we can conclude that the Mandarin fruits were found with the following defects: (See Photos 19 to 110)"
            ),
        },
    },
    "orange": {
        "label": "Fresh Orange",
        "unit": "pcs",
        "categories": [
            {"key": "sound", "label": "Sound (Pcs)"},
            {"key": "soft", "label": "Soft (Pcs)"},
            {"key": "green_patch", "label": "Green Patch (Pcs)"},
            {"key": "mechanical_injury", "label": "Mechanical Injury (Pcs)"},
            {"key": "rotten", "label": "Rotten (Pcs)"},
        ],
        "default_rows": [
            {"group": "Count 72 (2 Boxes)", "values": {"sound": "102", "soft": "28", "green_patch": "12", "mechanical_injury": "8", "rotten": "4"}},
            {"group": "Count 80 (2 Boxes)", "values": {"sound": "98", "soft": "32", "green_patch": "16", "mechanical_injury": "10", "rotten": "4"}},
            {"group": "Count 88 (2 Boxes)", "values": {"sound": "94", "soft": "38", "green_patch": "22", "mechanical_injury": "14", "rotten": "8"}},
            {"group": "Count 100 (2 Boxes)", "values": {"sound": "84", "soft": "44", "green_patch": "28", "mechanical_injury": "18", "rotten": "10"}},
        ],
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "4.2", "max": "5.1", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "10.50", "max": "11.80", "unit": "%"},
            {"subject": "Pulp Condition", "method": "Cutting Inspection", "min": "Firm & Juicy", "max": "", "unit": "-"},
        ],
        "narrative_sections": {
            "SUMMARY": (
                "Total of 8 cartons under 4 counts were randomly selected across different pallet tiers of the Container "
                "and was opened for detailed QC inspection. The orange fruits inside the cartons exhibited sound condition "
                "with isolated instances of green patch, softness, and superficial mechanical injury. (See Photos 1 to 10)"
            ),
            "THERMAL_AND_INTERNAL": (
                "Pulp temperature of fresh oranges was checked with a digital probe thermometer inside the cold room and "
                "recorded between 4.2°C and 5.1°C. (See Photos 11 & 12)\n\n"
                "• Upon cutting the Orange fruits, the pulp was found firm and juicy with normal internal coloration. (See Photos 13 & 14)\n"
                "• Brix was checked via digital refractometer and ranged between 10.50% and 11.80%. (See Photos 15 & 16)\n\n"
                "Based on QC-Inspection findings, segregation results from the 8 sample cartons under 4 counts are detailed below: (See Photos 17 to 85)"
            ),
        },
    },
    "grapes": {
        "label": "Fresh Table Grapes",
        "unit": "kg",
        "categories": [
            {"key": "sound", "label": "Sound (kg)"},
            {"key": "decay_rot", "label": "Decay / Rot (kg)"},
            {"key": "softness", "label": "Softness (kg)"},
            {"key": "stem_dehydration", "label": "Stem Dehydration (kg)"},
            {"key": "split_berries", "label": "Split Berries (kg)"},
            {"key": "shatter", "label": "Shatter (kg)"},
        ],
        "default_rows": [
            {"group": "Pallet 1 / Box 1-4", "values": {"sound": "18.820", "decay_rot": "0.340", "softness": "0.450", "stem_dehydration": "0.180", "split_berries": "0.120", "shatter": "0.090"}},
            {"group": "Pallet 2 / Box 5-8", "values": {"sound": "19.110", "decay_rot": "0.220", "softness": "0.310", "stem_dehydration": "0.140", "split_berries": "0.150", "shatter": "0.070"}},
            {"group": "Pallet 3 / Box 9-12", "values": {"sound": "18.650", "decay_rot": "0.410", "softness": "0.520", "stem_dehydration": "0.210", "split_berries": "0.090", "shatter": "0.120"}},
        ],
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "0.8", "max": "1.6", "unit": "°C"},
            {"subject": "Brix Content", "method": "Digital Refractometer", "min": "16.00", "max": "18.50", "unit": "%"},
            {"subject": "Berry Firmness", "method": "Penetrometer", "min": "Firm & Intact", "max": "", "unit": "-"},
        ],
        "narrative_sections": {
            "SUMMARY": (
                "Representative sample cartons were selected across pallet tiers for 100% net weight segregation and "
                "quality analysis. The table grapes were inspected for decay, stem condition, browning, and shatter. (See Photos 1 to 15)"
            ),
            "THERMAL_AND_INTERNAL": (
                "Pulp temperature of grape berries was checked across 3 pallets using a digital probe thermometer and "
                "measured between 0.8°C and 1.6°C. (See Photos 16 & 17)\n\n"
                "• Stems were predominantly green to slightly turned amber; bunch attachment was normal. (See Photos 18 to 20)\n"
                "• Soluble solids (Brix) were found in the range of 16.00% to 18.50%. (See Photos 21 & 22)\n\n"
                "Based on quality segregation, sample findings in kilograms are summarized in the table below: (See Photos 23 to 60)"
            ),
        },
    },
    "apples": {
        "label": "Fresh Apples",
        "unit": "pcs",
        "categories": [
            {"key": "sound", "label": "Sound (Pcs)"},
            {"key": "bruised", "label": "Bruised (Pcs)"},
            {"key": "mechanical_injury", "label": "Mechanical Injury (Pcs)"},
            {"key": "rotten", "label": "Rotten (Pcs)"},
            {"key": "bitter_pit", "label": "Bitter Pit / Shrinkage (Pcs)"},
        ],
        "default_rows": [
            {"group": "Count 100 (2 Boxes)", "values": {"sound": "142", "bruised": "26", "mechanical_injury": "14", "rotten": "8", "bitter_pit": "10"}},
            {"group": "Count 113 (2 Boxes)", "values": {"sound": "158", "bruised": "32", "mechanical_injury": "18", "rotten": "6", "bitter_pit": "12"}},
            {"group": "Count 125 (2 Boxes)", "values": {"sound": "172", "bruised": "38", "mechanical_injury": "20", "rotten": "8", "bitter_pit": "12"}},
        ],
        "measurements": [
            {"subject": "Pulp Temperature", "method": "Digital Probe Thermometer", "min": "1.2", "max": "2.0", "unit": "°C"},
            {"subject": "Fruit Pressure / Firmness", "method": "Penetrometer (11mm tip)", "min": "14.5", "max": "17.0", "unit": "lbs/cm²"},
            {"subject": "Starch Iodine Index", "method": "CTIFL Scale (1-8)", "min": "4.0", "max": "5.5", "unit": "Score"},
        ],
        "narrative_sections": {
            "SUMMARY": (
                "Upon opening and on checking, Apple fruits packed inside the cartons were found with mixture of "
                "sound, bruised, mechanical injured, and rotten condition at places to varying degrees. (See Photos 1 to 12)"
            ),
            "THERMAL_AND_INTERNAL": (
                "The pulp temperature of the fresh Apple fruits was checked by means of a digital probe thermometer "
                "inside the cold room and was found in the range of 1.2°C to 2.0°C. (See Photos 13 & 14)\n\n"
                "• The pressure of the randomly selected Apple fruits from the cartons was checked with a fruit pressure "
                "tester and recorded between 14.5 and 17.0 lbs/cm². (See Photos 15 & 16)\n"
                "• Upon cutting the sound apples, the pulp was found in hard & white condition; bruised fruits exhibited "
                "brownish discoloration below the epidermal layer. (See Photos 17 & 18)\n\n"
                "Based on QC-Inspection findings, defect breakdown across sample cartons is summarized below: (See Photos 19 to 90)"
            ),
        },
    },
}


def get_default_block_state(template_id: str, commodity_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a rich, authentic initial block_state for a new report.
    Pre-populates particulars, measurements, boilerplate narrative, defect tables,
    and formal closure text.
    """
    comm_key = (commodity_key or "").lower()
    if comm_key not in COMMODITY_PRESETS:
        comm_key = "mandarin"

    comm = COMMODITY_PRESETS[comm_key]
    today_str = date.today().strftime("%d %B %Y")
    is_qc = "qc" in template_id.lower()
    is_air = "air" in template_id.lower()
    mode = "AIR" if is_air else "SEA"

    if is_qc:
        return {
            "report_title": f"IN-HOUSE QC INSPECTION REPORT ({comm['label'].upper()})",
            "metadata": {
                "docx_template": "mca-qc-canonical-v1.docx",
                "family": "QC_REPORT",
            },
            "transport": {
                "mode": mode,
                "container_no": "FBIU5499689",
                "vessel": "M.V. EVER GLORY" if mode == "SEA" else "FLIGHT EK-504",
                "voyage": "V.2026S" if mode == "SEA" else "AWB 176-12345675",
                "origin": "Guangzhou, China",
                "destination": "Nhava Sheva, India" if mode == "SEA" else "Mumbai Airport, India",
            },
            "weights": {
                "manifest_kg": "28576.80",
                "gross_kg": "28576.80",
                "tare_kg": "4500.00",
                "net_kg": "24076.80",
            },
            "blocks": [
                {
                    "id": "b_particulars",
                    "type": "particulars",
                    "title": "Cargo Particulars",
                    "rows": [
                        {"label": "Exporter / Shipper", "value": ["Guangzhou Dunfu Trading Co., Ltd, China"]},
                        {"label": "Consignee", "value": ["Saanvi Fresh Fruit, Haryana, India"]},
                        {"label": "Container / Carriage Unit", "value": [f"FBIU5499689 (1x40' High Cube Reefer)"]},
                        {"label": "QC In-Charge Name", "value": ["Mr. Kishan Singh"]},
                        {"label": "Survey Date", "value": [today_str]},
                        {"label": "Inspection Location", "value": ["Prabhu Hira Ice & Cold Storage, Sector 19B, Vashi, Navi Mumbai"]},
                        {"label": "Declared Consignment", "value": [f"{comm['label']} (9 Kg Cartons) — Total: 2,916 Boxes (Net: 26,244 kg / Gross: 28,576.8 kg)"]},
                    ],
                },
                {
                    "id": "b_narrative_summary",
                    "type": "narrative",
                    "section": "SUMMARY",
                    "additional_text": comm["narrative_sections"]["SUMMARY"],
                },
                {
                    "id": "b_measurements",
                    "type": "measurements",
                    "title": "On-Site Physical & Instrumental Measurements",
                    "rows": comm["measurements"],
                },
                {
                    "id": "b_narrative_internal",
                    "type": "narrative",
                    "section": "INTERNAL QUALITY & TEMPERATURE FINDINGS",
                    "additional_text": comm["narrative_sections"]["THERMAL_AND_INTERNAL"],
                },
                {
                    "id": "b_table",
                    "type": "table",
                    "title": f"DEFECT ANALYSIS BREAKDOWN — {comm['label'].upper()}",
                    "grouping_label": "Count / Box Sample",
                    "layout": "two_tier",
                    "unit": comm["unit"],
                    "categories": comm["categories"],
                    "rows": comm["default_rows"],
                },
                {
                    "id": "b_photos",
                    "type": "photo_plate",
                    "title": "IN-HOUSE QC PHOTOGRAPHS",
                    "series_id": "survey",
                    "observation_groups": [
                        {"id": "og1", "label": "Container Exterior, Seal & Temperature Display", "asset_ids": []},
                        {"id": "og2", "label": "Pulp Temperature Probe Readings", "asset_ids": []},
                        {"id": "og3", "label": "Fruit Cutting & Brix Refractometer Inspection", "asset_ids": []},
                        {"id": "og4", "label": "Defect Segregation & Sorted Boxes", "asset_ids": []},
                    ],
                },
                {
                    "id": "b_closure",
                    "type": "fixed_text",
                    "title": "SURVEYOR SIGN-OFF & LEGAL CLOSURE",
                    "content": (
                        "QC In-Charge (Consignee): Kishan Singh\n"
                        "Signature: ______________________________\n\n"
                        "“ISSUED WITHOUT PREJUDICE”\n"
                        f"Dated: {today_str}\n"
                        "ØØØ"
                    ),
                },
            ],
        }

    # Default survey report block state
    return {
        "report_title": "MARINE CARGO SURVEY REPORT",
        "metadata": {
            "docx_template": "mca-synthetic-v1.docx",
            "family": "SURVEY_REPORT",
        },
        "transport": {
            "mode": mode,
            "container_no": "SEGU9979141",
            "vessel": "M.V. MAERSK KARACHI" if mode == "SEA" else "AIR CARGO FREIGHTER",
            "voyage": "V.102W" if mode == "SEA" else "AWB 098-98765432",
            "origin": "Valparaiso, Chile",
            "destination": "Nhava Sheva, India",
        },
        "weights": {
            "manifest_kg": "24500.00",
            "gross_kg": "24480.00",
            "tare_kg": "4320.00",
            "net_kg": "20160.00",
        },
        "blocks": [
            {
                "id": "b_parties",
                "type": "parties",
                "rows": [
                    {"role": "Instructing Principal", "name": "DP Survey Group N.V., Antwerp"},
                    {"role": "Consignee / Importer", "name": "Reliance Retail Ltd, Mumbai"},
                    {"role": "Shipper / Exporter", "name": "Sanjo Cooperativa Agricola, Brazil"},
                    {"role": "Ocean Carrier", "name": "Mediterranean Shipping Company (MSC)"},
                ],
            },
            {
                "id": "b_attendance",
                "type": "attendance",
                "attendees": [
                    {"name": "Mr. Kishan Singh", "representing": "Marine Cargo Agencies (Surveyor)"},
                    {"name": "Mr. A. K. Sharma", "representing": "Consignee Warehouse Manager"},
                    {"name": "Mr. Rajesh Patel", "representing": "Customs Clearing Agent (CHA)"},
                ],
            },
            {
                "id": "b_particulars",
                "type": "particulars",
                "rows": [
                    {"label": "Bill of Lading / AWB", "value": ["MEDUMM123456"]},
                    {"label": "Container Number", "value": ["SEGU9979141 (40' HC Reefer)"]},
                    {"label": "Seal Number", "value": ["MSCIND987654 (Found Intact)"]},
                    {"label": "Carrying Vessel", "value": ["M.V. MAERSK KARACHI V.102W"]},
                    {"label": "Port of Loading", "value": ["Santos, Brazil"]},
                    {"label": "Port of Discharge", "value": ["Nhava Sheva (JNPT), India"]},
                    {"label": "Cargo Declared", "value": ["Fresh Apples (2,100 Cartons on 20 Pallets)"]},
                ],
            },
            {
                "id": "b_timeline",
                "type": "timeline",
                "events": [
                    {"date": "2026-05-10", "event": "Vessel arrived at JNPT and berthed"},
                    {"date": "2026-05-12", "event": "Container discharged to CFS under seal"},
                    {"date": "2026-05-15", "event": "Customs out-of-charge examination held"},
                    {"date": "2026-05-16", "event": "Surveyor attended cold storage for joint devanning inspection"},
                ],
            },
            {
                "id": "b_narrative_circ",
                "type": "narrative",
                "section": "CIRCUMSTANCES OF SURVEY & SAMPLING",
                "additional_text": (
                    "We the undersigned surveyors attended at the consignee's nominated cold storage on "
                    f"{today_str} to inspect the condition of the subject consignment upon container destuffing. "
                    "The container exterior was inspected prior to door opening; no structural breach or air leakage was noted. "
                    "Customs bottle seal was verified and cut in the presence of all attending representatives."
                ),
            },
            {
                "id": "b_measurements",
                "type": "measurements",
                "rows": comm["measurements"],
            },
            {
                "id": "b_narrative_cause",
                "type": "narrative",
                "section": "SURVEY FINDINGS & CAUSE OF LOSS",
                "additional_text": (
                    "Upon opening the container doors, cargo stowage was found uniform and intact. "
                    "Pulp temperatures were verified across top, middle, and bottom tiers using a calibrated probe thermometer. "
                    "Based on data logger readouts and pulp condition, cargo was maintained within acceptable carrying parameters "
                    "throughout the ocean voyage with negligible transit deterioration."
                ),
            },
            {
                "id": "b_photos",
                "type": "photo_plate",
                "title": "SURVEY PHOTOGRAPHS",
                "series_id": "survey",
                "observation_groups": [
                    {"id": "og1", "label": "Container Exterior & Seal Verification", "asset_ids": []},
                    {"id": "og2", "label": "Door Opening & Reefer Airflow Stacking", "asset_ids": []},
                    {"id": "og3", "label": "Pulp Temperature Verification & Fruit Quality", "asset_ids": []},
                ],
            },
            {
                "id": "b_annexures",
                "type": "annexures",
                "items": [
                    {"annexure_id": "A", "label": "Bill of Lading Copy", "page_count": 1},
                    {"annexure_id": "B", "label": "Commercial Invoice & Packing List", "page_count": 2},
                    {"annexure_id": "C", "label": "Temperature Datalogger Download Record", "page_count": 3},
                ],
            },
            {
                "id": "b_closure",
                "type": "fixed_text",
                "title": "SURVEYOR CERTIFICATE & CLOSURE",
                "content": (
                    "This survey has been conducted without prejudice to liability or rights of whomsoever it may concern.\n\n"
                    "“ISSUED WITHOUT PREJUDICE”\n"
                    f"Dated: {today_str}\n"
                    "Marine Cargo Agencies Pvt. Ltd.\n"
                    "ØØØ"
                ),
            },
        ],
    }
