"""
Port Normalization Engine.
Identifies port locations, ensures country names are attached (e.g., 'Nhava Sheva, India'),
utilizing an offline pre-seeded dictionary, persistent local cache, and free OpenStreetMap
Nominatim fallback for unknown ports.
"""

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"
PORTS_DATA_FILE = SEEDS_DIR / "ports_data.json"
CACHED_PORTS_FILE = SEEDS_DIR / "cached_ports.json"

_COUNTRIES: Set[str] = set()
_PORTS_MAP: Dict[str, Dict[str, str]] = {}
_DYNAMIC_CACHE: Dict[str, str] = {}
_LOADED = False


def _load_data():
    global _COUNTRIES, _PORTS_MAP, _DYNAMIC_CACHE, _LOADED
    if _LOADED:
        return

    if PORTS_DATA_FILE.exists():
        try:
            with open(PORTS_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _COUNTRIES = {c.strip().lower() for c in data.get("countries", []) if c.strip()}
                _PORTS_MAP = {k.strip().lower(): v for k, v in data.get("ports", {}).items()}
        except Exception as exc:
            logger.warning("Failed to load ports_data.json: %s", exc)

    if CACHED_PORTS_FILE.exists():
        try:
            with open(CACHED_PORTS_FILE, "r", encoding="utf-8") as f:
                _DYNAMIC_CACHE = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load cached_ports.json: %s", exc)

    _LOADED = True


def _save_dynamic_cache():
    try:
        with open(CACHED_PORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(_DYNAMIC_CACHE, f, indent=2)
    except Exception as exc:
        logger.warning("Failed to save cached_ports.json: %s", exc)


def has_country(port_str: str) -> bool:
    """
    Returns True if the port string already contains or ends with a recognized country.
    E.g. 'Navegantes, SC, Brazil' -> True, 'Cape Town, South Africa' -> True, 'Nhava Sheva' -> False.
    """
    _load_data()
    s = (port_str or "").strip()
    if not s or s.startswith("["):
        return True

    # If comma-separated, check the last element (and second to last element for state, country)
    parts = [p.strip().lower() for p in s.split(",") if p.strip()]
    if len(parts) >= 2:
        last = parts[-1]
        # Direct match or word match against known countries
        if last in _COUNTRIES:
            return True
        for c in _COUNTRIES:
            if re.search(rf"\b{re.escape(c)}\b", last):
                return True

    # Check if the entire string ends with a country name (e.g. 'Dalian China' or 'Port Chalmers New Zealand')
    s_lower = s.lower()
    for c in _COUNTRIES:
        if s_lower.endswith(c):
            # Check boundary before country
            pre = s_lower[:-len(c)].rstrip()
            if not pre or not pre[-1].isalnum() or pre.endswith(",") or pre.endswith("-"):
                return True

    return False


def fetch_country_online(port_name: str) -> Optional[str]:
    """
    Queries free OpenStreetMap Nominatim for port country with English response.
    Saves to dynamic cache upon success.
    """
    _load_data()
    clean = re.sub(r"\b(port of|terminal|cfs|port|icd)\b", "", port_name, flags=re.I).strip() or port_name
    headers = {
        "User-Agent": "MarineCargoReportTool/1.0 (info@marinecargo.in)",
        "Accept-Language": "en",
    }

    # Try 1: with 'port' keyword, Try 2: just clean name
    for q_str in [f"{clean} port", clean]:
        query = urllib.parse.quote(q_str)
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&addressdetails=1&accept-language=en"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and isinstance(data, list):
                    addr = data[0].get("address", {})
                    country = addr.get("country")
                    if country:
                        # Clean and return standard country
                        country_clean = country.strip()
                        key = port_name.strip().lower()
                        _DYNAMIC_CACHE[key] = country_clean
                        _save_dynamic_cache()
                        return country_clean
        except Exception:
            pass
    return None


def get_port_country(port_str: str, fetch_online: bool = True) -> Optional[str]:
    """
    Finds the country for a given port name using:
    1. Local pre-seeded dictionary
    2. Dynamic cache
    3. Online Nominatim query (if fetch_online is True)
    """
    _load_data()
    s = (port_str or "").strip()
    if not s or s.startswith("["):
        return None

    # Clean port string (remove 'Port', punctuation for key matching)
    key = s.lower()
    key_clean = re.sub(r"\b(port|terminal|cfs|icd)\b", "", key, flags=re.I).strip(" ,.-")

    # 1. Exact match in pre-seeded map
    if key in _PORTS_MAP:
        return _PORTS_MAP[key]["country"]
    if key_clean in _PORTS_MAP:
        return _PORTS_MAP[key_clean]["country"]

    # 2. Substring match in pre-seeded map
    for p_key, info in _PORTS_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", key):
            return info["country"]

    # 3. Dynamic cache
    if key in _DYNAMIC_CACHE:
        return _DYNAMIC_CACHE[key]
    if key_clean in _DYNAMIC_CACHE:
        return _DYNAMIC_CACHE[key_clean]

    # 4. Online lookup
    if fetch_online:
        country = fetch_country_online(s)
        if country:
            return country

    return None


def normalize_port_name(port_str: str, fetch_online: bool = True) -> str:
    """
    Normalizes a single port name by appending ', <Country>' if missing.
    E.g.:
      'Nhava Sheva' -> 'Nhava Sheva, India'
      'Navegantes, SC, Brazil' -> 'Navegantes, SC, Brazil'
      'Dalian' -> 'Dalian, China'
      '[Port of Discharge]' -> '[Port of Discharge]'
    """
    s = (port_str or "").strip()
    if not s or s.startswith("["):
        return s

    if has_country(s):
        return s

    country = get_port_country(s, fetch_online=fetch_online)
    if country:
        # Check if country isn't already inside
        if not re.search(rf"\b{re.escape(country)}\b", s, re.I):
            return f"{s}, {country}"

    return s


def normalize_voyage(voyage_str: str, fetch_online: bool = True) -> str:
    """
    Normalizes a full voyage string like 'Navegantes, SC, Brazil to Nhava Sheva'.
    Splits by ' to ', normalizes each side, and rejoins.
    E.g.:
      'Navegantes, SC, Brazil to Nhava Sheva' -> 'Navegantes, SC, Brazil to Nhava Sheva, India'
      'Navegantes to Nhava Sheva' -> 'Navegantes, Brazil to Nhava Sheva, India'
      'Valparaiso to Mundra' -> 'Valparaiso, Chile to Mundra, India'
    """
    s = (voyage_str or "").strip()
    if not s or s.startswith("["):
        return s

    # Match ' to ' delimiter
    if re.search(r"\s+to\s+", s, flags=re.I):
        parts = re.split(r"\s+to\s+", s, flags=re.I, maxsplit=1)
        origin = normalize_port_name(parts[0], fetch_online=fetch_online)
        dest = normalize_port_name(parts[1], fetch_online=fetch_online)
        return f"{origin} to {dest}"

    return normalize_port_name(s, fetch_online=fetch_online)
