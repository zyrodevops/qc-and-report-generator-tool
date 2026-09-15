"""
Clause Library API — surfaces frequently-used narrative paragraphs from both
perishable-fruit and general cargo reports so surveyors can pick and lightly edit rather than type.

Endpoint: GET /api/clauses?commodity=STEEL_METALS&section=survey_findings

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
# File paths
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # backend/app/api → repo root

_FRUITS_FREQ_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "sentence_frequency.csv"
_FRUITS_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "template_archetypes.json"
_FRUITS_FALLBACK_ARCHETYPES = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "template_archetypes.json"

_GC_FREQ_FILE = _REPO_ROOT / "tools" / "general_cargo_output" / "sentence_frequency.csv"
_GC_FALLBACK_FREQ = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "general_cargo_sentences.csv"
_GC_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "general_cargo_output" / "template_archetypes.json"
_GC_FALLBACK_ARCHETYPES = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "general_cargo_archetypes.json"

# ---------------------------------------------------------------------------
# Section classification — keyword groups map sentence text → section slug
# ---------------------------------------------------------------------------
_SECTION_RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "next_step",
        [
            "next step", "we advised the consignee", "to mitigate losses", "sell them immediately",
            "sell it immediately", "notice of claim", "best realisable", "best realizable",
            "provisional reserve", "claim reserve", "salvage value", "mitigate further loss",
            "reserve of", "holding them responsible", "segregation was highly recommended"
        ],
        [],
    ),
    (
        "circumstances_of_loss",
        [
            "hence, we were contact", "were apprised", "container was shift", "cfs",
            "customs formalities", "detention charges", "were contacted and requested",
            "forwarded for survey", "cargo was transfer", "container was discharg",
            "inland container", "dwell time", "pursuant to survey instructions",
            "destuffed in the presence", "arrived at port of discharge", "original bolt seal",
            "attended at the consignee", "unstuffing"
        ],
        ["cause of loss", "cause of damage"],
    ),
    (
        "cause_of_loss",
        [
            "cause of loss", "cause of damage", "mechanical injury", "pressure damage", "bruising",
            "temperature excursion", "no variation in temperature", "pre-harvest", "cold chain",
            "rough weather", "heavy rolling and pitching", "improper stowage", "inadequate lashing",
            "handling by shore", "wire lashings", "shifting in transit", "ingress of sea water",
            "monsoon transit", "impact crease", "negligence", "attributable to", "turnbuckle"
        ],
        [],
    ),
    (
        "survey_findings",
        [
            "pulp temperature", "brix", "firmness", "penetrometer",
            "were opened for", "cartons were open", "randomly selected",
            "digital thermometer", "condition found", "our survey:", "survey findings",
            "consignee's representative", "on-site", "at site", "sugar brix",
            "silver nitrate", "chlorides", "european rust grade", "surface rust",
            "external examination", "light test", "hose test", "structural condition",
            "dunnage wood", "gaskets were inspected", "water-tight condition"
        ],
        [],
    ),
    (
        "documentation",
        [
            "enclosure", "annexure", "reference of the recorder", "reference to the recorder",
            "transport document", "documentary evidence", "temperature recorder",
            "shipping documents", "bill of lading", "commercial invoice", "packing list",
            "equipment interchange receipt", "port out-turn", "notice of loss"
        ],
        [],
    ),
]

_COMMODITY_NOUNS: dict[str, list[str]] = {
    # Fruits
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
    # General Cargo
    "STEEL_METALS": ["steel", "coil", "pipe", "tube", "plate", "billet", "iron", "metal", "tinplate"],
    "MACHINERY_PARTS": ["machine", "machinery", "crane", "motor", "engine", "pump", "bearing", "shaft", "equipment"],
    "AUTOMOTIVE": ["suzuki", "maruti", "vehicle", "chassis", "automotive", "ckd", "skd", "car"],
    "CHEMICALS_LIQUIDS": ["drum", "barrel", "ibc", "liquid", "chemical", "resin", "oil"],
    "PAPER_PACKAGING": ["paper", "pulp", "reel", "roll", "kraft", "carton"],
    "GENERAL_CARGO": ["bag", "case", "merchandise", "breakbulk", "cargo", "pallet"],
}

_GC_KEYS = {"STEEL_METALS", "MACHINERY_PARTS", "AUTOMOTIVE", "CHEMICALS_LIQUIDS", "PAPER_PACKAGING", "GENERAL_CARGO"}


def _classify_section(text: str) -> str:
    low = text.lower()
    for slug, includes, excludes in _SECTION_RULES:
        if any(kw in low for kw in includes):
            if not any(ex in low for ex in excludes):
                return slug
    return "general"


def _commodity_match(text: str, commodity: str) -> bool:
    low = text.lower()
    target_words = _COMMODITY_NOUNS.get(commodity.upper(), [])
    all_fruit_words = [w for k, words in _COMMODITY_NOUNS.items() if k not in _GC_KEYS for w in words]
    all_gc_words = [w for k, words in _COMMODITY_NOUNS.items() if k in _GC_KEYS for w in words]

    is_gc = commodity.upper() in _GC_KEYS

    if is_gc:
        # Don't match fruit sentences for general cargo
        if any(fw in low for fw in all_fruit_words):
            return False
        # If it matches specific GC words
        if target_words and any(tw in low for tw in target_words):
            return True
        # Generic GC sentence (mentions general logistics / maritime terms)
        return True
    else:
        # Perishable fruit logic
        mentions_any_fruit = any(fw in low for fw in all_fruit_words)
        if not mentions_any_fruit:
            return True
        return any(tw in low for tw in target_words)


def _placeholder_to_editable(text: str) -> str:
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


@lru_cache(maxsize=1)
def _load_frequency_data() -> list[dict]:
    rows: list[dict] = []
    seen = set()

    # 1. Perishable fruits sentences
    if _FRUITS_FREQ_FILE.exists():
        with open(_FRUITS_FREQ_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cnt = int(row.get("count", 0))
                if cnt < 8:
                    break
                txt = row.get("sentence", "").strip()
                if txt and txt not in seen:
                    seen.add(txt)
                    rows.append({
                        "raw_text": txt,
                        "text": _placeholder_to_editable(txt),
                        "count": cnt,
                        "section": _classify_section(txt),
                        "is_template": bool(re.search(r"\[.*?\]|\{.*?\}", _placeholder_to_editable(txt))),
                        "is_gc": False,
                    })

    # 2. General cargo sentences
    gc_file = _GC_FREQ_FILE if _GC_FREQ_FILE.exists() else _GC_FALLBACK_FREQ
    if gc_file.exists():
        with open(gc_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cnt = int(row.get("count", 0))
                if cnt < 3:
                    break
                txt = row.get("sentence", "").strip()
                if txt and txt not in seen:
                    seen.add(txt)
                    rows.append({
                        "raw_text": txt,
                        "text": _placeholder_to_editable(txt),
                        "count": cnt,
                        "section": _classify_section(txt),
                        "is_template": bool(re.search(r"\[.*?\]|\{.*?\}", _placeholder_to_editable(txt))),
                        "is_gc": True,
                    })

    return rows


@lru_cache(maxsize=1)
def _load_archetypes() -> dict:
    merged = {}
    for path in (_FRUITS_ARCHETYPES_FILE, _FRUITS_FALLBACK_ARCHETYPES):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                merged.update(json.load(f))
            break
    for path in (_GC_ARCHETYPES_FILE, _GC_FALLBACK_ARCHETYPES):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                merged.update(json.load(f))
            break
    return merged


@router.get("/clauses")
async def get_clauses(
    commodity: Optional[str] = Query(None, description="Commodity key, e.g. APPLE, STEEL_METALS"),
    section: Optional[str] = Query(
        None,
        description="Section slug: circumstances_of_loss | cause_of_loss | "
                    "survey_findings | next_step | documentation | general",
    ),
    limit: int = Query(10, ge=1, le=30, description="Max clauses to return"),
):
    """
    Return top corpus clauses for a given commodity and/or section.
    Supports both Perishable Fruits and General Cargo commodities.
    """
    commodity_key = commodity.upper().strip() if isinstance(commodity, str) and commodity.strip() else None
    section_slug = section.lower().strip() if isinstance(section, str) and section.strip() else None
    lim = limit if isinstance(limit, int) else 10
    is_gc = commodity_key in _GC_KEYS if commodity_key else False

    all_rows = _load_frequency_data()
    archetypes = _load_archetypes()

    # Filter by commodity / cargo family
    if commodity_key:
        rows = [r for r in all_rows if _commodity_match(r["raw_text"], commodity_key)]
    else:
        rows = list(all_rows)

    # Filter by section
    if section_slug and section_slug != "general":
        matched = [r for r in rows if r["section"] == section_slug]
        if len(matched) < 4:
            general = [r for r in rows if r["section"] == "general"]
            matched = matched + general[: max(0, 6 - len(matched))]
    else:
        matched = rows

    seen_text = set()
    unique: list[dict] = []
    for r in matched:
        k = r["text"].lower()[:100]
        if k not in seen_text:
            seen_text.add(k)
            unique.append(r)

    # Supplement with archetype top_narrative_clauses
    if commodity_key and commodity_key in archetypes:
        archetype_clauses = archetypes[commodity_key].get("top_narrative_clauses", [])
        for raw in archetype_clauses:
            text = _placeholder_to_editable(raw)
            k = text.lower()[:100]
            if k not in seen_text:
                seen_text.add(k)
                unique.append({
                    "raw_text": raw,
                    "text": text,
                    "count": 0,
                    "section": _classify_section(raw),
                    "is_template": bool(re.search(r"\[.*?\]|\{.*?\}", text)),
                    "is_gc": is_gc,
                })

    unique.sort(key=lambda r: r["count"], reverse=True)
    result = unique[:lim]

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
