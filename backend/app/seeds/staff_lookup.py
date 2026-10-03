import json
import os
import re
from typing import List, Dict, Any, Optional

_DATA_PATH = os.path.join(os.path.dirname(__file__), "staff_and_surveyors.json")
_CACHE = None

def _get_data() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if os.path.exists(_DATA_PATH):
            with open(_DATA_PATH, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
        else:
            _CACHE = {
                "consignees": [],
                "shipping_lines": [],
                "shippers": [],
                "cargo_insurers": [],
                "mca_surveyors": [],
            }
    return _CACHE

def _clean_str(s: str) -> str:
    res = (s or "").lower()
    res = re.sub(r"\((?:consignees?|consignee's|consignee's customers|consignees end buyer / vendor)\)", " ", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(?:pvt|ltd|limited|llp|co|company|and|m/s)\b", " ", res, flags=re.IGNORECASE)
    res = re.sub(r"[-.,'\"&]", " ", res)
    return " ".join(res.split())

def lookup_consignee_staff(consignee_name: str) -> List[Dict[str, str]]:
    """Find matching staff members for a given consignee name."""
    if not consignee_name or consignee_name.startswith("["):
        return []
    
    cleaned_input = _clean_str(consignee_name)
    if not cleaned_input:
        return []

    data = _get_data()
    consignees = data.get("consignees", [])
    
    # 1. Exact cleaned match
    exact_matches = [c for c in consignees if _clean_str(c.get("company", "")) == cleaned_input]
    if exact_matches:
        return _dedup(exact_matches)
        
    # 2. Input contains company name as a complete whole-word phrase
    phrase_matches = []
    for c in consignees:
        cleaned_comp = _clean_str(c.get("company", ""))
        if cleaned_comp and re.search(r'\b' + re.escape(cleaned_comp) + r'\b', cleaned_input):
            phrase_matches.append(c)
    if phrase_matches:
        return _dedup(phrase_matches)

    # 3. Company name contains input as a complete whole-word phrase
    reverse_matches = []
    for c in consignees:
        cleaned_comp = _clean_str(c.get("company", ""))
        if cleaned_comp and re.search(r'\b' + re.escape(cleaned_input) + r'\b', cleaned_comp):
            reverse_matches.append(c)
    if reverse_matches:
        return _dedup(reverse_matches)

    # 4. Token overlap
    input_tokens = set(t for t in cleaned_input.split() if len(t) > 1)
    token_matches = []
    for c in consignees:
        cleaned_comp = _clean_str(c.get("company", ""))
        comp_tokens = set(t for t in cleaned_comp.split() if len(t) > 1)
        if comp_tokens and comp_tokens.issubset(input_tokens):
            token_matches.append(c)
        elif comp_tokens and len(comp_tokens.intersection(input_tokens)) >= 2:
            token_matches.append(c)

    return _dedup(token_matches)

def _dedup(matches: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for m in matches:
        key = (m.get("name"), m.get("representing"))
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    return deduped

def get_default_attendance(consignee_name: str = "") -> List[Dict[str, str]]:
    """Build initial attendance table rows for a report."""
    rows: List[Dict[str, str]] = []
    
    # 1. Consignee attendees
    matched = lookup_consignee_staff(consignee_name)
    if matched:
        for m in matched:
            rows.append({
                "name": m.get("name", ""),
                "designation": m.get("designation", ""),
                "representing": m.get("representing", ""),
            })
            
    # 2. Always add MCA Surveyor
    rows.append({
        "name": "Mr. Baburao Bhosale",
        "designation": "Surveyor",
        "representing": "Marine Cargo Agencies Pvt.Ltd (On behalf of Consignees)",
    })
    
    return rows
