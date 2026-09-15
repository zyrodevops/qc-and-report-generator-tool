"""
Clause Library API — surfaces frequently-used narrative paragraphs from the
perishable-fruit corpus so surveyors can pick and lightly edit rather than type.

Endpoint: GET /api/clauses?commodity=APPLE&section=circumstances_of_loss

Section slugs accepted:
    circumstances_of_loss | cause_of_loss | survey_findings | next_step | documentation | general

100 % offline — data comes from sentence_frequency.csv + template_archetypes.json.
"""

import csv
import json
import pathlib
import re
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# File paths  (same two-path fallback pattern as commodities.py)
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # backend/app/api → repo root
_FREQ_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "sentence_frequency.csv"
_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "template_archetypes.json"
_FALLBACK_ARCHETYPES = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "template_archetypes.json"

# ---------------------------------------------------------------------------
# Section classification — keyword groups map sentence text → section slug
# Each tuple: (required_keywords_any, exclude_keywords)
# A sentence is assigned to the FIRST section whose any-keyword matches AND
# none of its exclude-keywords match.
# ---------------------------------------------------------------------------
_SECTION_RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "next_step",
        ["next step", "we advised the consignee", "to mitigate losses", "sell them immediately",
         "sell it immediately", "notice of claim", "best realisable", "best realizable"],
        [],
    ),
    (
        "circumstances_of_loss",
        ["hence, we were contact", "were apprised", "container was shift", "cfs",
         "customs formalities", "detention charges", "were contacted and requested",
         "forwarded for survey", "cargo was transfer", "container was discharg",
         "inland container", "dwell time"],
        ["cause", "deteriorat"],
    ),
    (
        "cause_of_loss",
        ["cause of loss", "mechanical injury", "pressure damage", "bruising",
         "temperature excursion", "no variation in temperature",
         "pre-harvest", "cold chain", "skin disorder", "over-ripen",
         "senesc", "physiolog", "breakdown", "improper harvest",
         "contributing factors"],
        [],
    ),
    (
        "survey_findings",
        ["pulp temperature", "brix", "firmness", "penetrometer",
         "were opened for", "cartons were open", "randomly selected",
         "digital thermometer", "condition found", "our survey:",
         "consignee's representative", "on-site", "at site",
         "sugar brix", "digital penetro"],
        [],
    ),
    (
        "documentation",
        ["enclosure", "annexure", "reference of the recorder",
         "reference to the recorder", "transport document",
         "documentary evidence", "temperature recorder"],
        [],
    ),
]

# Commodity-name substitution words for "generic" sentences that mention
# a specific fruit — we keep them but note they contain a fruit name.
_COMMODITY_NOUNS: dict[str, list[str]] = {
    "APPLE": ["apple"],
    "APRICOT": ["apricot"],
    "AVOCADO": ["avocado"],
    "BLUEBERRY": ["blueberry", "blueberries"],
    "CHERRY": ["cherry", "cherries"],
    "DRAGON": ["dragon fruit", "dragon"],
    "GRAPE": ["grape", "grapes"],
    "KIWI": ["kiwi", "kiwis"],
    "MANDARIN": ["mandarin", "mandarins"],
    "ORANGE": ["orange", "oranges"],
    "PEAR": ["pear", "pears"],
    "PLUM": ["plum", "plums"],
}


def _classify_section(text: str) -> str:
    """Return the section slug for a sentence, or 'general' if unclassified."""
    low = text.lower()
    for slug, includes, excludes in _SECTION_RULES:
        if any(kw in low for kw in includes):
            if not any(ex in low for ex in excludes):
                return slug
    return "general"


def _commodity_match(text: str, commodity: str) -> bool:
    """Return True if sentence mentions the commodity OR is fully generic (no fruit noun)."""
    low = text.lower()
    target_words = _COMMODITY_NOUNS.get(commodity.upper(), [])
    # Collect all fruit words across all commodities
    all_fruit_words = [w for words in _COMMODITY_NOUNS.values() for w in words]

    # Sentence is generic if it doesn't mention any fruit word
    mentions_any_fruit = any(fw in low for fw in all_fruit_words)
    if not mentions_any_fruit:
        return True  # generic — valid for any commodity

    # Sentence mentions this commodity → include
    return any(tw in low for tw in target_words)


def _placeholder_to_editable(text: str) -> str:
    """
    Convert anonymised corpus placeholders to user-friendly edit markers.
    {CONTAINER} → [CONTAINER NO.]
    {REPORT_NO} → [REPORT NO.]
    {CURRENCY}  → [AMOUNT]
    {TEMP}      → [TEMP °C]
    {PERCENT}   → [_%]
    {N}         → [N]
    """
    replacements = [
        (r"\{CONTAINER\}", "[CONTAINER NO.]"),
        (r"\{REPORT_NO\}", "[REPORT NO.]"),
        (r"\{CURRENCY\}", "[AMOUNT]"),
        (r"\{TEMP\}", "[TEMP °C]"),
        (r"\{PERCENT\}", "[_%]"),
        (r"\{N\}", "[N]"),
    ]
    result = text
    for pattern, sub in replacements:
        result = re.sub(pattern, sub, result)
    return result


# ---------------------------------------------------------------------------
# Data loading (cached for process lifetime)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_frequency_data() -> list[dict]:
    """
    Load sentence_frequency.csv and return a list of dicts:
    [{text, count, section, is_template}] sorted by count desc.
    """
    rows: list[dict] = []
    if not _FREQ_FILE.exists():
        return rows

    with open(_FREQ_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            count = int(row.get("count", 0))
            if count < 8:  # skip very rare sentences
                break
            text = row.get("sentence", "").strip()
            if not text:
                continue
            rows.append({
                "raw_text": text,
                "text": _placeholder_to_editable(text),
                "count": count,
                "section": _classify_section(text),
                "is_template": bool(re.search(r"\[.*?\]|\{.*?\}", _placeholder_to_editable(text))),
            })
    return rows


@lru_cache(maxsize=1)
def _load_archetypes() -> dict:
    for path in (_ARCHETYPES_FILE, _FALLBACK_ARCHETYPES):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@router.get("/clauses")
async def get_clauses(
    commodity: Optional[str] = Query(None, description="Commodity key, e.g. APPLE"),
    section: Optional[str] = Query(
        None,
        description="Section slug: circumstances_of_loss | cause_of_loss | "
                    "survey_findings | next_step | documentation | general",
    ),
    limit: int = Query(10, ge=1, le=30, description="Max clauses to return"),
):
    """
    Return top corpus clauses for a given commodity and/or section.

    Clauses are sourced from sentence_frequency.csv (primary) and
    template_archetypes.json (supplementary top_narrative_clauses).
    Sentences are filtered to match the commodity (or generic sentences
    that don't mention any specific fruit) and classified by section.
    """
    commodity_key = (commodity or "").upper().strip() or None
    section_slug = (section or "").lower().strip() or None

    all_rows = _load_frequency_data()
    archetypes = _load_archetypes()

    # --- Filter by commodity ---
    if commodity_key:
        rows = [r for r in all_rows if _commodity_match(r["raw_text"], commodity_key)]
    else:
        rows = list(all_rows)

    # --- Filter by section ---
    if section_slug and section_slug != "general":
        # Primary: exact section match
        matched = [r for r in rows if r["section"] == section_slug]
        # Supplement with "general" sentences if we have too few
        if len(matched) < 4:
            general = [r for r in rows if r["section"] == "general"]
            matched = matched + general[: max(0, 6 - len(matched))]
    else:
        matched = rows

    # Deduplicate by text
    seen: set[str] = set()
    unique: list[dict] = []
    for r in matched:
        key_txt = r["text"].lower()[:100]
        if key_txt not in seen:
            seen.add(key_txt)
            unique.append(r)

    # --- Merge archetype top_narrative_clauses as supplementary ---
    if commodity_key and commodity_key in archetypes:
        archetype_clauses = archetypes[commodity_key].get("top_narrative_clauses", [])
        for raw in archetype_clauses:
            text = _placeholder_to_editable(raw)
            k = text.lower()[:100]
            if k not in seen:
                seen.add(k)
                unique.append({
                    "raw_text": raw,
                    "text": text,
                    "count": 0,  # frequency unknown for archetype extras
                    "section": _classify_section(raw),
                    "is_template": bool(re.search(r"\[.*?\]|\{.*?\}", text)),
                })

    # Sort: known-frequency first (by count desc), then archetype extras
    unique.sort(key=lambda r: r["count"], reverse=True)

    # Return limited set
    result = unique[:limit]

    return JSONResponse(content={
        "clauses": [
            {
                "text": r["text"],
                "count": r["count"],
                "section": r["section"],
                "is_template": r["is_template"],
            }
            for r in result
        ],
        "commodity": commodity_key,
        "section": section_slug,
        "total": len(result),
    })
