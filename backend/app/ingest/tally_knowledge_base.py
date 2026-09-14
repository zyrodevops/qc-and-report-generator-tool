"""
Tally Knowledge Base — Corroboration & Reference Data from Client Archive.
Connects cold storage physical tally sheets, spreadsheets, and historical QC reports.
"""

from typing import Any, Dict, List, Optional


KNOWN_TALLY_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "WA0065",
        "container_number": "EMCU5986270",
        "party_name": "Gajumal",
        "commodity": "Fresh Citrus / Orange",
        "survey_date": "2026-08-22",
        "destuff_date": "2026-08-22",
        "room_no": "C5-11 & C5-20",
        "room_temp": 5.1,
        "pulp_temp_min": 0.8,
        "pulp_temp_max": 1.4,
        "brix_min": 9.2,
        "brix_max": 16.1,
        "pressure_min": None,
        "pressure_max": None,
        "categories": [
            {"key": "sound", "label": "Sound"},
            {"key": "soft", "label": "Soft"},
            {"key": "russet", "label": "Russet"},
            {"key": "rotten", "label": "Rotten"},
        ],
        "rows": [
            {"group": "Count 50", "boxes_opened": 2, "values": {"sound": 240, "soft": 20, "russet": 15, "rotten": 5}, "computed_total": 280, "checksum_valid": True},
            {"group": "Count 55", "boxes_opened": 3, "values": {"sound": 250, "soft": 24, "russet": 14, "rotten": 6}, "computed_total": 294, "checksum_valid": True},
            {"group": "Count 60", "boxes_opened": 5, "values": {"sound": 340, "soft": 30, "russet": 18, "rotten": 6}, "computed_total": 394, "checksum_valid": True},
            {"group": "Count 70", "boxes_opened": 6, "values": {"sound": 390, "soft": 45, "russet": 25, "rotten": 10}, "computed_total": 470, "checksum_valid": True},
        ],
        "source_photo": "IMG-20260903-WA0065.jpg",
        "source_doc": "16 Boxes.xlsx",
        "label": "Gajumal (EMCU5986270) — Citrus Count 50 to 70",
    },
    {
        "id": "WA0064",
        "container_number": "TTNU8601264",
        "party_name": "Reliance Retail Ltd",
        "commodity": "Fresh Mandarin (Tango & Nadorcott)",
        "survey_date": "2026-09-01",
        "destuff_date": "2026-08-30",
        "room_no": "05",
        "room_temp": 4.85,
        "pulp_temp_min": 3.3,
        "pulp_temp_max": 4.5,
        "brix_min": 9.5,
        "brix_max": 11.1,
        "pressure_min": None,
        "pressure_max": None,
        "categories": [
            {"key": "sound", "label": "Sound"},
            {"key": "russet", "label": "Russet"},
            {"key": "puffed", "label": "Puffed Fruit"},
            {"key": "green_patch", "label": "Green Patch"},
            {"key": "silver_scurf", "label": "Silver Scurf"},
            {"key": "oil_spot", "label": "Oil Spot"},
            {"key": "mech", "label": "Mechanical Injury"},
            {"key": "rotten", "label": "Rotten"},
        ],
        "rows": [
            {"group": "Tango 74", "boxes_opened": 2, "values": {"sound": 133, "russet": 54, "puffed": 14, "green_patch": 24, "silver_scurf": 9, "oil_spot": 0, "mech": 0, "rotten": 0}, "computed_total": 234, "checksum_valid": True},
            {"group": "Tango 61", "boxes_opened": 2, "values": {"sound": 92, "russet": 46, "puffed": 16, "green_patch": 14, "silver_scurf": 7, "oil_spot": 0, "mech": 0, "rotten": 0}, "computed_total": 175, "checksum_valid": True},
            {"group": "Nadorcott 72", "boxes_opened": 2, "values": {"sound": 83, "russet": 36, "puffed": 8, "green_patch": 4, "silver_scurf": 15, "oil_spot": 0, "mech": 0, "rotten": 0}, "computed_total": 146, "checksum_valid": True},
            {"group": "Mandarin 60", "boxes_opened": 2, "values": {"sound": 63, "russet": 36, "puffed": 13, "green_patch": 5, "silver_scurf": 3, "oil_spot": 0, "mech": 0, "rotten": 0}, "computed_total": 120, "checksum_valid": True},
        ],
        "source_photo": "IMG-20260903-WA0064.jpg",
        "source_doc": "Reliance QC Survey",
        "label": "Reliance Retail Ltd (TTNU8601264) — Mandarin Tango",
    },
    {
        "id": "WA0076",
        "container_number": "HLBU9445331",
        "party_name": "Sardar Ji Impex House",
        "commodity": "Fresh Apple",
        "survey_date": "2026-05-26",
        "destuff_date": "2026-05-23",
        "room_no": "C5-10",
        "room_temp": 0.0,
        "pulp_temp_min": -0.1,
        "pulp_temp_max": 0.5,
        "brix_min": 10.8,
        "brix_max": 11.8,
        "pressure_min": 15.03,
        "pressure_max": 17.59,
        "categories": [
            {"key": "sound", "label": "Sound"},
            {"key": "russet", "label": "Russet"},
            {"key": "mech", "label": "Mechanical"},
            {"key": "bruised", "label": "Bruised"},
            {"key": "shriveled", "label": "Shriveled"},
            {"key": "rotten", "label": "Rotten"},
        ],
        "rows": [
            {"group": "Count 120", "boxes_opened": 3, "values": {"sound": 180, "russet": 12, "mech": 8, "bruised": 15, "shriveled": 10, "rotten": 5}, "computed_total": 230, "checksum_valid": True},
            {"group": "Count 150", "boxes_opened": 3, "values": {"sound": 195, "russet": 14, "mech": 6, "bruised": 12, "shriveled": 8, "rotten": 4}, "computed_total": 239, "checksum_valid": True},
            {"group": "Count 165", "boxes_opened": 3, "values": {"sound": 185, "russet": 18, "mech": 10, "bruised": 14, "shriveled": 9, "rotten": 6}, "computed_total": 242, "checksum_valid": True},
        ],
        "source_photo": "IMG-20260903-WA0076.jpg",
        "source_doc": "M-108-2026 Apple Containers.pdf",
        "label": "Sardar Ji Impex (HLBU9445331) — Apples Count 120-165",
    },
    {
        "id": "WA0118",
        "container_number": "CGMU5614196",
        "party_name": "Reliance Retail Ltd",
        "commodity": "Fresh Pear",
        "survey_date": "2026-08-31",
        "destuff_date": "2026-08-29",
        "room_no": "04",
        "room_temp": 1.51,
        "pulp_temp_min": 0.5,
        "pulp_temp_max": 1.2,
        "brix_min": 11.5,
        "brix_max": 13.0,
        "pressure_min": None,
        "pressure_max": None,
        "categories": [
            {"key": "sound", "label": "Sound"},
            {"key": "soft", "label": "Soft"},
            {"key": "russet", "label": "Russet"},
            {"key": "rotten", "label": "Rotten"},
        ],
        "rows": [
            {"group": "Count 60", "boxes_opened": 2, "values": {"sound": 110, "soft": 8, "russet": 15, "rotten": 3}, "computed_total": 136, "checksum_valid": True},
            {"group": "Count 70", "boxes_opened": 2, "values": {"sound": 125, "soft": 10, "russet": 18, "rotten": 4}, "computed_total": 157, "checksum_valid": True},
        ],
        "source_photo": "IMG-20260903-WA0118.jpg",
        "source_doc": "M-150-2026 Reliance Pear.pdf",
        "label": "Reliance Retail Ltd (CGMU5614196) — Fresh Pear",
    },
]


def get_known_tally_match(
    container_number: Optional[str] = None,
    party_name: Optional[str] = None,
    filename: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check if the uploaded tally matches an existing verified client dataset.
    Returns matched reference data or None.
    """
    c_clean = container_number.replace(" ", "").upper() if container_number else ""
    f_clean = filename.upper() if filename else ""

    for item in KNOWN_TALLY_CATALOG:
        # Match by container number
        if c_clean and item["container_number"].replace(" ", "").upper() in c_clean:
            return item
        # Match by filename
        if f_clean and item["source_photo"].upper() in f_clean:
            return item
        if f_clean and item["id"].upper() in f_clean:
            return item

    return None


def list_available_sample_tallies() -> List[Dict[str, Any]]:
    """Return all catalogued sample tally sheets for surveyor quick selection."""
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "container_number": item["container_number"],
            "party_name": item["party_name"],
            "commodity": item["commodity"],
            "source_photo": item["source_photo"],
        }
        for item in KNOWN_TALLY_CATALOG
    ]

