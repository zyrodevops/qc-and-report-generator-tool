"""
Fruit-driven tally columns.

The grid a surveyor fills in at the cold room is not a fixed shape. The defect
columns are whatever that fruit is graded on: apple is scored on russet,
lenticels and bruising; mandarin on puffed fruit, green patch and silver scurf.
Offering one hardcoded set of columns for every commodity forces the surveyor to
hand-map his sheet onto the wrong grid, and anything he cannot map gets dropped.

Columns therefore come from FRUIT_CONFIG, which was generated from the client's
own archive, plus two fixed ones that every sheet has:

  Sound   the count fit for sale, always the first data column
  Total   the figure the surveyor WROTE on the sheet

The stated total is deliberately kept out of the category list and held on the
row instead, because it is evidence rather than a data column. It is the only
thing that makes the row check meaningful: if the app derived the total from the
same cells it just read, the check would compare a number with itself and could
never fail. Comparing what was read against what was written is what catches a
misread digit.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.seeds.fruit_config import FRUIT_CONFIG, normalise_column

# Always the first data column, for every commodity.
SOUND_COLUMN: Dict[str, str] = {"key": "sound", "label": "Sound", "role": "sound"}

# Words that mark the written-total column rather than a defect column.
_TOTAL_WORDS = ("total", "tot", "sum", "grand total")

# Words that mark the row-label column (count / size / caliber).
_LABEL_WORDS = ("count", "size", "caliber", "calibre", "grade", "group", "item", "sr", "sr.no", "srno")


def slug(name: str) -> str:
    """Stable JSON key for a column label, after alias normalisation."""
    return re.sub(r"[^a-z0-9]+", "_", normalise_column(name)).strip("_")


# The generated config keys some fruits plural and the rest of the application
# keys them singular: FRUIT_CONFIG has GRAPES and MANDARINS, while the report
# defaults, the commodity dropdown and the seeded block state all say GRAPE and
# MANDARIN. The lookup missed, so a grape report offered one column — Sound —
# and the surveyor had nowhere to put a soft or rotten count.
_FRUIT_ALIASES: Dict[str, str] = {
    "GRAPE": "GRAPES",
    "MANDARIN": "MANDARINS",
    "TABLE GRAPES": "GRAPES",
    "BLUEBERRIES": "BLUEBERRY",
    "CHERRIES": "CHERRY",
    "APPLES": "APPLE",
    "PEARS": "PEAR",
    "ORANGES": "ORANGE",
    "PLUMS": "PLUM",
    "KIWIS": "KIWI",
    "AVOCADOS": "AVOCADO",
    "APRICOTS": "APRICOT",
    "DRAGON FRUIT": "DRAGON",
}


def lookup_fruit(commodity: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Case-insensitive FRUIT_CONFIG lookup that returns None instead of raising.

    Tries the name as given, then its alias, then the plural and singular forms,
    so a caller does not have to know which spelling the generated config used.
    """
    if not commodity:
        return None

    key = " ".join(commodity.strip().upper().split())
    for candidate in (key, _FRUIT_ALIASES.get(key), f"{key}S", key.rstrip("S")):
        if candidate and candidate in FRUIT_CONFIG:
            return FRUIT_CONFIG[candidate]
    return None


def build_categories(commodity: Optional[str]) -> List[Dict[str, str]]:
    """
    The columns this commodity's tally grid should have.

    Returns Sound first, then that fruit's defect columns in corpus order. When
    the commodity is unknown, returns Sound alone: the remaining columns are then
    taken from whatever headers the sheet itself carries, rather than inventing a
    set the surveyor never uses.
    """
    categories: List[Dict[str, str]] = [dict(SOUND_COLUMN)]
    fruit = lookup_fruit(commodity)
    if not fruit:
        return categories

    for label in fruit.get("defect_columns", []):
        key = slug(label)
        if not key or any(c["key"] == key for c in categories):
            continue
        categories.append({"key": key, "label": label, "role": "defect"})
    return categories


def unit_for(commodity: Optional[str]) -> str:
    """'pcs' or 'kg' — how this fruit is counted. Defaults to pieces."""
    fruit = lookup_fruit(commodity)
    return str(fruit.get("unit", "pcs")) if fruit else "pcs"


def is_total_header(raw_header: str) -> bool:
    """True when a header cell names the written-total column."""
    clean = " ".join(raw_header.lower().replace(".", " ").split())
    return any(w == clean or w in clean.split() for w in _TOTAL_WORDS)


def is_label_header(raw_header: str) -> bool:
    """True when a header cell names the count/size column, not a data column."""
    clean = " ".join(raw_header.lower().replace(".", " ").split())
    return any(w in clean for w in _LABEL_WORDS)


# Words that decorate a column heading without changing what it counts. A
# spreadsheet from a cold store writes 'Soft Grapes (2.264 Kg)' where the sheet
# in the notebook just says 'Soft'.
_NOISE_WORDS = {
    "pcs", "pieces", "piece", "nos", "no", "kg", "kgs", "kilo", "kilos",
    "qty", "quantity", "count", "counts", "total", "weight", "wt", "pulp",
    "fruit", "fruits", "grapes", "grape", "apple", "apples", "pear", "pears",
    "kiwi", "kiwis", "orange", "oranges", "mandarin", "mandarins", "cherry",
    "cherries", "plum", "plums", "avocado", "avocados", "blueberry",
    "blueberries", "berries", "berry", "apricot", "apricots", "peach",
    "peaches", "nectarine", "nectarines", "dragon",
}


def _tokens(raw: str) -> List[str]:
    """
    A heading reduced to the words that say what it counts.

    Strips anything parenthesised — '(Pcs)', '(2.264 Kg)' — then drops digits,
    punctuation and the packaging and commodity words that carry no meaning for
    matching. 'Soft Grapes (2.264 Kg)' becomes ['soft'].
    """
    without_parens = re.sub(r"\([^)]*\)", " ", raw)
    letters_only = re.sub(r"[^a-zA-Z\s]", " ", without_parens)
    return [
        w for w in letters_only.lower().split()
        if w and w not in _NOISE_WORDS and len(w) > 1
    ]


def match_header_to_category(
    raw_header: str,
    categories: List[Dict[str, str]],
) -> Optional[str]:
    """
    Match a heading, from a sheet or a spreadsheet, to one of this fruit's columns.

    Tried in descending order of confidence: the canonical key outright, then
    the meaningful words of the heading against the meaningful words of a column,
    then a containment check strict enough that a stray word cannot land
    somewhere by accident.

    Returns None when nothing fits, which is the useful answer — the caller puts
    the column in front of the surveyor instead of guessing, and guessing here
    means someone's rotten count lands under bruised.
    """
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", re.sub(r"\([^)]*\)", " ", raw_header)).strip()
    if not cleaned:
        return None

    key = slug(cleaned)
    for cat in categories:
        if cat["key"] == key:
            return cat["key"]

    header_tokens = set(_tokens(raw_header))
    if not header_tokens:
        return None

    # A column whose own words are all present in the heading. 'Soft' matches
    # 'Soft Grapes'; 'Mechanical Injury' matches 'Mech Injury (Pcs)' only if
    # both its words survive, which they do not, so that falls to the next test.
    best: Optional[str] = None
    best_len = 0
    for cat in categories:
        cat_tokens = set(_tokens(cat["label"]))
        if cat_tokens and cat_tokens <= header_tokens and len(cat_tokens) > best_len:
            best, best_len = cat["key"], len(cat_tokens)
    if best:
        return best

    # Word-by-word, allowing each word to be shortened: 'Mech Injury' against
    # 'Mechanical Injury'. Every word of the column must be accounted for, and
    # an abbreviation must be at least four characters, so 'Ro' cannot reach
    # 'Rotten' and land a rot count in the wrong place.
    for cat in categories:
        cat_tokens = _tokens(cat["label"])
        if not cat_tokens:
            continue
        if all(
            any(
                h == c or (len(h) >= 4 and c.startswith(h)) or (len(c) >= 4 and h.startswith(c))
                for h in header_tokens
            )
            for c in cat_tokens
        ):
            return cat["key"]

    # Last: an abbreviation or extension of a single-word column. Four
    # characters minimum, for the same reason.
    if len(key) >= 4:
        for cat in categories:
            if key in cat["key"] or cat["key"] in key:
                return cat["key"]
    return None
