"""
The client's private lists, read from PRIVATE_DATA_DIR (default backend/private).

  staff_and_surveyors.json    consignees' staff, shipping line / shipper /
                              insurer surveyors, the firm's own surveyors
  cold_storage_locations.json registered cold storages with their addresses
  banner.png                  the letterhead banner printed across the top of
                              page 1 of a survey report

They hold real names, so they are not in git and not in the frontend bundle.
A missing or unreadable file gives an empty list (or no banner): attendance
and the cold storage search then start empty, page 1 starts with the title,
and everything else works as before.
"""

import io
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

STAFF_FILE = "staff_and_surveyors.json"
COLD_STORAGE_FILE = "cold_storage_locations.json"
BANNER_FILE = "banner.png"
# The banner is printed 19.3 cm wide; 2,200 px is about 290 dpi there, and
# keeps every Word file from carrying the 2 MB original.
BANNER_MAX_PX = 2200

EMPTY_STAFF: Dict[str, List[Dict[str, str]]] = {
    "consignees": [],
    "shipping_lines": [],
    "shippers": [],
    "cargo_insurers": [],
    "mca_surveyors": [],
}


def private_dir() -> Path:
    if settings.PRIVATE_DATA_DIR:
        return Path(settings.PRIVATE_DATA_DIR)
    return Path(__file__).resolve().parents[2] / "private"


def _load(name: str, default: Any) -> Any:
    path = private_dir() / name
    if not path.exists():
        logger.warning("Private list %s not found; using an empty list.", path)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("Private list %s could not be read (%s); using an empty list.", path, exc)
        return default


def load_staff() -> Dict[str, List[Dict[str, str]]]:
    data = _load(STAFF_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {key: list(data.get(key) or []) for key in EMPTY_STAFF}


def load_cold_storages() -> List[Dict[str, str]]:
    data = _load(COLD_STORAGE_FILE, [])
    return data if isinstance(data, list) else []


def banner_jpeg() -> Optional[bytes]:
    """The page 1 banner as a JPEG on white, or None when there is no banner file."""
    path = private_dir() / BANNER_FILE
    if not path.exists():
        return None
    try:
        return _banner_jpeg(str(path), path.stat().st_mtime)
    except Exception as exc:  # a broken image must not stop a report
        logger.warning("Banner %s could not be read (%s); page 1 starts without it.", path, exc)
        return None


@lru_cache(maxsize=2)
def _banner_jpeg(path: str, _mtime: float) -> bytes:
    from PIL import Image

    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.getchannel("A"))
        im = flat
    else:
        im = im.convert("RGB")
    if im.width > BANNER_MAX_PX:
        im = im.resize((BANNER_MAX_PX, round(im.height * BANNER_MAX_PX / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    # Full colour detail: the default JPEG halves it (4:2:0), which washed
    # out the logo and the ship.
    im.save(buf, "JPEG", quality=95, subsampling=0)
    return buf.getvalue()
