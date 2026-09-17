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

# Busy and rate-limit responses are routine on the free tier and say nothing
# about the sheet, so each model is given a few attempts with a widening gap
# before moving on to the next one.
_MAX_ATTEMPTS_PER_MODEL = 3
_BACKOFF_SECONDS = 2.0


@dataclass
class CloudRow:
    """One line off the sheet. A null cell is one the model could not read."""
    group: str
    values: Dict[str, Optional[int]] = field(default_factory=dict)
    stated_total: Optional[int] = None
    is_subtotal: bool = False


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
        "- Individual carton lines have no written total. Leave their stated_total null.\n",
        "TRANSCRIPTION RULES:\n"
        "- Report the digits written. Do not add up, correct, balance or infer anything.\n"
        "- Leading zeros are normal: 09 is 9, 05 is 5.\n"
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
                    "stated_total": {
                        "type": "integer",
                        "nullable": True,
                        "description": "Subtotal lines only: total pieces from the COUNT cell.",
                    },
                    "cells": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string"},
                                "value": {"type": "integer", "nullable": True},
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

    resp, model_used, transport_error = await _post_with_retries(body)

    if transport_error:
        return CloudReadResult(configured=True, used=False, header_sent=header_sent,
                               error=transport_error)

    if resp is None:
        return CloudReadResult(
            configured=True, used=False, header_sent=header_sent,
            error="Every reader was busy or rate-limited. Wait a minute and try again, "
                  "or type the sheet in — the row checks work either way.",
        )

    if resp.status_code in (401, 403):
        return CloudReadResult(configured=True, used=False, header_sent=header_sent,
                               error="The API key was rejected. Check GEMINI_API_KEY.")
    if resp.status_code >= 400:
        logger.warning("Cloud reader HTTP %s: %s", resp.status_code, resp.text[:400])
        return CloudReadResult(configured=True, used=False, header_sent=header_sent,
                               error=f"The reader returned an error (HTTP {resp.status_code}).")

    try:
        payload = resp.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except Exception:
        logger.warning("Cloud reader returned an unexpected payload.")
        return CloudReadResult(configured=True, used=False, header_sent=header_sent,
                               error="The reader's answer could not be understood.")

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


def _model_chain() -> List[str]:
    """
    The configured model first, then alternates.

    The free tier returns 503 when a model is busy and 429 when the per-minute
    allowance is spent, and both are common on the newest model at busy times.
    Both are temporary and neither says anything about the sheet, so a second
    model is tried rather than handing the surveyor an error he cannot act on.
    """
    chain = [settings.GEMINI_MODEL]
    for alternate in ("gemini-3.6-flash", "gemini-flash-latest", "gemini-3.5-flash"):
        if alternate not in chain:
            chain.append(alternate)
    return chain


async def _post_with_retries(
    body: Dict[str, Any],
) -> Tuple[Optional[httpx.Response], Optional[str], Optional[str]]:
    """
    Post to each model in turn, backing off on busy and rate-limit responses.

    Returns (response, model that answered, transport error). A response is
    returned as soon as one is not a busy/rate-limit refusal, including a real
    error, because those say something about the request rather than the load.
    """
    import asyncio

    last: Optional[httpx.Response] = None

    async with httpx.AsyncClient(timeout=settings.TALLY_CLOUD_TIMEOUT_SECONDS) as client:
        for model in _model_chain():
            url = _ENDPOINT.format(model=model)

            for attempt in range(_MAX_ATTEMPTS_PER_MODEL):
                try:
                    resp = await client.post(
                        url, params={"key": settings.GEMINI_API_KEY},
                        json=body, headers={"Content-Type": "application/json"},
                    )
                except httpx.TimeoutException:
                    return None, None, ("The reader timed out. Try again, or enter the "
                                        "figures by hand.")
                except Exception as exc:
                    logger.warning("Cloud reader call failed: %s", exc)
                    return None, None, ("The reader could not be reached. Check the "
                                        "internet connection.")

                if resp.status_code not in (429, 500, 502, 503, 504):
                    return resp, model, None

                last = resp
                wait = _BACKOFF_SECONDS * (2 ** attempt)
                logger.info(
                    "[CloudReader] %s returned %s; retrying in %.1fs (attempt %d/%d)",
                    model, resp.status_code, wait, attempt + 1, _MAX_ATTEMPTS_PER_MODEL,
                )
                await asyncio.sleep(wait)

            logger.info("[CloudReader] %s still unavailable; trying the next model.", model)

    return (last if last is not None and last.status_code not in (429, 503) else None), None, None


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
            values[key] = int(raw_val) if isinstance(raw_val, (int, float)) else None

        total = raw.get("stated_total")
        rows.append(CloudRow(
            group=str(raw.get("count_label", "")).strip(),
            values=values,
            stated_total=int(total) if isinstance(total, (int, float)) else None,
            is_subtotal=bool(raw.get("is_subtotal")),
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
