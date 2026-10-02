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



@lru_cache(maxsize=1)
def _load_fruit_archetypes() -> dict:
    """Load and cache the fruits archetypes JSON from disk."""
    for path in (_FRUITS_ARCHETYPES_FILE, _FRUITS_FALLBACK_FILE):
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
        # The cargo types of the general cargo analysis. No damage columns and
        # no sample wording: a general cargo report's tables and wording are
        # chosen in the report itself, not fixed by the cargo.
        from app.seeds.general_cargo import CARGO_TYPES

        for ct in CARGO_TYPES:
            result.append({
                "key": ct["key"],
                "display": ct["display"],
                "emoji": ct["emoji"],
                "color": ct["color"],
                "description": ct["description"],
                "category": "GENERAL_CARGO",
                "report_count": 0,
                "unit": "pcs",
                "defect_columns": [],
                "heading_sequence": [],
                "top_narrative_clauses": [],
            })

    # Sort: within each category by report_count descending
    result.sort(key=lambda x: (x["category"], -x["report_count"]))

    return JSONResponse(content={"commodities": result, "total": len(result)})
