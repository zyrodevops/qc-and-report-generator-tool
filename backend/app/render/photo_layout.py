"""
How the survey photographs are laid out in the report.

The client builds his photo pages with his own Auto-on-render tool (Pro mode),
and the layout here is that tool's, measured against his reports: in 60 of his
perishable reports, 50 carry 8 photos to an A4 page and 10 carry 6; the photos
are 8.2 x 5.6 cm (the tool's 310 x 210 px), two across with no gap, no border,
and the caption under each is just "Survey Photo No. N".

The same options the tool offers — border and its colour, caption wording,
numbering start, caption font, size and colour, photo compression — are kept on
the photo block as `layout`, and both the Word and the HTML renderer read them
from here so the two stay alike.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# The tool's Pro-mode photo box, in pixels at 96 dpi: 8.20 x 5.56 cm.
IMAGE_W_PX = 310
IMAGE_H_PX = 210
EMU_PER_PX = 9525
CM_PER_PX = 2.54 / 96

# Twips, as the tool sets them.
CELL_MARGIN = {"plain": {"top": 5, "bottom": 5, "left": 20, "right": 20},
               "border": {"top": 10, "bottom": 10, "left": 10, "right": 10}}
PARA_SPACING = {"plain": 5, "border": 10}
CAPTION_MARGIN = {"top": 5, "bottom": 5, "left": 20, "right": 20}
BORDER_SIZE = 12  # eighths of a point

KEYWORDS = ("Survey Photo No.", "QC Inspection Photo No.")
FONTS = ("Arial", "Calibri", "Times New Roman", "Georgia", "Verdana")
FONT_SIZES = (8, 9, 10, 11, 12, 14, 16, 18, 20)
FONT_COLORS = ("000000", "FFFFFF", "000080", "404040", "006400")
BORDER_COLORS = ("000000", "808080", "000080", "8B4513")
PER_PAGE = (8, 6)

# Longest side in px and JPEG quality, as the tool's presets. "original"
# keeps the full size; only the phone's rotation is corrected.
QUALITY = {
    "original": (None, 95),
    "high": (3000, 88),
    "balanced": (2200, 78),
    "small": (1600, 65),
    "display": (800, 80),   # HTML preview only
}

DEFAULTS: Dict[str, Any] = {
    "per_page": 8,
    "border": False,
    "border_color": "000000",
    "caption_keyword": "Survey Photo No.",
    "number_from": 1,
    "caption_font": "Arial",
    "caption_size": 11,
    "caption_color": "000000",
    "quality": "balanced",
    "landscape": True,
    "show_heading": False,
}


def layout_of(block: Dict[str, Any]) -> Dict[str, Any]:
    """The block's layout with anything missing or out of range set to the default."""
    raw = block.get("layout") or {}
    out = dict(DEFAULTS)

    def pick(key, allowed, cast=lambda v: v):
        try:
            v = cast(raw.get(key))
        except (TypeError, ValueError):
            return
        if v in allowed:
            out[key] = v

    pick("per_page", PER_PAGE, int)
    pick("caption_font", FONTS)
    pick("caption_size", FONT_SIZES, int)
    pick("caption_color", FONT_COLORS, lambda v: str(v).upper().lstrip("#"))
    pick("border_color", BORDER_COLORS, lambda v: str(v).upper().lstrip("#"))
    pick("quality", tuple(k for k in QUALITY if k != "display"))
    for key in ("border", "landscape", "show_heading"):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    kw = " ".join(str(raw.get("caption_keyword") or "").split())
    if kw:
        out["caption_keyword"] = kw[:40]
    try:
        n = int(raw.get("number_from"))
        if 1 <= n <= 9999:
            out["number_from"] = n
    except (TypeError, ValueError):
        pass
    return out


_PREFIX_ONLY = re.compile(
    r"^\(?\s*(?:survey\s+|qc\s+inspection\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?[:\-—\.,\s]*$",
    re.I,
)
_PREFIX = re.compile(
    r"^\s*\(?\s*(?:survey\s+|qc\s+inspection\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?\s*[:\-—\.,\s]\s*",
    re.I,
)


def strip_number(text: str) -> str:
    """
    The caption text without a photo number typed into it.

    Numbers are worked out when the report is made. Older reports and the
    photo studio wrote them into the text ("Photo 1", "Survey Photo No. 3: Seal"),
    which printed twice once the number was added again.
    """
    t = (text or "").strip()
    if not t or _PREFIX_ONLY.match(t):
        return ""
    return _PREFIX.sub("", t, count=1).strip()


def caption(layout: Dict[str, Any], number: int, text: str = "") -> str:
    body = strip_number(text)
    head = f"{layout['caption_keyword']} {number}"
    return f"{head} — {body}" if body else head


def photos_of(block: Dict[str, Any], computed: Dict[str, Any], assets: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every photo in the block, in order, with its printed number and caption."""
    lay = layout_of(block)
    shift = lay["number_from"] - 1
    groups_c = (computed or {}).get("groups", {})
    out: List[Dict[str, Any]] = []
    for g in block.get("groups", []) or []:
        ids = g.get("asset_ids", []) or []
        numbers = groups_c.get(g.get("id", ""), {}).get("numbers") or list(range(len(out) + 1, len(out) + 1 + len(ids)))
        for aid, num in zip(ids, numbers):
            n = num + shift
            out.append({
                "asset_id": aid,
                "number": n,
                "caption": caption(lay, n, g.get("observation", "")),
                "asset": assets.get(aid, {}) or {},
            })
    return out


def pages(photos: List[Any], layout: Dict[str, Any]) -> List[List[Any]]:
    """Photos split into pages; a heading on the first page takes one row."""
    per = layout["per_page"]
    first = per - 2 if layout["show_heading"] else per
    if not photos:
        return []
    chunks = [photos[:first]]
    rest = photos[first:]
    chunks += [rest[i:i + per] for i in range(0, len(rest), per)]
    return [c for c in chunks if c]
