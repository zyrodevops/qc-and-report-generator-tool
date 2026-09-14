"""
Commodities API — serves the mined template archetypes from the corpus mining output.
This endpoint is unauthenticated so the frontend can populate the 'New Report' modal
without requiring a prior login token (token is still needed to actually create reports).
"""

import json
import pathlib
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

# Resolve the archetypes file relative to the repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # backend/app/api -> repo root
_ARCHETYPES_FILE = _REPO_ROOT / "tools" / "perishable_fruits_output" / "template_archetypes.json"

# Emoji and display-name mapping for the UI
_COMMODITY_META: dict[str, dict] = {
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
def _load_archetypes() -> dict:
    """Load and cache the archetypes JSON from disk."""
    if not _ARCHETYPES_FILE.exists():
        return {}
    with open(_ARCHETYPES_FILE, encoding="utf-8") as f:
        return json.load(f)


@router.get("/commodities")
async def list_commodities():
    """
    Return all discovered commodity templates from corpus mining.
    Each entry includes: key, display name, emoji, report_count, unit,
    defect_columns (top 6), heading_sequence, top_narrative_clauses.
    """
    raw = _load_archetypes()
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="Commodity archetypes file not found. Run tools/mine_corpus.py first.",
        )

    result = []
    for key, data in sorted(raw.items()):
        meta = _COMMODITY_META.get(key, {"emoji": "🌿", "display": key.capitalize(), "color": "gray"})
        # Deduplicate & clean defect columns (some are noisy long sentences from PDF noise)
        defect_cols = [
            c for c in data.get("defect_columns", [])
            if len(c) <= 60  # skip PDF noise lines masquerading as column headers
        ]
        # Keep at most 8 unique columns
        seen: set[str] = set()
        clean_cols: list[str] = []
        for col in defect_cols:
            normalised = col.strip().lower()
            if normalised not in seen:
                seen.add(normalised)
                clean_cols.append(col.strip())
            if len(clean_cols) >= 8:
                break

        result.append({
            "key": key,
            "display": meta["display"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "report_count": data.get("report_count", 0),
            "unit": data.get("unit", "pcs"),
            "defect_columns": clean_cols,
            "heading_sequence": data.get("heading_sequence", []),
            "top_narrative_clauses": data.get("top_narrative_clauses", [])[:3],
        })

    # Sort by report_count descending so popular commodities appear first
    result.sort(key=lambda x: x["report_count"], reverse=True)

    return JSONResponse(content={"commodities": result, "total": len(result)})
