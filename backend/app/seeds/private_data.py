"""
The client's private lists, read from PRIVATE_DATA_DIR (default backend/private).

  staff_and_surveyors.json    consignees' staff, shipping line / shipper /
                              insurer surveyors, the firm's own surveyors
  cold_storage_locations.json registered cold storages with their addresses

They hold real names, so they are not in git and not in the frontend bundle.
A missing or unreadable file gives an empty list: attendance and the cold
storage search then start empty and everything else works as before.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

STAFF_FILE = "staff_and_surveyors.json"
COLD_STORAGE_FILE = "cold_storage_locations.json"

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
