"""
Scanned papers read by the online reader (Gemini): weight slips and lorry
receipts / consignment notes.

These come as scans or phone photos, so there is no text to read on this
server. Each page's picture is sent to Gemini with a request to copy what is
printed, field by field, and to leave a field empty when it cannot be read.
What comes back is only a proposal: every value is shown to the surveyor,
who corrects or clears it before anything goes into the report.

Checked here, not trusted:
  - a container number must have its check digit right, else it is flagged;
  - on a weight slip, gross - tare must equal net when all three are read,
    else the slip is flagged;
  - a figure must look like a figure.

When no model answers (no key, the free allowance used up, no internet, all
busy), the reason is returned and the surveyor types the figures in; the
weighbridge table in each survey paragraph takes them as it always did.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

PAGES_PER_REQUEST = 5

FIELDS = {
    "weight_slip": ("weighbridge", "slip_no", "date", "vehicle_no", "container_no", "gross_kg", "tare_kg", "net_kg"),
    "lorry_receipt": ("lr_no", "date", "truck_no", "from_place", "to_place", "consignor", "consignee", "packages",
                      "weight", "remarks"),
}

_PROMPTS = {
    "weight_slip": (
        "Each image is one weighbridge weight slip (weighment slip), scanned or photographed. For each image, copy "
        "exactly what is printed or written: the weighbridge's name, the slip (ticket / serial) number, the date, the "
        "vehicle (truck) number, the container number, and the gross, tare and net weights in kg as printed (digits "
        "only, no units). If a value is not on the slip or cannot be read with certainty, give null. Do not work "
        "anything out and do not guess."
    ),
    "lorry_receipt": (
        "Each image is one lorry receipt / goods consignment note from a road transporter, scanned or photographed. "
        "For each image, copy exactly what is printed or written: the LR / consignment note number, the date, the "
        "truck number, from where and to where, the consignor, the consignee, the number and kind of packages, the "
        "weight, and any remarks (such as damage noted). If a value is not there or cannot be read with certainty, "
        "give null. Do not guess."
    ),
}


def _schema(kind: str) -> Dict[str, Any]:
    props = {f: {"type": "STRING", "nullable": True} for f in FIELDS[kind]}
    props["image"] = {"type": "INTEGER"}
    return {"type": "OBJECT", "properties": {"items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": props}}}}


def _digits(v: Any) -> Optional[str]:
    s = re.sub(r"[,\s]", "", str(v or ""))
    s = re.sub(r"(?i)kgs?$", "", s)
    return s if re.fullmatch(r"\d+(?:\.\d+)?", s) else None


def check_row(kind: str, row: Dict[str, Any]) -> List[str]:
    """What looks wrong in one read row, in words for the surveyor."""
    from app.ingest.documents.readers import containers_in

    flags: List[str] = []
    cno = str(row.get("container_no") or "").replace(" ", "").upper()
    if cno and not containers_in(cno):
        flags.append(f"container number {cno} fails its check digit")
    if kind == "weight_slip":
        g, t, n = (_digits(row.get(k)) for k in ("gross_kg", "tare_kg", "net_kg"))
        for key in ("gross_kg", "tare_kg", "net_kg"):
            if row.get(key) not in (None, "") and _digits(row.get(key)) is None:
                flags.append(f"{key.replace('_kg', '')} weight is not a number")
        if g and t and n and abs(float(g) - float(t) - float(n)) > 0.5:
            flags.append("gross − tare ≠ net on the slip")
    return flags


async def read_scans(kind: str, images: List[Tuple[int, bytes]]) -> Dict[str, Any]:
    """{"rows": [{page, fields..., flags}], "error": str|None, "model": str|None}."""
    if kind not in FIELDS:
        return {"rows": [], "error": "This kind of scan is not read by the online reader; type it in.", "model": None}
    if not images:
        return {"rows": [], "error": "No scanned picture was found on these pages.", "model": None}
    if not settings.GEMINI_API_KEY:
        return {"rows": [], "error": "The online reader is not set up (no Gemini key). Type the figures in.", "model": None}

    from app.ingest.tally.cloud_reader import _race_models

    rows: List[Dict[str, Any]] = []
    model_used: Optional[str] = None
    error: Optional[str] = None
    for start in range(0, len(images), PAGES_PER_REQUEST):
        batch = images[start:start + PAGES_PER_REQUEST]
        parts: List[Dict[str, Any]] = [{"text": _PROMPTS[kind] + " Reply as JSON: {\"items\": [one object per image, "
                                        "with \"image\" = its number from 1, in order]}."}]
        for i, (_page, jpeg) in enumerate(batch, 1):
            parts.append({"text": f"Image {i}:"})
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")}})
        body = {"contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                     "responseSchema": _schema(kind)}}
        try:
            parsed, model, err = await _race_models(body)
        except Exception as exc:  # the report must not depend on this
            logger.warning("[ScanReader] %s: %s", type(exc).__name__, exc)
            parsed, model, err = None, None, "The online reader failed."
        if parsed is None:
            error = err or "The online reader gave no answer."
            # Pages not read stay in the list, empty, for the surveyor to type.
            rows += [{"page": p, **{f: None for f in FIELDS[kind]}, "flags": ["not read"]} for p, _ in batch]
            continue
        model_used = model_used or model
        items = parsed.get("items") or []
        for i, (page, _jpeg) in enumerate(batch, 1):
            item = next((x for x in items if x.get("image") == i), items[i - 1] if i - 1 < len(items) else {})
            row = {"page": page, **{f: (str(item.get(f)).strip() if item.get(f) not in (None, "") else None)
                                    for f in FIELDS[kind]}}
            if kind == "weight_slip":
                for k in ("gross_kg", "tare_kg", "net_kg"):
                    row[k] = _digits(row[k]) or row[k]
                if row.get("container_no"):
                    row["container_no"] = row["container_no"].replace(" ", "").upper()
            row["flags"] = check_row(kind, row)
            rows.append(row)
    return {"rows": rows, "error": error, "model": model_used}
