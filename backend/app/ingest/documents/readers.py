"""
Readers for each kind of shipment document.

Every reader returns what it found and where — the page and the label or
pattern it came from — and leaves out what it did not find. Nothing here fills
a gap: a field that is not on the document is simply absent, and the surveyor
sees that on the review screen.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.ingest.documents.pdf_boxes import PageBoxes, first_of

# ---------------------------------------------------------------------------
# Shapes that identify a value wherever it is printed
# ---------------------------------------------------------------------------

_CONTAINER = re.compile(r"\b([A-Z]{3}[UJZ])\s?(\d{6})\s?(\d)\b")
_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def iso6346_ok(owner: str, serial: str, check: str) -> bool:
    """The container number's own check digit. Keeps "RUC6BR0158…" and the like out."""
    vals = {}
    n = 10
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if n % 11 == 0:
            n += 1
        vals[c] = n
        n += 1
    code = owner + serial
    total = sum((vals[ch] if ch.isalpha() else int(ch)) * (2 ** i) for i, ch in enumerate(code))
    return (total % 11) % 10 == int(check)


def containers_in(text: str) -> List[str]:
    out: List[str] = []
    for m in _CONTAINER.finditer(text):
        if iso6346_ok(m.group(1), m.group(2), m.group(3)):
            c = m.group(1) + m.group(2) + m.group(3)
            if c not in out:
                out.append(c)
    return out


def written_date(text: str) -> Optional[str]:
    """A date with the month in words, as "16 May 2026". Numeric dates are left alone:
    04/05/2026 is April or May depending on who typed it."""
    t = text.strip().upper()
    m = re.search(r"\b(\d{1,2})[\s\-./]+([A-Z]{3})[A-Z]*[\s\-./,]+(\d{2,4})\b", t)
    if not m:
        m2 = re.search(r"\b([A-Z]{3})[A-Z]*[\s\-./]+(\d{1,2}),?[\s\-./]+(\d{2,4})\b", t)
        if not m2:
            return None
        mon, day, year = m2.group(1), m2.group(2), m2.group(3)
    else:
        day, mon, year = m.group(1), m.group(2), m.group(3)
    if mon not in _MONTHS:
        return None
    y = int(year)
    if y < 100:
        y += 2000
    try:
        d = datetime(y, _MONTHS[mon], int(day))
    except ValueError:
        return None
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _num(s: Optional[str]) -> Optional[str]:
    return s.strip() if s else None


# ---------------------------------------------------------------------------
# Opening a PDF
# ---------------------------------------------------------------------------

def open_pdf(data: bytes) -> Tuple[List[PageBoxes], List[str]]:
    import pdfplumber

    boxes: List[PageBoxes] = []
    texts: List[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            boxes.append(PageBoxes(page))
            texts.append(page.extract_text(layout=True) or "")
    return boxes, texts


def quick_text(data: bytes, max_pages: int = 3) -> str:
    """The first pages' text, fast, for telling what a document is."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((reader.pages[i].extract_text() or "") for i in range(min(max_pages, len(reader.pages))))
    except Exception:
        return ""


def classify(text: str, filename: str = "") -> str:
    """What a document is, from its own words (the file name only as a tie-break)."""
    t = text.upper()
    name = filename.upper()
    if len(t.strip()) < 40:
        return "scanned"
    if re.search(r"LOGGING SUMMARY|DATA LOGGER|TRIP LENGTH|MEAN KINETIC|DATA POINT", t):
        return "recorder"
    # Another surveyor's report quotes the B/L; it is not one.
    if re.search(r"JOINT SURVEY REPORT|SURVEY REPORT NO|INSPECTION REPORT", t[:1500]):
        return "other_report"
    if re.search(r"AIR\s*WAY\s*BILL|AIRWAY\s*BILL|AIR CONSIGNMENT NOTE|AIRPORT OF DEPARTURE", t):
        return "air_waybill"
    if re.search(r"SEA\s*WAYBILL|SEAWAY\s*BILL|NON[- ]NEGOTIABLE WAYBILL", t):
        return "sea_waybill"
    if re.search(r"BILL OF LADING", t):
        return "bill_of_lading"
    if re.search(r"PACKING LIST|LISTA DE EMBA", t):
        return "packing_list"
    if re.search(r"COMMERCIAL INVOICE|PROFORMA INVOICE|\bINVOICE\b|FACTURA", t):
        return "invoice"
    if "PACKING" in name:
        return "packing_list"
    if "INVOICE" in name:
        return "invoice"
    return "unknown"


def _field(out: Dict[str, Any], key: str, value: Any, page: int, how: str) -> None:
    if value in (None, "", [], ()):
        return
    out.setdefault("fields", {})[key] = {"value": value, "page": page, "how": how}


# ---------------------------------------------------------------------------
# B/L and sea waybill
# ---------------------------------------------------------------------------

_SEA_LABELS: Dict[str, Sequence[str]] = {
    "shipper": ("SHIPPER", "SHIPPER/EXPORTER", "SHIPPER / EXPORTER", "EXPORTER"),
    "consignee": ("CONSIGNEE",),
    "notify": ("NOTIFY PARTY", "NOTIFY"),
    "vessel": ("VESSEL", "OCEAN VESSEL", "VESSEL NAME", "VESSEL AND VOYAGE", "VESSEL / VOYAGE"),
    "voyage": ("VOYAGE NUMBER", "VOYAGE NO", "VOY. NO", "VOYAGE"),
    "document_number": ("BILL OF LADING NUMBER", "B/L NUMBER", "B/L NO", "BILL OF LADING NO", "BL NO",
                        "SEA WAYBILL NUMBER", "SEA WAYBILL NO", "WAYBILL NUMBER", "WAYBILL NO", "SWB NO"),
    "place_of_receipt": ("PLACE OF RECEIPT",),
    "port_of_loading": ("PORT OF LOADING",),
    "port_of_discharge": ("PORT OF DISCHARGE",),
    "place_of_delivery": ("FINAL PLACE OF DELIVERY", "PLACE OF DELIVERY"),
    "freight_payable_at": ("FREIGHT TO BE PAID AT", "FREIGHT PAYABLE AT"),
}


def _clean_lines(lines: Optional[List[str]]) -> List[str]:
    return [l.strip() for l in (lines or []) if l.strip() and not re.fullmatch(r"[\W_]+", l.strip())]


def read_sea_document(data: bytes, kind: str) -> Dict[str, Any]:
    boxes, texts = open_pdf(data)
    full = "\n".join(texts)
    flat = _flat(full)
    out: Dict[str, Any] = {"kind": kind, "mode": "SEA", "pages": len(texts)}

    first = boxes[0]
    for key, labels in _SEA_LABELS.items():
        lines, lab = first_of(first, labels, "below")
        lines = _clean_lines(lines)
        if not lines:
            lines2, lab2 = first_of(first, labels, "right")
            lines, lab = _clean_lines(lines2), lab2
        if lines:
            single = key in ("vessel", "voyage", "document_number", "place_of_receipt", "port_of_loading",
                             "port_of_discharge", "place_of_delivery", "freight_payable_at")
            _field(out, key, lines[0] if single else lines, 1, f"box: {lab}")

    m = re.search(r"PLACE AND DATE OF ISSUE\s+(.+?)\s+(\d{1,2}[\s\-]+[A-Z]{3,9}[\s\-,]+\d{2,4})", full)
    if m:
        _field(out, "issue_place", m.group(1).strip(), len(texts), "label: PLACE AND DATE OF ISSUE")
        _field(out, "issue_date", written_date(m.group(2)), len(texts), "label: PLACE AND DATE OF ISSUE")
    m = re.search(r"SHIPPED ON BOARD\s+(.+?)\s+(\d{1,2}[\-\s][A-Z]{3}[A-Z]*[\-\s]\d{2,4})", flat, re.I)
    if m:
        _field(out, "shipped_on_board_date", written_date(m.group(2)), len(texts), "text: Shipped on Board")

    temps = set()
    for m in re.finditer(r"(?:carrying|set|requested)[^.]{0,40}?temperature[^.]{0,20}?(?:of|at)\s*([+-]?\d+(?:\.\d+)?)\s*(?:°|degrees?|deg|C\b|CO\b)", flat, re.I):
        temps.add(m.group(1))
    for m in re.finditer(r"SET AT\s*([+-]?\d+(?:\.\d+)?)\s*(?:°|C\b|CO\b|DEG)", flat, re.I):
        temps.add(m.group(1))
    if temps:
        _field(out, "requested_temperature_c", sorted({str(float(t)).rstrip("0").rstrip(".") if "." in t else t for t in temps}),
               1, "text: carrying / set temperature")

    for key, pat in (("total_net_kg", r"TOTAL NET WEIGHT:?\s*([\d.,]+)\s*KGS?"),
                     ("total_gross_kg", r"TOTAL GROSS WEIGHT:?\s*([\d.,]+)\s*KGS?"),
                     ("total_packages", r"\b(\d[\d,.]*)\s+(?:CARTONS|CTNS|BOXES|PACKAGES)\b")):
        m = re.search(pat, flat, re.I)
        if m:
            _field(out, key, m.group(1), 1, "text")

    # Containers: every valid container number, with the seal, type and
    # package line printed with it.
    conts: List[Dict[str, Any]] = []
    for p_idx, text in enumerate(texts, 1):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for c in containers_in(line):
                if any(x["container"] == c for x in conts):
                    continue
                entry: Dict[str, Any] = {"container": c, "page": p_idx}
                after = line[line.find(c[:4]):]
                m = re.search(r"\b(?:\d\s?[xX]\s?)?(20|40|45)\s?'?\s?(RH|RF|RA|HR|HC|RE|R1|RQ|DV|GP|HQ)\b", after)
                if m:
                    entry["type"] = m.group(0).strip()
                m = re.search(r"\b(\d{1,6})\s+(CARTONS?|CTNS?|BOXES|PALLETS?|PKGS?|PACKAGES)\b", after, re.I)
                if m:
                    entry["packages"] = f"{m.group(1)} {m.group(2).upper()}"
                nums = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*[.,]\d{3}\b|\b\d{4,6}\.\d{1,3}\b", after)
                if nums:
                    entry["gross_kg"] = nums[0]
                for look in [line] + lines[i + 1:i + 3]:
                    m = re.search(r"\bSEAL(?:\s*NO\.?|\s*#)?[:\s]+([A-Z0-9]{5,15})\b", look, re.I)
                    if m:
                        entry["seal"] = m.group(1)
                        break
                conts.append(entry)
    if conts:
        out["containers"] = conts

    m = re.search(r"\bTH:?\s*((?:\|?\s*\d{6,}[A-Z]?\s*)+)", full)
    if m:
        _field(out, "recorder_ids", re.findall(r"\d{6,}[A-Z]?", m.group(1)), 1, "text: TH")
    return out


# ---------------------------------------------------------------------------
# Air waybill (built to the IATA layout; not yet tried on a real one)
# ---------------------------------------------------------------------------

_AIR_LABELS: Dict[str, Sequence[str]] = {
    "shipper": ("SHIPPER'S NAME AND ADDRESS", "SHIPPER’S NAME AND ADDRESS", "SHIPPER"),
    "consignee": ("CONSIGNEE'S NAME AND ADDRESS", "CONSIGNEE’S NAME AND ADDRESS", "CONSIGNEE"),
    "airport_of_departure": ("AIRPORT OF DEPARTURE",),
    "airport_of_destination": ("AIRPORT OF DESTINATION",),
    "flight": ("FLIGHT/DATE", "FLIGHT / DATE", "REQUESTED FLIGHT/DATE", "FLIGHT NO"),
    "handling_information": ("HANDLING INFORMATION",),
}


def read_air_waybill(data: bytes) -> Dict[str, Any]:
    boxes, texts = open_pdf(data)
    full = "\n".join(texts)
    flat = _flat(full)
    out: Dict[str, Any] = {"kind": "air_waybill", "mode": "AIR", "pages": len(texts)}
    first = boxes[0]
    for key, labels in _AIR_LABELS.items():
        lines, lab = first_of(first, labels, "below")
        lines = _clean_lines(lines)
        if lines:
            _field(out, key, lines if key in ("shipper", "consignee", "handling_information") else lines[0], 1, f"box: {lab}")
    m = re.search(r"\b(\d{3})[\s\-](\d{4})\s?(\d{4})\b", flat)
    if m:
        _field(out, "document_number", f"{m.group(1)}-{m.group(2)}{m.group(3)}", 1, "shape: AWB number")
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*°?\s*C?\s*(?:to|-|–)\s*([+-]?\d+(?:\.\d+)?)\s*°\s*C", flat, re.I)
    if m:
        _field(out, "requested_temperature_c", [m.group(1), m.group(2)], 1, "text: temperature range")
    return out


# ---------------------------------------------------------------------------
# Invoice and packing list
# ---------------------------------------------------------------------------

def _tables(data: bytes) -> List[Tuple[int, List[List[str]]]]:
    import pdfplumber

    out = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for p_idx, page in enumerate(pdf.pages, 1):
            for t in page.extract_tables():
                out.append((p_idx, [[(c or "").replace("\n", " ").strip() for c in row] for row in t]))
    return out


def _header_index(rows: List[List[str]], *needles: str) -> Optional[Tuple[int, Dict[str, int]]]:
    """The first row that has a column for each needle, and where those columns are."""
    for i, row in enumerate(rows):
        cols: Dict[str, int] = {}
        for j, cell in enumerate(row):
            low = cell.lower()
            for n in needles:
                if n not in cols and re.search(n, low):
                    cols[n] = j
        if len(cols) == len(needles):
            return i, cols
    return None


_FRUITS = r"apples?|pears?|kiwis?|kiwifruit|grapes?|oranges?|mandarins?|plums?|cherr(?:y|ies)|blueberr(?:y|ies)|avocados?|apricots?|dragon ?fruits?"


def _describe(desc: str) -> Dict[str, Any]:
    """Variety and count from an invoice description, if it states them plainly."""
    d = re.sub(r"(?i)^cartons? of \d+(?:[.,]\d+)?\s*kgs?\s*-\s*", "", desc).strip()
    out: Dict[str, Any] = {"description": desc}
    m = re.search(r"(?:-|\bcount\b|\bsize\b)\s*(\d{2,3})\s*$", d, re.I)
    if m:
        out["count"] = m.group(1)
        d = d[:m.start()].strip(" -")
    fruit = re.search(_FRUITS, d, re.I)
    if fruit:
        out["fruit"] = fruit.group(0)
        d = (d[:fruit.start()] + d[fruit.end():]).strip(" -")
    d = re.sub(r"\s*-\s*$", "", d).strip()
    if d:
        out["variety"] = d
    m = re.search(r"(?i)cartons? of (\d+(?:[.,]\d+)?)\s*kgs?", desc)
    if m:
        out["kg_per_carton"] = m.group(1)
    return out


def read_invoice(data: bytes) -> Dict[str, Any]:
    boxes, texts = open_pdf(data)
    full = "\n".join(texts)
    out: Dict[str, Any] = {"kind": "invoice", "pages": len(texts)}
    first = boxes[0]
    for key, labels in (("invoice_number", ("INV. NUMBER", "INVOICE NUMBER", "INVOICE NO", "INVOICE #", "INV. NO", "INVOICE")),
                        ("invoice_date", ("DATE", "INVOICE DATE", "FECHA")),
                        ("incoterm", ("INCOTERM", "INCOTERMS", "TERMS OF DELIVERY"))):
        v, lab = first_of(first, labels, "right")
        if v and v[0]:
            val = v[0]
            if key == "invoice_date":
                val = written_date(val) or val
            _field(out, key, val, 1, f"label: {lab}")
    if "incoterm" not in out.get("fields", {}):
        m = re.search(r"\b(CIF|CFR|FOB|EXW|DAP|DDP|CPT|CIP|FCA)\b", full)
        if m:
            _field(out, "incoterm", m.group(1), 1, "shape: incoterm")

    lines: List[Dict[str, Any]] = []
    conts: List[Dict[str, Any]] = []
    for p_idx, rows in _tables(data):
        hit = _header_index(rows, r"carton|box|qty|quantity", r"description")
        if hit and not lines:
            i, cols = hit
            for row in rows[i + 1:]:
                qty = row[cols[r"carton|box|qty|quantity"]].replace(",", "").strip()
                desc = row[cols[r"description"]].strip()
                if re.fullmatch(r"\d{1,6}", qty) and desc and not re.match(r"(?i)total", desc):
                    lines.append({"cartons": int(qty), **_describe(desc), "page": p_idx})
        # A heading cell that is the word, not a sentence that uses it
        # ("… 21 pallets per container").
        hit = _header_index(rows, r"^\s*container\b(?!.{25,})")
        if hit:
            i, cols = hit
            head = [c.lower() for c in rows[i]]
            rec_col = next((j for j, h in enumerate(head) if re.search(r"thermo|recorder|logger|temp ?tale|\bth\b", h)), None)
            seal_col = next((j for j, h in enumerate(head) if "seal" in h), None)
            for row in rows[i + 1:]:
                found = containers_in(" ".join(row))
                if not found:
                    continue
                entry: Dict[str, Any] = {"container": found[0], "page": p_idx}
                if rec_col is not None and rec_col < len(row) and row[rec_col]:
                    entry["recorder_id"] = row[rec_col]
                if seal_col is not None and seal_col < len(row) and row[seal_col]:
                    entry["seal"] = row[seal_col]
                conts.append(entry)
    # Descriptions the table missed, laid out as text lines instead.
    if not lines:
        for m in re.finditer(r"^\s*\d{1,3}\s+(\d{1,6})\s+(Cartons? of [^\n]+?)\s+(?:USD|EUR|US\$)", full, re.M | re.I):
            lines.append({"cartons": int(m.group(1)), **_describe(m.group(2)), "page": 1})
    if lines:
        out["lines"] = lines
    if conts:
        out["containers"] = conts
    m = re.search(r"(\d[\d.,]*)\s+Cartons? on\s+(\d+)\s+pallets", _flat(full), re.I)
    if m:
        _field(out, "pallets", m.group(2), 1, "text: cartons on pallets")
    return out


def read_packing_list(data: bytes) -> Dict[str, Any]:
    boxes, texts = open_pdf(data)
    full = "\n".join(texts)
    out: Dict[str, Any] = {"kind": "packing_list", "pages": len(texts)}
    conts = containers_in(full)
    if conts:
        _field(out, "containers", conts, 1, "shape: container number")
    m = re.search(r"\bSEAL(?:\s*NO\.?|\s*#)?[:\s]+([A-Z0-9]{5,15})\b", full, re.I)
    if m:
        _field(out, "seal", m.group(1), 1, "label: SEAL")
    for key, labels in (("port_of_loading", ("PORT OF LOADING",)), ("port_of_discharge", ("PORT OF DISCHARGE",))):
        v, lab = first_of(boxes[0], labels, "right")
        if v and v[0]:
            _field(out, key, v[0], 1, f"label: {lab}")
    boxes_total = 0
    pallets = 0
    for _p, rows in _tables(data):
        hit = _header_index(rows, r"box|carton|qty")
        if not hit:
            continue
        i, cols = hit
        for row in rows[i + 1:]:
            qty = row[cols[r"box|carton|qty"]].replace(",", "").strip()
            if re.fullmatch(r"\d{1,5}", qty):
                boxes_total += int(qty)
                pallets += 1
        break
    if boxes_total:
        _field(out, "boxes", boxes_total, 1, "table: boxes column")
        _field(out, "pallets", pallets, 1, "table: rows")
    return out


# ---------------------------------------------------------------------------
# Temperature recorder
# ---------------------------------------------------------------------------

def read_recorder(data: bytes, filename: str = "") -> Dict[str, Any]:
    """
    The recorder's own summary, exactly as it prints it, and every reading.
    Dates are read in the order the file says it uses ([MM/DD/YY …]); a file
    that does not say is not guessed at.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    out: Dict[str, Any] = {"kind": "recorder", "pages": len(reader.pages)}
    pats = {
        "device_id": r"Device ID:\s*([A-Z0-9]+?)(?=\s|Log\b|$)",
        "start": r"Start Time(?:/First Point)?:\s*([\d/]+\s+[\d:]+)",
        "stop": r"Stop Time:\s*([\d/]+\s+[\d:]+)",
        "highest_c": r"Highest Temperature:\s*(-?[\d.]+)",
        "lowest_c": r"Lowest Temperature:\s*(-?[\d.]+)",
        "average_c": r"Average Temperature:\s*(-?[\d.]+)",
        "mkt_c": r"Mean Kinetic Temperature:\s*(-?[\d.]+)",
        "data_points": r"Data Point[s]?:\s*(\d+)",
        "interval": r"Log Interval(?:/cycle)?:\s*(\d+\s*(?:min|s|sec|h))",
        "trip_length": r"Trip Length:\s*(\S+)",
        "utc_offset": r"\]\s*([+-]\d{2}:\d{2})|UTC\s*([+-]\d{2}:\d{2})",
    }
    summary: Dict[str, Any] = {}
    for key, pat in pats.items():
        m = re.search(pat, text)
        if m:
            summary[key] = next(g for g in m.groups() if g)
    order = "MDY" if re.search(r"MM/DD/YY", text) else ("DMY" if re.search(r"DD/MM/YY", text) else None)
    summary["date_order"] = order
    readings: List[Tuple[str, float]] = []
    if order:
        fmt = "%m/%d/%y %H:%M:%S" if order == "MDY" else "%d/%m/%y %H:%M:%S"
        # A reading is date, time, then a temperature with its decimal. The
        # chart's axis labels are date, time, date — not readings.
        for d, tm, v in re.findall(r"(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(-?\d+\.\d+)(?![\d/])", text):
            try:
                readings.append((datetime.strptime(f"{d} {tm}", fmt).isoformat(), float(v)))
            except ValueError:
                continue
    for key in ("start", "stop"):
        if key in summary and order:
            try:
                fmt = "%m/%d/%y %H:%M:%S" if order == "MDY" else "%d/%m/%y %H:%M:%S"
                summary[key + "_iso"] = datetime.strptime(summary[key], fmt).isoformat()
            except ValueError:
                pass
    conts = containers_in(filename.upper() + " " + text[:3000])
    if conts:
        summary["container"] = conts[0]
    out["summary"] = summary
    out["readings"] = readings
    return out


# ---------------------------------------------------------------------------

def read_document(data: bytes, filename: str) -> Dict[str, Any]:
    """Tell what the document is and read it. Never raises for a bad file."""
    if not data[:5] == b"%PDF-":
        return {"kind": "unsupported", "status": "Only PDF documents can be read for now."}
    text = quick_text(data)
    kind = classify(text, filename)
    try:
        if kind == "scanned":
            return {"kind": "scanned", "status": "This PDF is a scan (no text inside), so it cannot be read yet."}
        if kind == "recorder":
            return read_recorder(data, filename)
        if kind in ("bill_of_lading", "sea_waybill"):
            return read_sea_document(data, kind)
        if kind == "air_waybill":
            return read_air_waybill(data)
        if kind == "invoice":
            return read_invoice(data)
        if kind == "packing_list":
            return read_packing_list(data)
        if kind == "other_report":
            return {"kind": "other_report", "status": "A survey report, not a shipment document; nothing is taken from it."}
        return {"kind": "unknown", "status": "Not recognised as a B/L, waybill, invoice, packing list or recorder file."}
    except Exception as exc:  # a malformed PDF must not stop the other documents
        return {"kind": kind, "status": f"Could not be read: {type(exc).__name__}"}
