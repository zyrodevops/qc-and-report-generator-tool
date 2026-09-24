"""
Primary reader for handwritten tally sheets: a hosted vision model.

Why this is primary rather than a fallback. The client's sheets are a
pre-printed Marine Cargo Agencies form filled in by pen:

  * the field labels and the SR.NO / COUNT / SOUND columns are printed, but the
    defect column headings are handwritten and differ sheet to sheet
  * photographs are frequently rotated a quarter turn, taken on a desk or a
    cold-room floor
  * subtotal rows are struck through with green highlighter, which classical
    binarisation turns into a solid block
  * counts are written with leading zeros — 09, 05, 02 — and the odd figure is
    overwritten or corrected in place

Morphological line detection plus a character recogniser does not survive that.
A vision model reads it, including the rotation, without preprocessing.

Primary means it reads first. It does not mean it is believed. Everything
returned here arrives in the Verification Workbench flagged for checking, and
the row arithmetic is proved against the total written on the sheet before
anything can be saved into a report.

Two structural facts about these sheets the prompt has to know, because getting
them wrong silently doubles the counts:

  * Each numbered line is ONE carton opened. Several lines share a count.
  * After each group of lines comes a SUBTOTAL line, usually highlighted, whose
    COUNT cell holds the total pieces examined for that group. That figure is
    the independent check: on a real sheet, sound + every defect on the subtotal
    line equals it exactly.
"""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image

from app.config import settings
from app.ingest.tally.logger import get_ocr_logger

logger = get_ocr_logger()

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Fraction of the page occupied by the printed header block, dropped when the
# client has chosen not to send identifying detail off-site.
_HEADER_FRACTION = 0.30

# Longest edge sent. The grid stays legible well below full phone resolution and
# a smaller image is markedly faster.
_MAX_EDGE = 2200

# If every model in the pool is busy, ask the whole pool once more after a
# short pause. The overall wait is capped by TALLY_CLOUD_TOTAL_BUDGET_SECONDS.
_ROUNDS = 2
_ROUND_PAUSE_SECONDS = 4.0


@dataclass
class CloudRow:
    """One line off the sheet. A null cell is one the model could not read."""
    group: str
    # As read: whole numbers for counts, decimals for kg weights. The pipeline
    # turns each into an int or a 3-dp Decimal, because it knows the unit.
    values: Dict[str, Optional[Any]] = field(default_factory=dict)
    stated_total: Optional[Any] = None
    is_subtotal: bool = False
    is_grand_total: bool = False


@dataclass
class CloudReadResult:
    configured: bool
    used: bool
    rows: List[CloudRow] = field(default_factory=list)
    headers: Dict[str, Any] = field(default_factory=dict)
    discovered_columns: List[str] = field(default_factory=list)
    error: Optional[str] = None
    header_sent: bool = True
    model: Optional[str] = None


def cloud_reader_configured() -> bool:
    """True when a key is present. Without one the local engine is used."""
    return bool(settings.GEMINI_API_KEY)


def _prepare_image(image_bytes: bytes) -> Tuple[bytes, bool]:
    """Downscale, and drop the header band when the client has asked for that."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    header_sent = True
    if not settings.TALLY_CLOUD_SEND_FULL_SHEET:
        w, h = img.size
        if h >= 400:
            img = img.crop((0, int(h * _HEADER_FRACTION), w, h))
            header_sent = False

    if max(img.size) > _MAX_EDGE:
        img.thumbnail((_MAX_EDGE, _MAX_EDGE), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), header_sent


def _build_prompt(categories: List[Dict[str, str]], commodity: Optional[str], header_sent: bool) -> str:
    known = ", ".join(f'"{c["label"]}"' for c in categories)
    fruit = (commodity or "fruit").lower()

    parts = [
        "This photograph is a handwritten cargo inspection tally sheet on a pre-printed form. "
        "It may be rotated; read it whichever way up it is.\n",
        f"The consignment is {fruit}. Columns usually drawn from: {known}. "
        "The handwritten column headings on this sheet are what count — if a heading is not in "
        "that list, report it under the heading as written.\n",
        "STRUCTURE — read this carefully, it is the part that goes wrong:\n"
        "- Each numbered line (SR.NO 1, 2, 3 …) is ONE carton that was opened. Several "
        "consecutive lines belong to the same COUNT; the count is usually written once against "
        "the first of them and left blank on the rest. Repeat it on every line of that group.\n"
        "- After each group there is a SUBTOTAL line. It is often struck through with "
        "highlighter and it has no SR.NO. Its COUNT cell holds the TOTAL PIECES examined for "
        "that group, not a caliber. Return that line with is_subtotal true and put that figure "
        "in stated_total.\n"
        "- If the sheet has a TOTAL column, put each line's written total in stated_total. "
        "If it has none, leave stated_total null on carton lines.\n"
        "- A line at the foot of the sheet labelled Total (or Grand Total) that adds up all "
        "the lines above it is not a carton: return it with is_grand_total true.\n",
        "TRANSCRIPTION RULES:\n"
        "- Report the figures written. Do not add up, correct, balance or infer anything.\n"
        "- Leading zeros are normal in counts: 09 is 9, 05 is 5.\n"
        "- Some sheets record weights in kg with decimals, e.g. 0.820. Report those as "
        "decimal numbers exactly as written; never drop the decimal point.\n"
        "- A blank cell, or one you cannot read with confidence, must be null. Never guess a "
        "number to make a line add up. A wrong figure that looks plausible is worse than a gap, "
        "because the gap gets filled in and the wrong figure gets signed.\n"
        "- If a figure is overwritten or corrected, report what appears to be the final value "
        "and leave it null if that is genuinely unclear.\n"
        "- Highlighter over a row does not change its values.\n"
        "- Ignore any blank facing page.\n",
    ]

    if header_sent:
        parts.append(
            "HEADER: also read the printed fields at the top — party name, survey date, "
            "destuff date, container number, room number, room temperature, pulp temperature "
            "range, brix range, and pressure range if present. Dates as written. Ranges as "
            "separate min and max. Anything absent or unreadable is null.\n"
        )

    return "".join(parts)


_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "columns": {
            "type": "array",
            "description": "Handwritten defect column headings, left to right as they appear.",
            "items": {"type": "string"},
        },
        "header": {
            "type": "object",
            "properties": {
                "party_name": {"type": "string", "nullable": True},
                "survey_date": {"type": "string", "nullable": True},
                "destuff_date": {"type": "string", "nullable": True},
                "container_number": {"type": "string", "nullable": True},
                "room_no": {"type": "string", "nullable": True},
                "room_temp": {"type": "number", "nullable": True},
                "pulp_temp_min": {"type": "number", "nullable": True},
                "pulp_temp_max": {"type": "number", "nullable": True},
                "brix_min": {"type": "number", "nullable": True},
                "brix_max": {"type": "number", "nullable": True},
                "pressure_min": {"type": "number", "nullable": True},
                "pressure_max": {"type": "number", "nullable": True},
            },
        },
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "count_label": {
                        "type": "string",
                        "description": "Count or variety for this line, e.g. '120', '30 XF', 'TANGO 74'.",
                    },
                    "is_subtotal": {"type": "boolean"},
                    "is_grand_total": {"type": "boolean"},
                    "stated_total": {
                        "type": "number",
                        "nullable": True,
                        "description": "The line's written total, if the sheet has one.",
                    },
                    "cells": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string"},
                                "value": {"type": "number", "nullable": True},
                            },
                            "required": ["column"],
                        },
                    },
                },
                "required": ["count_label", "cells"],
            },
        },
    },
    "required": ["rows"],
}


async def read_sheet(
    image_bytes: bytes,
    categories: List[Dict[str, str]],
    commodity: Optional[str] = None,
) -> CloudReadResult:
    """Read the whole sheet. Never raises; failure falls back to local OCR."""
    if not cloud_reader_configured():
        return CloudReadResult(
            configured=False, used=False,
            error="No GEMINI_API_KEY is configured, so the local engine was used instead.",
        )

    try:
        payload_bytes, header_sent = _prepare_image(image_bytes)
    except Exception as exc:
        logger.warning("Could not prepare the image for the cloud reader: %s", exc)
        return CloudReadResult(configured=True, used=False, error="The image could not be prepared for reading.")

    body = {
        "contents": [{
            "parts": [
                {"text": _build_prompt(categories, commodity, header_sent)},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(payload_bytes).decode("ascii"),
                }},
            ]
        }],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _SCHEMA,
        },
    }

    parsed, model_used, error = await _race_models(body)

    if parsed is None:
        return CloudReadResult(configured=True, used=False, header_sent=header_sent, error=error)

    rows, discovered = _parse_rows(parsed, categories)
    return CloudReadResult(
        configured=True,
        used=True,
        rows=rows,
        headers=_clean_headers(parsed.get("header") or {}) if header_sent else {},
        discovered_columns=discovered,
        header_sent=header_sent,
        model=model_used,
    )


def _model_pool() -> List[str]:
    """
    Every model worth asking, the configured one first.

    On the free tier any single model is regularly "experiencing high demand"
    (503) for minutes at a time, and which one is busy changes from hour to hour.
    Measured on 23 Sep 2026: of eleven models, eight returned 503 or 429 while
    three answered correctly — and it was not the newest ones that answered.
    So the pool is wide, and GEMINI_FALLBACK_MODELS lets it be changed without
    a code edit when Google retires or adds a model.
    """
    extra = [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]
    pool: List[str] = []
    for m in [settings.GEMINI_MODEL, *extra]:
        if m and m not in pool:
            pool.append(m)
    return pool


# Busy, rate-limited or briefly broken. Worth asking again; says nothing about the sheet.
_TRANSIENT = {429, 500, 502, 503, 504}


async def _ask_one(
    client: httpx.AsyncClient, model: str, body: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]], Optional[int]]:
    """
    One request to one model. Returns (model, parsed JSON or None, HTTP status).

    Never raises: in a race a timeout or dropped connection on one model is just
    that model losing, not a reason to stop the others.
    """
    try:
        resp = await client.post(
            _ENDPOINT.format(model=model),
            params={"key": settings.GEMINI_API_KEY},
            json=body, headers={"Content-Type": "application/json"},
        )
    except Exception as exc:
        logger.info("[CloudReader] %s: %s", model, type(exc).__name__)
        return model, None, None

    if resp.status_code != 200:
        logger.info("[CloudReader] %s returned %s", model, resp.status_code)
        return model, None, resp.status_code

    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return model, json.loads(text), 200
    except Exception:
        # A 200 with an unusable body loses too, rather than ending the race.
        logger.info("[CloudReader] %s answered but the reply could not be parsed", model)
        return model, None, 200


async def _race_models(
    body: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Ask every model in the pool at once and take the first usable answer.

    This replaced asking them one after another with back-off, which during a
    client demo spent over two minutes on four busy models in turn before giving
    up — while other models were answering in under four seconds. Asking in
    parallel costs a few extra requests per sheet, which at five or six sheets a
    day is nothing against the free allowance, and each model's quota is
    separate.

    If the whole pool is busy, one more round is tried after a short pause, and
    the total wait is capped so the surveyor is never left watching a spinner.

    Returns (parsed JSON, model that answered, error message for the surveyor).
    """
    import asyncio
    import time

    pool = _model_pool()
    deadline = time.monotonic() + settings.TALLY_CLOUD_TOTAL_BUDGET_SECONDS
    statuses: List[Optional[int]] = []

    async with httpx.AsyncClient(timeout=settings.TALLY_CLOUD_TIMEOUT_SECONDS) as client:
        for round_no in range(_ROUNDS):
            remaining = deadline - time.monotonic()
            if remaining <= 5:
                break

            tasks = [asyncio.create_task(_ask_one(client, m, body)) for m in pool]
            try:
                for next_done in asyncio.as_completed(tasks, timeout=remaining):
                    model, parsed, status = await next_done
                    statuses.append(status)
                    if parsed is not None:
                        logger.info("[CloudReader] %s answered first (round %d)", model, round_no + 1)
                        return parsed, model, None
            except asyncio.TimeoutError:
                logger.info("[CloudReader] round %d ran out of time", round_no + 1)
            finally:
                for t in tasks:
                    if not t.done():
                        t.cancel()

            # A key problem will not fix itself by asking again.
            if statuses and all(s in (401, 403) for s in statuses if s is not None):
                return None, None, "The API key was rejected. Check GEMINI_API_KEY."

            if round_no + 1 < _ROUNDS and deadline - time.monotonic() > _ROUND_PAUSE_SECONDS + 5:
                await asyncio.sleep(_ROUND_PAUSE_SECONDS)

    if statuses and all(s == 429 for s in statuses if s is not None):
        return None, None, ("Today's free reading allowance is used up. Type the figures in, "
                            "or try again later.")
    if not any(s is not None for s in statuses):
        return None, None, "Could not reach the online reader. Check the internet connection."
    return None, None, ("Google's reading service is overloaded right now. Wait a minute and "
                        "press Change to try the same photo again, or type the figures in.")


def _parse_rows(
    parsed: Dict[str, Any],
    categories: List[Dict[str, str]],
) -> Tuple[List[CloudRow], List[str]]:
    """Map the returned cells onto this fruit's columns, keeping any extras."""
    from app.ingest.tally.categories import match_header_to_category, slug

    discovered: List[str] = []
    rows: List[CloudRow] = []

    for raw in parsed.get("rows", []):
        values: Dict[str, Optional[int]] = {}
        for cell in raw.get("cells", []):
            heading = str(cell.get("column", "")).strip()
            if not heading:
                continue
            key = match_header_to_category(heading, categories)
            if not key:
                # A column this sheet has and the fruit config does not know
                # about. Keep it: it is the surveyor's data, and dropping it
                # would lose counts that belong in the report.
                key = slug(heading)
                if not key:
                    continue
                if heading not in discovered:
                    discovered.append(heading)

            raw_val = cell.get("value")
            # Kept as read; the pipeline turns it into a count or a 3-dp weight by unit.
            values[key] = raw_val if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool) else None

        total = raw.get("stated_total")
        rows.append(CloudRow(
            group=str(raw.get("count_label", "")).strip(),
            values=values,
            stated_total=total if isinstance(total, (int, float)) and not isinstance(total, bool) else None,
            is_subtotal=bool(raw.get("is_subtotal")),
            is_grand_total=bool(raw.get("is_grand_total")),
        ))

    return rows, discovered


def _clean_headers(h: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tidy the header fields.

    Dates come back as written on the sheet — 26/05/2026 — and are converted to
    ISO so the form receives what it expects. Container numbers lose their
    internal space. Neither is checked by arithmetic the way the counts are, so
    the workbench shows all of them for the surveyor to read against the sheet;
    there are only six and they take seconds.
    """
    from app.ingest.tally_ocr import clean_container_no, clean_ocr_date

    out: Dict[str, Any] = {}
    for k in (
        "party_name", "survey_date", "destuff_date", "container_number", "room_no",
        "room_temp", "pulp_temp_min", "pulp_temp_max",
        "brix_min", "brix_max", "pressure_min", "pressure_max",
    ):
        v = h.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            out[k] = None
        elif isinstance(v, str):
            out[k] = v.strip()
        else:
            out[k] = v

    for date_field in ("survey_date", "destuff_date"):
        raw = out.get(date_field)
        if isinstance(raw, str) and raw:
            out[date_field] = clean_ocr_date(raw) or raw

    raw_container = out.get("container_number")
    if isinstance(raw_container, str) and raw_container:
        out["container_number"] = clean_container_no(raw_container) or raw_container

    return out
