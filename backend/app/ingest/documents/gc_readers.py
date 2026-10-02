"""
Readers for the documents of a general cargo job: the insurance certificate,
the bill of entry and shipping bill (Indian customs), the EIR (equipment
interchange report) and online container tracking. And, from the invoice and
packing lists, what general cargo needs that fruit did not: the invoice value
and each container's weight.

As the other readers: what was found and where, and nothing that was not.
A value these patterns cannot find is left out, and the surveyor sees that.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.ingest.documents.readers import _field, containers_in, written_date

_CURRENCY = r"(USD|INR|EUR|GBP|AED|US\$|Rs\.?|₹)"


def _flat(text: str) -> str:
    return " ".join((text or "").split())


def _dmy(s: Optional[str]) -> Optional[str]:
    """DD/MM/YYYY -> "24 May 2026". Only for Indian customs papers, which always print it day first."""
    if not s:
        return None
    m = re.fullmatch(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\s*", s)
    if not m:
        return written_date(s)
    try:
        d = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _money(currency: Optional[str], amount: str) -> str:
    cur = (currency or "").replace("US$", "USD").replace("Rs.", "INR").replace("Rs", "INR").replace("₹", "INR").strip()
    return f"{cur} {amount}".strip()


# ---------------------------------------------------------------------------
# Insurance policy / certificate
# ---------------------------------------------------------------------------

def read_insurance(texts: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"kind": "insurance", "pages": len(texts)}
    first = texts[0] if texts else ""
    flat = _flat(first)
    m = re.search(r"([A-Z][A-Za-z&.\- ]{2,60}?(?:General |Marine )?Insurance Co(?:mpany|\.)?(?: of [A-Za-z]+)?\.?"
                  r"(?: Ltd\.?| Limited))", flat)
    if m:
        _field(out, "insurer", m.group(1).strip(), 1, "text: insurance company")
    m = re.search(r"Policy\s*(?:No\.?|Number)\s*[:.]*\s*([0-9][0-9 ]{5,30}[0-9]|[A-Z0-9][A-Z0-9/\-]{5,30})", flat, re.I)
    if m:
        _field(out, "policy_number", " ".join(m.group(1).split()), 1, "label: Policy No.")
    m = re.search(r"Certificate\s*(?:No\.?|Number)\s*[:.]*\s*([A-Z0-9][A-Z0-9/\- ]{4,30}[A-Z0-9])", flat, re.I)
    if m:
        _field(out, "certificate_number", " ".join(m.group(1).split()), 1, "label: Certificate No.")
    m = re.search(r"(?:Insured(?:'s)? Name|Name of (?:the )?Insured|Assured)\s*[:.]*\s*[:.]*\s*(?:M/S\.?\s*)?"
                  r"([A-Z][A-Za-z0-9&.,\- ]{2,70}?)(?=\s{2,}|\s+(?:Policy|Customer|Address|Transit)\b|$)", first, re.I | re.M)
    if m:
        _field(out, "assured", m.group(1).strip(" .,"), 1, "label: Insured Name")
    # "Sum Insured in Invoice Currency ... <newline> USD 1,10,000.00 90.00 99,00,000.00 ..."
    m = re.search(r"Sum Insured[^\n]{0,120}\n\s*" + _CURRENCY + r"\s*([\d,]+(?:\.\d+)?)(?:\s+([\d.]+)\s+([\d,]+(?:\.\d+)?))?",
                  first, re.I)
    if m:
        value = _money(m.group(1), m.group(2))
        if m.group(4) and "INR" not in value:
            value += f" (INR {m.group(4)})"
        _field(out, "insured_value", value, 1, "table: Sum Insured")
    else:
        m = re.search(r"(?:Sum Insured|Insured Value|Amount Insured)\s*(?:\(?[A-Za-z ]{0,20}\)?)?\s*[:\-]?\s*"
                      + _CURRENCY + r"?\s*([\d,]{4,}(?:\.\d+)?)", flat, re.I)
        if m:
            _field(out, "insured_value", _money(m.group(1), m.group(2)), 1, "label: Sum Insured")
    m = re.search(r"(?:Policy )?Issuance Date\s*[:.]*\s*[:.]*\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/,]+\d{2,4})",
                  flat, re.I)
    if m:
        _field(out, "issue_date", _dmy(m.group(1)), 1, "label: Issuance Date")
    return out


# ---------------------------------------------------------------------------
# Indian customs: bill of entry (import) and shipping bill (export)
# ---------------------------------------------------------------------------

def _customs_seals(texts: List[str]) -> List[Dict[str, str]]:
    """The container list: "1 F SEAL001 TSTU1111118" -> container and seal."""
    out: List[Dict[str, str]] = []
    for t in texts:
        for line in t.splitlines():
            conts = containers_in(line)
            if not conts:
                continue
            m = re.search(r"\b\d{1,3}\s+(?:F|L|FCL|LCL)\s+([A-Z0-9]{5,15})\s+" + conts[0][:4], line)
            if m and not any(x["container"] == conts[0] for x in out):
                out.append({"container": conts[0], "seal": m.group(1)})
    return out


def read_bill_of_entry(texts: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"kind": "bill_of_entry", "pages": len(texts)}
    first = texts[0] if texts else ""
    m = re.search(r"BE No\s+BE Date[^\n]*\n\s*([A-Z]{5}\d)\s+(\d{5,9})\s+(\d{2}/\d{2}/\d{4})", first)
    if m:
        _field(out, "port_code", m.group(1), 1, "box: Port Code")
        _field(out, "be_number", m.group(2), 1, "box: BE No")
        _field(out, "be_date", _dmy(m.group(3)), 1, "box: BE Date")
    m = re.search(r"CB NAME\s+(.+?)\s*(?:\d\.|$)", first, re.M)
    if m:
        _field(out, "customs_broker", m.group(1).strip(), 1, "box: CB NAME")
    m = re.search(r"1\.IGM NO.*?\n\s*(\d{5,9})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})", first, re.S)
    if m:
        _field(out, "igm_number", m.group(1), 1, "box: IGM NO")
        _field(out, "igm_date", _dmy(m.group(2)), 1, "box: IGM DATE")
        _field(out, "inward_date", _dmy(m.group(3)), 1, "box: INW DATE")
    m = re.search(r"OOC DATE\s*[:.]?\s*(\d{2}/\d{2}/\d{4})", _flat("\n".join(texts)))
    if m:
        _field(out, "ooc_date", _dmy(m.group(1)), 1, "box: OOC DATE")
    seals = _customs_seals(texts)
    if seals:
        out["containers"] = seals
    return out


def read_shipping_bill(texts: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"kind": "shipping_bill", "pages": len(texts)}
    first = texts[0] if texts else ""
    m = re.search(r"SB No\s+SB Date.*?\b([A-Z]{5}\d)\s+(\d{5,9})\s+(\d{1,2}-[A-Z]{3}-\d{2,4})", first, re.S)
    if m:
        _field(out, "port_code", m.group(1), 1, "box: Port Code")
        _field(out, "sb_number", m.group(2), 1, "box: SB No")
        _field(out, "sb_date", written_date(m.group(3)), 1, "box: SB Date")
    m = re.search(r"CB NAME\s+(.+?)\s{2,}|CB NAME\s+(.+?)\s+\d+\.", first)
    if m:
        _field(out, "customs_broker", (m.group(1) or m.group(2)).strip(), 1, "box: CB NAME")
    seals = _customs_seals(texts)
    if seals:
        out["containers"] = seals
    return out


# ---------------------------------------------------------------------------
# EIR: one container per page, as the terminal printed (often photographed) it
# ---------------------------------------------------------------------------

def read_eir(texts: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"kind": "eir", "pages": len(texts)}
    rows = []
    for n, t in enumerate(texts, 1):
        conts = containers_in(t)
        if not conts:
            continue
        row: Dict[str, Any] = {"container": conts[0], "page": n}
        for key, rx in (("out", r"Out\s*Date\s*:\s*([0-9eO/ ]{8,12}\s+\d{1,2}:\d{2})"),
                        ("in", r"In\s*Date\s*:\s*([0-9eO/ ]{8,12}\s+\d{1,2}:\d{2})"),
                        ("movement", r"(DELIVER(?:Y)?\s+IMPORT\s+CON\s?TAINER|RECEIVE\s+EXPORT\s+CON\s?TAINER)"),
                        ("destination", r"Dest\s*/?\s*POD2?\s*:\s*([^\n]+)"),
                        ("seal", r"Seal\s*1\s*:\s*([A-Z0-9]{5,15})"),
                        ("truck", r"Truck\s*No\s*:\s*([A-Z0-9 ]{6,14})\b"),
                        ("gross", r"Gross\s*Wt\s*:\s*([\d. ]+)"),
                        ("remarks", r"Re?r?marks\s*:\s*([^\n]*)")):
            m = re.search(rx, t, re.I)
            if m and m.group(1).strip():
                v = " ".join(m.group(1).split())
                if key in ("out", "in"):
                    v = v.replace("e", "0").replace("O", "0")
                if key == "seal":
                    # OCR reads the letter O of a seal as the digit 0 and back again: kept as printed.
                    v = v.upper()
                row[key] = v
        rows.append(row)
    if rows:
        out["eirs"] = rows
    return out


# ---------------------------------------------------------------------------
# Container tracking (the shipping line's web page, printed)
# ---------------------------------------------------------------------------

_EVENTS = (
    "EMPTY TO SHIPPER", "READY TO BE LOADED", "LOADED ON BOARD", "VESSEL DEPARTURE", "VESSEL ARRIVAL",
    "DISCHARGED IN TRANSHIPMENT", "DISCHARGED FROM VESSEL", "DISCHARGED", "IN TRANSIT", "GATE IN RAMP",
    "GATE OUT TO CONSIGNEE", "CONTAINER TO CONSIGNEE", "EMPTY RETURNED", "EMPTY IN DEPOT",
)
_EVENT_RE = re.compile(
    r"(?:MON|TUES|WEDNES|THURS|FRI|SATUR|SUN)DAY,?\s*(\d{1,2}-[A-Z]{3}-\s?\d{2,4})\s+(\d{1,2}:\d{2})\s*(?:[AP]M)?\s+("
    + "|".join(re.escape(e) for e in _EVENTS) + r")\b(.*)")


def read_tracking(texts: List[str]) -> Dict[str, Any]:
    """Each container's moves: when it was loaded, discharged at the port of discharge, and sent to the consignees."""
    out: Dict[str, Any] = {"kind": "container_tracking", "pages": len(texts)}
    per: Dict[str, Dict[str, Any]] = {}
    for n, t in enumerate(texts, 1):
        up = t.upper()
        conts = containers_in(up)
        # A page that tracks one container (its number at the top).
        head = containers_in(up[:300])
        events = []
        for line in up.splitlines():
            m = _EVENT_RE.search(line)
            if m:
                events.append({"date": written_date(m.group(1).replace(" ", "")), "time": m.group(2), "event": m.group(3),
                               "place": " ".join(m.group(4).split())[:60]})
        if head and events:
            c = per.setdefault(head[0], {"container": head[0], "page": n})
            c["events"] = events
        # The status list: "TSTU1111118 22G1 (20ST) GATE OUT TO CONSIGNEE / ETA Berth at POD
        # / Sat.11-JUL-2026 ... Display Details / SOME ICD Tue. 04-AUG-2026 12:35 PM" —
        # the status's own date is the one after "Display Details" (the first is the ETA).
        for m in re.finditer(r"\b([A-Z]{4}\d{7})\b[^\n]*?\b(" + "|".join(re.escape(e) for e in _EVENTS) + r")\b"
                             r"(?:[\s\S]{0,160}?DISPLAY DETAILS\s+([A-Z ,()\-]+?)\s+(?:MON|TUE|WED|THU|FRI|SAT|SUN)[A-Z]*\.?\s*"
                             r"(\d{1,2}-[A-Z]{3}-\d{4}))?", up):
            if m.group(1) in conts:
                c = per.setdefault(m.group(1), {"container": m.group(1), "page": n})
                c.setdefault("status", m.group(2))
                if m.group(4):
                    c.setdefault("status_date", written_date(m.group(4)))
                    c.setdefault("status_place", " ".join(m.group(3).split()))
    for c in per.values():
        ev = c.get("events") or []

        def last(*names):
            hits = [e for e in ev if e["event"] in names and e.get("date")]
            return hits[-1] if hits else None

        def first(*names):
            hits = [e for e in ev if e["event"] in names and e.get("date")]
            return hits[0] if hits else None

        if first("LOADED ON BOARD"):
            c["loaded_on_board"] = first("LOADED ON BOARD")["date"]
        if last("VESSEL ARRIVAL"):
            c["arrival"] = last("VESSEL ARRIVAL")["date"]
        if last("DISCHARGED", "DISCHARGED FROM VESSEL"):
            c["discharged"] = last("DISCHARGED", "DISCHARGED FROM VESSEL")["date"]
        if last("GATE OUT TO CONSIGNEE", "CONTAINER TO CONSIGNEE"):
            c["to_consignee"] = last("GATE OUT TO CONSIGNEE", "CONTAINER TO CONSIGNEE")["date"]
        elif c.get("status") in ("GATE OUT TO CONSIGNEE", "CONTAINER TO CONSIGNEE") and c.get("status_date"):
            c["to_consignee"] = c["status_date"]
    if per:
        out["tracking"] = list(per.values())
    return out


# ---------------------------------------------------------------------------
# What general cargo needs from the invoice and the packing lists
# ---------------------------------------------------------------------------

def _amount(s: str) -> float:
    return float(s.replace(",", ""))


def invoice_value(texts: List[str]) -> Optional[str]:
    """The invoice's value, with its currency: "USD 1,90,336.50"."""
    flat = _flat("\n".join(texts))
    for rx in (r"Invoice Value\s*[:\-]?\s*([\d,]+\.\d{2})\s*" + _CURRENCY,
               r"(?:GRAND TOTAL|TOTAL (?:INVOICE )?(?:VALUE|AMOUNT))\s*(?:\(?\s*" + _CURRENCY + r"\s*\)?)?\s*[:\-]?\s*"
               + _CURRENCY + r"?\s*\$?([\d,]+\.\d{2})",
               r"(?:Net Receivable|Invoice Amount|Basic Amount)\s*\(\s*" + _CURRENCY + r"\s*\)\s*:\s*([\d,]+\.\d{2})"):
        m = re.search(rx, flat, re.I)
        if not m:
            continue
        g = [x for x in m.groups() if x]
        amount = next((x for x in g if re.fullmatch(r"[\d,]+\.\d{2}", x)), None)
        cur = next((x for x in g if not re.fullmatch(r"[\d,]+\.\d{2}", x)), None)
        if amount:
            return _money(cur, amount)
    # Amounts printed with a dollar sign: the invoice value is the largest.
    # The "TOTAL" line can be a balance ("less: advance payment received").
    dollars = re.findall(r"\$\s?([\d,]+\.\d{2})", flat)
    if dollars:
        return _money("USD", max(dollars, key=_amount))
    return None


def total_weights(texts: List[str]) -> Dict[str, str]:
    """The shipment's total net / gross weight in kg, as the packing list states it."""
    flat = _flat("\n".join(texts))
    out: Dict[str, str] = {}
    for key, label in (("total_net_kg", "NET"), ("total_gross_kg", "GROSS")):
        m = re.search(rf"TOTAL {label} WEIGHT\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(KGS?|MT|M\.T\.)?", flat, re.I)
        if m:
            v = m.group(1).replace(",", "")
            out[key] = _mt_kg(v) if (m.group(2) or "").upper().startswith("M") else v
    return out


def container_weights(texts: List[str]) -> List[Dict[str, Any]]:
    """
    Each container's net and gross weight (kg) as the packing list states it:
    a line per container ("TSTU1111118 24000.000 24090.000 ...", or "... 21.000
    M.T. 21.410 M.T."), or one container per page with its total line.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for n, t in enumerate(texts, 1):
        page_conts = containers_in(t)
        for line in t.splitlines():
            conts = containers_in(line)
            if len(conts) != 1:
                continue
            after = line[line.find(conts[0][:4]) + 11:]
            mt = re.findall(r"(\d+(?:\.\d+)?)\s*M\.?\s?T\.?", after, re.I)
            kg = re.findall(r"\b(\d{3,6}\.\d{1,3})\b", after)
            if len(mt) >= 2:
                out[conts[0]] = {"container": conts[0], "net_kg": _mt_kg(mt[0]), "gross_kg": _mt_kg(mt[1]), "page": n}
            elif len(kg) >= 2:
                out[conts[0]] = {"container": conts[0], "net_kg": kg[0], "gross_kg": kg[1], "page": n}
        # One container per page: "CONTAINER NO.: X" and "TOTAL <gross> <tare> <net>".
        m = re.search(r"CONTAINER NO\.?\s*:\s*([A-Z]{4}\d{7})", t)
        tot = re.search(r"^\s*TOTAL\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", t, re.M)
        if m and tot and m.group(1) in page_conts and m.group(1) not in out:
            out[m.group(1)] = {"container": m.group(1), "gross_kg": tot.group(1), "net_kg": tot.group(3), "page": n}
    return list(out.values())


def _mt_kg(mt: str) -> str:
    """20.765 (tonnes) -> "20765"."""
    try:
        return f"{float(mt) * 1000:.3f}".rstrip("0").rstrip(".")
    except ValueError:
        return mt
