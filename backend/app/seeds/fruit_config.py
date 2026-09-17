"""
Per-fruit configuration, GENERATED from the corpus analysis.

Source: D:/marine-corpus/analysis/tally_columns_per_fruit.csv
        plus the feature coverage measured in IMPLEMENTATION-SPEC-perishable-fruits.md section 2.
Generated: 2026-09-17 by _tools/gen_fruit_config.py

Do not hand-edit. Re-run the generator instead.

Fruit is the master switch: it decides the unit, which sections appear, whether a chart
is produced, which measurements are offered, and which tally columns are presented.
Transport mode is NOT here on purpose - it is a property of the shipment, taken from the
uploaded transport document or chosen explicitly, never inferred from the commodity.
"""

from typing import Any, Dict, List


FRUIT_CONFIG: Dict[str, Dict[str, Any]] = {
    "APPLE": {
        "display": "Apple",
        "emoji": "🍎",
        "reports_in_corpus": 122,
        "unit": "pcs",
        "show_condition_found": True,   # 51% of this fruit's reports
        "show_chart": False,             # 9%
        "show_penetrometer": True,     # 96%
        "show_brix": True,            # 95%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Mechanical Injury",
            "Russet",
            "Bruised",
            "Less Colour",
            "Pressure",
            "Rotten Spot",
            "Soft",
            "Lenticels",
            "Shrivelled",
        ],
    },
    "GRAPES": {
        "display": "Grapes",
        "emoji": "🍇",
        "reports_in_corpus": 52,
        "unit": "kg",
        "show_condition_found": False,   # 0% of this fruit's reports
        "show_chart": True,             # 71%
        "show_penetrometer": False,     # 0%
        "show_brix": True,            # 73%
        "air_observed_pct": 4,            # observed only - see spec 2.0
        "defect_columns": [
            "Soft",
            "Rotten",
            "Decay",
            "Blackish",
            "Sulphur White Spots",
            "Sulphur Marks",
        ],
    },
    "BLUEBERRY": {
        "display": "Blueberry",
        "emoji": "🫐",
        "reports_in_corpus": 44,
        "unit": "kg",
        "show_condition_found": True,   # 100% of this fruit's reports
        "show_chart": True,             # 97%
        "show_penetrometer": False,     # 0%
        "show_brix": False,            # 36%
        "air_observed_pct": 100,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Soft",
            "Shrinkage",
            "Shrivelled",
            "Scar",
        ],
    },
    "ORANGE": {
        "display": "Orange",
        "emoji": "🍊",
        "reports_in_corpus": 43,
        "unit": "pcs",
        "show_condition_found": False,   # 6% of this fruit's reports
        "show_chart": True,             # 86%
        "show_penetrometer": False,     # 0%
        "show_brix": True,            # 79%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Russet",
            "Pressure",
            "Mechanical Injury",
            "Rotten Spot",
            "Soft",
            "Silver Scurf",
            "Scab",
            "Chilling Injury",
            "Pitting Marks",
        ],
    },
    "PEAR": {
        "display": "Pear",
        "emoji": "🍐",
        "reports_in_corpus": 37,
        "unit": "pcs",
        "show_condition_found": True,   # 78% of this fruit's reports
        "show_chart": False,             # 0%
        "show_penetrometer": True,     # 100%
        "show_brix": True,            # 83%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Mechanical Injury",
            "Russet",
            "Rotten",
            "Yellowish",
            "Pressure",
            "Shrivelled",
            "Rotten Spot",
            "Quantity",
            "Soft",
            "Yellow",
        ],
    },
    "KIWI": {
        "display": "Kiwi",
        "emoji": "🥝",
        "reports_in_corpus": 34,
        "unit": "pcs",
        "show_condition_found": True,   # 82% of this fruit's reports
        "show_chart": False,             # 0%
        "show_penetrometer": True,     # 100%
        "show_brix": True,            # 91%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Soft",
            "Pressure",
            "Skin Disorder",
            "Butterfly",
            "Mechanical Injury",
            "Russet",
        ],
    },
    "DRAGON": {
        "display": "Dragon Fruit",
        "emoji": "🐉",
        "reports_in_corpus": 28,
        "unit": "pcs",
        "show_condition_found": True,   # 71% of this fruit's reports
        "show_chart": True,             # 85%
        "show_penetrometer": False,     # 0%
        "show_brix": False,            # 28%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Soft",
            "White Spot",
            "Shrinkage",
            "Shrivelled",
            "Skin Russet",
        ],
    },
    "PLUM": {
        "display": "Plum",
        "emoji": "🟣",
        "reports_in_corpus": 24,
        "unit": "pcs",
        "show_condition_found": False,   # 0% of this fruit's reports
        "show_chart": False,             # 8%
        "show_penetrometer": False,     # 33%
        "show_brix": True,            # 79%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Mechanical Injury",
            "Soft",
            "Russet",
            "Shrivelled",
            "Shrinkage",
            "Crack",
            "Russet / Skin Defect",
            "Quantity",
            "Pressure",
        ],
    },
    "MANDARINS": {
        "display": "Mandarin",
        "emoji": "🍊",
        "reports_in_corpus": 24,
        "unit": "pcs",
        "show_condition_found": False,   # 0% of this fruit's reports
        "show_chart": True,             # 91%
        "show_penetrometer": False,     # 0%
        "show_brix": True,            # 100%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Russet",
            "Green Patch",
            "Soft",
            "Mechanical Injury",
            "Rotten Spot",
            "Silver Scurf",
            "Pitting Marks",
            "Soft / Pressed",
            "Russet / Skin Defects",
        ],
    },
    "CHERRY": {
        "display": "Cherry",
        "emoji": "🍒",
        "reports_in_corpus": 18,
        "unit": "kg",
        "show_condition_found": True,   # 66% of this fruit's reports
        "show_chart": True,             # 72%
        "show_penetrometer": False,     # 0%
        "show_brix": True,            # 88%
        "air_observed_pct": 56,            # observed only - see spec 2.0
        "defect_columns": [
            "Soft",
            "Pitting Marks",
            "Rotten",
            "Cracked",
            "Crack",
        ],
    },
    "AVOCADO": {
        "display": "Avocado",
        "emoji": "🥑",
        "reports_in_corpus": 10,
        "unit": "pcs",
        "show_condition_found": False,   # 0% of this fruit's reports
        "show_chart": False,             # 30%
        "show_penetrometer": True,     # 50%
        "show_brix": False,            # 0%
        "air_observed_pct": 0,            # observed only - see spec 2.0
        "defect_columns": [
            "Rotten",
            "Soft",
            "Black Spot",
            "Pressure",
            "Browning",
        ],
    },
    "APRICOT": {
        "display": "Apricot / Stone fruit",
        "emoji": "🍑",
        "reports_in_corpus": 3,
        "unit": "pcs",
        "show_condition_found": True,   # 66% of this fruit's reports
        "show_chart": False,             # 33%
        "show_penetrometer": False,     # 0%
        "show_brix": False,            # 33%
        "air_observed_pct": 100,            # observed only - see spec 2.0
        "defect_columns": [
            "Soft",
            "Rotten",
            "Pitting Marks",
        ],
    },
}


# Column spellings that mean the same thing. Normalise before matching.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "skin disorder": ['Skin Disorder', 'Skin-Disorder', 'Skin Dis-Order', 'Skin Dis- Order'],
    "butterfly": ['Butterfly', 'Butter-Fly', 'Butter Fly'],
    "mechanical injury": ['Mechanical Injury', 'Mechaniical Injury', 'Mechanical'],
    "pressure": ['Pressure', 'Pressure Damaged', 'Pressed Marks'],
    "rotten spot": ['Rotten Spot', 'Rotten Spots'],
    "white spot": ['White Spot', 'White Spots'],
    "black spot": ['Black Spot', 'Black Spots'],
    "shrivelled": ['Shrivelled', 'Shriveled', 'Shrivel'],
    "less colour": ['Less Colour', 'Less Color', 'Low Colour'],
    "pitting marks": ['Pitting Marks', 'Pitting', 'Pitting Mark'],
}


def normalise_column(name: str) -> str:
    """Map any spelling of a tally column onto its canonical key."""
    key = " ".join(name.lower().replace("-", " ").replace("_", " ").split())
    for canonical, variants in COLUMN_ALIASES.items():
        if key == canonical or key in [
            " ".join(v.lower().replace("-", " ").split()) for v in variants
        ]:
            return canonical
    return key


def get_fruit(name: str) -> Dict[str, Any]:
    """Look up a fruit config, case-insensitively. Raises KeyError if unknown."""
    return FRUIT_CONFIG[name.strip().upper()]
