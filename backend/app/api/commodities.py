"""
Commodities API — serves the mined template archetypes from the corpus mining output.
Supports both Perishable Fruits and General Cargo subcategories.
This endpoint is unauthenticated so the frontend can populate the 'New Report' modal
without requiring a prior login token (token is still needed to actually create reports).
"""

import json
import pathlib
from functools import lru_cache
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()

# Resolve archetypes files relative to the repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # backend/app/api -> repo root
_FRUITS_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "template_archetypes.json"
_FRUITS_FALLBACK_FILE = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "template_archetypes.json"

_GC_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "general_cargo_output" / "template_archetypes.json"
_GC_FALLBACK_FILE = pathlib.Path(__file__).resolve().parents[1] / "seeds" / "general_cargo_archetypes.json"

# Emoji and display-name mapping for Perishable Fruits
_FRUITS_META: dict[str, dict] = {
    "APPLE": {"emoji": "🍎", "display": "Apple", "color": "red"},
    "APRICOT": {"emoji": "🍑", "display": "Apricot", "color": "orange"},
    "AVOCADO": {"emoji": "🥑", "display": "Avocado", "color": "green"},
    "BLUEBERRY": {"emoji": "🫐", "display": "Blueberry", "color": "blue"},
    "CHERRY": {"emoji": "🍒", "display": "Cherry", "color": "red"},
    "DRAGON": {"emoji": "🐉", "display": "Dragon Fruit", "color": "pink"},
    "GRAPE": {"emoji": "🍇", "display": "Grape", "color": "purple"},
    "KIWI": {"emoji": "🥝", "display": "Kiwi", "color": "green"},
    "MANDARIN": {"emoji": "🍊", "display": "Mandarin", "color": "orange"},
    "ORANGE": {"emoji": "🍊", "display": "Orange", "color": "orange"},
    "PEAR": {"emoji": "🍐", "display": "Pear", "color": "green"},
    "PLUM": {"emoji": "🟣", "display": "Plum", "color": "purple"},
}

# Emoji and display-name mapping for General Cargo
_GC_META: dict[str, dict] = {
    "STEEL_METALS": {"emoji": "🔩", "display": "Steel & Metals", "color": "slate", "description": "Coils, pipes, plates, bars, wire rods, tinplates"},
    "MACHINERY_PARTS": {"emoji": "⚙️", "display": "Machinery & Equipment", "color": "amber", "description": "Industrial machinery, engines, bearings, pumps, transformers"},
    "AUTOMOTIVE": {"emoji": "🚗", "display": "Automotive & Parts", "color": "indigo", "description": "CKD/SKD kits, vehicle chassis, engines, automotive components"},
    "CHEMICALS_LIQUIDS": {"emoji": "🧪", "display": "Chemicals & Liquids", "color": "teal", "description": "Steel drums, plastic barrels, IBC tanks, ISO tanks, liquid bulk"},
    "PAPER_PACKAGING": {"emoji": "📦", "display": "Paper & Packaging", "color": "yellow", "description": "Paper reels, packaging kraft, cartons, pulp bales"},
    "GENERAL_CARGO": {"emoji": "🚢", "display": "General Merchandise", "color": "blue", "description": "Breakbulk cargo, bagged commodities, wooden cases, palletized cargo"},
}


@lru_cache(maxsize=1)
def _load_fruit_archetypes() -> dict:
    """Load and cache the fruits archetypes JSON from disk."""
    for path in (_FRUITS_ARCHETYPES_FILE, _FRUITS_FALLBACK_FILE):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


@lru_cache(maxsize=1)
def _load_gc_archetypes() -> dict:
    """Load and cache the general cargo archetypes JSON from disk."""
    for path in (_GC_ARCHETYPES_FILE, _GC_FALLBACK_FILE):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


@router.get("/commodities")
async def list_commodities(category: Optional[str] = Query(None, description="Filter: FRUITS | GENERAL_CARGO")):
    """
    Return all discovered commodity templates from corpus mining.
    Each entry includes: key, display name, emoji, category, report_count, unit,
    defect_columns (top 6), heading_sequence, top_narrative_clauses.
    """
    fruit_raw = _load_fruit_archetypes()
    gc_raw = _load_gc_archetypes()

    result = []

    cat_str = category if isinstance(category, str) else None
    cat_upper = cat_str.upper() if cat_str else None

    # 1. Fruits — served from FRUIT_CONFIG, generated from the corpus analysis of
    #    451 of the client's own reports. See IMPLEMENTATION-SPEC section 2.
    #
    #    Fruit is the master switch: it decides the unit, which sections render,
    #    whether a chart is produced, which measurements are offered and which
    #    tally columns appear. Transport mode is deliberately NOT here — that is a
    #    property of the shipment, taken from the uploaded transport document or
    #    chosen explicitly, never inferred from the commodity (spec section 2.0).
    if not cat_upper or cat_upper == "FRUITS":
        from app.seeds.fruit_config import FRUIT_CONFIG

        for key, cfg in sorted(
            FRUIT_CONFIG.items(), key=lambda kv: -kv[1]["reports_in_corpus"]
        ):
            legacy = fruit_raw.get(key, {})
            result.append({
                "key": key,
                "display": cfg["display"],
                "emoji": cfg["emoji"],
                "color": _FRUITS_META.get(key, {}).get("color", "gray"),
                "category": "FRUITS",
                "report_count": cfg["reports_in_corpus"],
                "unit": cfg["unit"],
                "defect_columns": cfg["defect_columns"],
                # feature flags that drive the form
                "show_condition_found": cfg["show_condition_found"],
                "show_chart": cfg["show_chart"],
                "show_penetrometer": cfg["show_penetrometer"],
                "show_brix": cfg["show_brix"],
                "air_observed_pct": cfg["air_observed_pct"],
                "heading_sequence": legacy.get("heading_sequence", []),
            })

    # 2. General Cargo
    if not cat_upper or cat_upper == "GENERAL_CARGO":
        for key, meta in _GC_META.items():
            data = gc_raw.get(key, {})
            defect_cols = data.get("defect_columns") or [
                "Sound", "Dented / Deformed", "Rusted / Oxidized", "Wet / Moisture", "Torn / Broken", "Shortage"
            ]
            result.append({
                "key": key,
                "display": meta["display"],
                "emoji": meta["emoji"],
                "color": meta["color"],
                "description": meta.get("description", ""),
                "category": "GENERAL_CARGO",
                "report_count": data.get("report_count", 0),
                "unit": data.get("unit", "pcs"),
                "defect_columns": defect_cols,
                "heading_sequence": data.get("heading_sequence") or [
                    "PARTICULARS", "ATTENDANCE", "CIRCUMSTANCES OF LOSS", "CONDITION OF CONTAINER",
                    "OUR SURVEY & CARGO FINDINGS", "DAMAGE INVENTORY & RECONCILIATION",
                    "CAUSE OF LOSS & LIABILITY", "CLAIM RESERVE / QUANTIFICATION",
                    "SALVAGE & MITIGATION", "DOCUMENTATION & ENCLOSURES", "SURVEY PHOTOGRAPHS"
                ],
                "top_narrative_clauses": data.get("top_narrative_clauses", [])[:4],
            })

    # Sort: within each category by report_count descending
    result.sort(key=lambda x: (x["category"], -x["report_count"]))

    return JSONResponse(content={"commodities": result, "total": len(result)})
