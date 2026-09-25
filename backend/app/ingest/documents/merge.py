"""
The documents of one shipment, put together and checked against each other.

The B/L (or waybill) is the source for the voyage, the parties and the
containers; the invoice for what was shipped; packing lists and recorder files
for each container. Where two documents state the same thing differently — a
seal number, a container, a port — both are kept and the difference is shown,
never settled by picking one.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

TRANSPORT_KINDS = ("bill_of_lading", "sea_waybill", "air_waybill")
KIND_LABELS = {
    "bill_of_lading": "Bill of Lading", "sea_waybill": "Sea Waybill", "air_waybill": "Air Waybill",
    "invoice": "Invoice", "packing_list": "Packing List", "recorder": "Temperature recorder",
    "other_report": "Other report", "scanned": "Scanned PDF", "unknown": "Not recognised", "unsupported": "Not a PDF",
}

_COUNTRIES = (
    "South Africa", "New Zealand", "United States", "United Kingdom", "Saudi Arabia", "United Arab Emirates",
    "Brazil", "Chile", "Argentina", "Peru", "Uruguay", "Colombia", "Mexico", "USA", "Canada", "Australia",
    "Italy", "Spain", "France", "Belgium", "Netherlands", "Poland", "Greece", "Portugal", "Germany", "Turkey",
    "Egypt", "Morocco", "Iran", "Afghanistan", "China", "Thailand", "Vietnam", "Malaysia", "Indonesia",
    "Singapore", "Sri Lanka", "Bangladesh", "Nepal", "UAE", "India",
)
_INDIAN_STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
)
_KEEP_UPPER = {"SC", "SA", "LLC", "LLP", "USA", "UK", "UAE", "INC", "SRL", "SPA", "BV", "S.A.", "S.A"}
# Short words that are words, not codes: "Frutas De Santa Rita", "Sardar Ji".
_SHORT_WORDS = {"DE", "DA", "DO", "DI", "DU", "LA", "LE", "EL", "JI", "OF", "Y", "E", "AL", "EN", "ET"}


def title(s: str) -> str:
    """NAVEGANTES, SC, BRAZIL -> Navegantes, SC, Brazil. Short codes stay upper case."""
    out = []
    for w in re.split(r"(\s+|,|/|-)", s.strip()):
        if not w or re.fullmatch(r"\s+|,|/|-", w):
            out.append(w)
        elif w.upper() in _KEEP_UPPER or (len(w) <= 2 and w.isalpha() and w.upper() not in _SHORT_WORDS):
            out.append(w.upper())
        elif w.isalpha() and len(w) <= 5 and not re.search(r"[AEIOUY]", w.upper()) and w.upper() not in ("PVT", "LTD"):
            out.append(w.upper())  # an acronym: NGK, MSC
        elif any(ch.isdigit() for ch in w):
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return "".join(out)


def party(lines: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    """A name-and-address box: the name (lines before the address starts), and where it is."""
    if not lines:
        return None
    name_parts: List[str] = []
    for l in lines:
        if re.search(r"\d", l) and name_parts:
            break
        if re.search(r"\d", l):
            break
        name_parts.append(l.strip(" ,"))
        if len(name_parts) >= 3:
            break
    name = " ".join(name_parts).strip() or lines[0].strip()
    block = " ".join(lines)
    country = next((c for c in _COUNTRIES if re.search(rf"\b{re.escape(c)}\b", block, re.I)), None)
    state = next((s for s in _INDIAN_STATES if re.search(rf"\b{re.escape(s)}\b", block, re.I)), None) \
        if country and country.lower() == "india" else None
    shown = ", ".join(x for x in [title(name), state, country and title(country)] if x)
    return {"name": title(name), "state": state, "country": country and title(country), "shown": shown, "lines": lines}


def _v(doc: Dict[str, Any], key: str) -> Any:
    f = (doc.get("fields") or {}).get(key)
    return f["value"] if f else None


def _norm_seal(s: Optional[str]) -> Optional[str]:
    return re.sub(r"[^A-Z0-9]", "", s.upper()) if s else None


def merge(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    docs: [{"asset_id", "filename", ...reader output}]. Returns the shipment,
    the differences found, and which document each value came from.
    """
    notes: List[str] = []
    conflicts: List[Dict[str, Any]] = []
    transport = [d for d in docs if d.get("kind") in TRANSPORT_KINDS]
    invoices = [d for d in docs if d.get("kind") == "invoice"]
    packings = [d for d in docs if d.get("kind") == "packing_list"]
    recorders = [d for d in docs if d.get("kind") == "recorder"]
    if len(transport) > 1:
        notes.append("More than one B/L or waybill was uploaded; the first is used and the others are only checked against it.")

    ship: Dict[str, Any] = {"sources": {}}

    def put(key: str, value: Any, doc: Dict[str, Any]) -> None:
        if value in (None, "", []):
            return
        ship[key] = value
        ship["sources"][key] = doc.get("filename")

    t = transport[0] if transport else None
    if t:
        put("document_kind", t["kind"], t)
        put("mode", t.get("mode"), t)
        put("document_number", _v(t, "document_number"), t)
        put("document_date", _v(t, "issue_date") or _v(t, "shipped_on_board_date"), t)
        put("shipped_on_board_date", _v(t, "shipped_on_board_date"), t)
        put("shipper", party(_v(t, "shipper")), t)
        put("consignee", party(_v(t, "consignee")), t)
        put("notify", party(_v(t, "notify")), t)
        put("vessel", _v(t, "vessel"), t)
        put("voyage", _v(t, "voyage"), t)
        put("flight", _v(t, "flight"), t)
        put("port_of_loading", _v(t, "port_of_loading") or _v(t, "airport_of_departure"), t)
        put("port_of_discharge", _v(t, "port_of_discharge") or _v(t, "airport_of_destination"), t)
        put("place_of_delivery", _v(t, "place_of_delivery"), t)
        put("total_packages", _v(t, "total_packages"), t)
        put("total_net_kg", _v(t, "total_net_kg"), t)
        put("total_gross_kg", _v(t, "total_gross_kg"), t)
        temps = _v(t, "requested_temperature_c") or []
        if len(set(temps)) == 1 or (t.get("mode") == "AIR" and len(temps) == 2):
            put("requested_temperature_c", temps if len(temps) > 1 else temps[0], t)
        elif len(set(temps)) > 1:
            conflicts.append({"field": "Requested temperature", "values": [{"value": x, "from": t["filename"]} for x in temps]})

    # Containers: the B/L's list, completed and checked from the others.
    conts: Dict[str, Dict[str, Any]] = {}
    for c in (t or {}).get("containers", []):
        conts[c["container"]] = {**{k: v for k, v in c.items() if k != "page"}, "from": t["filename"]}
    for inv in invoices:
        for c in inv.get("containers", []):
            entry = conts.setdefault(c["container"], {"container": c["container"], "from": inv["filename"]})
            if t and c["container"] not in {x["container"] for x in t.get("containers", [])}:
                conflicts.append({"field": f"Container {c['container']}",
                                  "values": [{"value": "on the invoice", "from": inv["filename"]},
                                             {"value": "not on the B/L", "from": t["filename"]}]})
            for key in ("seal", "recorder_id"):
                if c.get(key):
                    if entry.get(key) and _norm_seal(entry[key]) != _norm_seal(c[key]):
                        conflicts.append({"field": f"{key.replace('_', ' ').title()} of {c['container']}",
                                          "values": [{"value": entry[key], "from": entry.get("from")},
                                                     {"value": c[key], "from": inv["filename"]}]})
                    else:
                        entry[key] = c[key]
    for pl in packings:
        pconts = _v(pl, "containers") or []
        seal = _v(pl, "seal")
        for cno in pconts[:1]:
            entry = conts.setdefault(cno, {"container": cno, "from": pl["filename"]})
            entry["packing_list"] = pl["filename"]
            if _v(pl, "boxes"):
                entry["boxes_packing_list"] = _v(pl, "boxes")
            if _v(pl, "pallets"):
                entry["pallets"] = _v(pl, "pallets")
            if seal:
                if entry.get("seal") and _norm_seal(entry["seal"]) != _norm_seal(seal):
                    conflicts.append({"field": f"Seal of {cno}", "values": [{"value": entry["seal"], "from": entry.get("from")},
                                                                            {"value": seal, "from": pl["filename"]}]})
                elif not entry.get("seal"):
                    entry["seal"] = seal
            pk = entry.get("packages")
            if pk and _v(pl, "boxes") and re.match(r"\d+", pk) and int(re.match(r"\d+", pk).group()) != int(_v(pl, "boxes")):
                conflicts.append({"field": f"Boxes in {cno}", "values": [{"value": pk, "from": entry.get("from")},
                                                                         {"value": str(_v(pl, "boxes")), "from": pl["filename"]}]})

    # Recorders: matched to a container by the recorder id the B/L / invoice
    # gives, or by the container number on the recorder file itself.
    by_id = {c.get("recorder_id"): cno for cno, c in conts.items() if c.get("recorder_id")}
    recs = []
    for r in recorders:
        s = r.get("summary", {})
        dev = s.get("device_id")
        cno = by_id.get(dev) or s.get("container")
        if dev and s.get("container") and by_id.get(dev) and by_id[dev] != s["container"]:
            conflicts.append({"field": f"Recorder {dev}", "values": [{"value": f"container {by_id[dev]}", "from": "invoice"},
                                                                    {"value": f"container {s['container']}", "from": r["filename"]}]})
        if cno and cno in conts:
            conts[cno]["recorder_id"] = conts[cno].get("recorder_id") or dev
        recs.append({"asset_id": r.get("asset_id"), "filename": r.get("filename"), "container": cno,
                     "summary": {k: v for k, v in s.items() if k != "container"}, "readings": len(r.get("readings") or [])})
    ids_on_bl = set(_v(t, "recorder_ids") or []) if t else set()
    for rid in sorted(ids_on_bl - {r["summary"].get("device_id") for r in recs}):
        notes.append(f"Recorder {rid} is listed on the B/L but its file was not uploaded.")
    ship["containers"] = list(conts.values())
    ship["recorders"] = recs

    # What was shipped: the invoice lines.
    lines = []
    for inv in invoices:
        for l in inv.get("lines", []):
            lines.append({k: l.get(k) for k in ("cartons", "variety", "count", "fruit", "kg_per_carton", "description")})
        if _v(inv, "invoice_number"):
            put("invoice_number", _v(inv, "invoice_number"), inv)
        if _v(inv, "invoice_date"):
            put("invoice_date", _v(inv, "invoice_date"), inv)
        if _v(inv, "incoterm"):
            put("incoterm", _v(inv, "incoterm"), inv)
    if lines:
        ship["consignment"] = lines
        total = sum(l["cartons"] for l in lines if l.get("cartons"))
        if ship.get("total_packages"):
            try:
                if int(re.sub(r"\D", "", str(ship["total_packages"]))) != total:
                    conflicts.append({"field": "Total cartons", "values": [
                        {"value": str(ship["total_packages"]), "from": ship["sources"].get("total_packages")},
                        {"value": str(total), "from": "invoice lines"}]})
            except ValueError:
                pass

    if t and packings:
        pod_pl = _v(packings[0], "port_of_discharge")
        if pod_pl and ship.get("port_of_discharge") and ship["port_of_discharge"].split(",")[0].strip().upper() not in pod_pl.upper():
            conflicts.append({"field": "Port of discharge", "values": [{"value": ship["port_of_discharge"], "from": t["filename"]},
                                                                       {"value": pod_pl, "from": packings[0]["filename"]}]})
    if not transport:
        notes.append("No B/L or waybill was uploaded, so the voyage, the parties and Sea / Air could not be read.")
    return {"shipment": ship, "conflicts": conflicts, "notes": notes}


def _kg(s: Optional[str]) -> Optional[str]:
    """148.176,000 or 148,176.000 -> 148,176 kg. As printed if the style is unclear."""
    if not s:
        return None
    t = s.strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d+", t):       # 148.176,000
        whole, frac = t.replace(".", "").split(",")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+\.\d+", t):     # 148,176.000
        whole, frac = t.replace(",", "").split(".")
    elif re.fullmatch(r"\d+\.\d{3}", t):                # 22814.400
        whole, frac = t.split(".")
    else:
        return t
    frac = frac.rstrip("0")
    return f"{int(whole):,}" + (f".{frac}" if frac else "") + " kg"


def particulars(ship: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    The Particulars rows the documents can fill, worded as the client's
    reports word them. Only rows with something to show are returned.
    """
    rows: List[Tuple[str, Optional[str], str]] = []
    src = ship.get("sources", {})
    if ship.get("shipper"):
        rows.append(("Exporter / Shipper", ship["shipper"]["shown"], src.get("shipper")))
    if ship.get("consignee"):
        rows.append(("Consignee", ship["consignee"]["shown"], src.get("consignee")))
    if ship.get("document_number"):
        dated = f" dated {ship['document_date']}" if ship.get("document_date") else ""
        rows.append(("Bill of Lading / AWB No.", f"{ship['document_number']}{dated}", src.get("document_number")))
    if ship.get("invoice_number"):
        dated = f" dated {ship['invoice_date']}" if ship.get("invoice_date") else ""
        rows.append(("Invoice No.", f"{ship['invoice_number']}{dated}", src.get("invoice_number")))
    conts = ship.get("containers") or []
    if conts:
        n = len(conts)
        size = next((re.search(r"(20|40|45)", c.get("type", "")).group(1) for c in conts if re.search(r"(20|40|45)", c.get("type", ""))), None)
        kind = f" ({n} × {size}' Reefer{'s' if n > 1 else ''})" if size else ""
        rows.append(("Container / Carriage Unit", ", ".join(c["container"] for c in conts) + kind, src.get("containers") or conts[0].get("from")))
        seals = [f"{c['container']}: {c['seal']}" if n > 1 else c["seal"] for c in conts if c.get("seal")]
        if seals:
            rows.append(("Seal No.", ", ".join(seals), conts[0].get("from")))
    if ship.get("vessel"):
        voy = f" Voy No. {ship['voyage']}" if ship.get("voyage") else ""
        rows.append(("Carrying Vessel / Flight", f"“{ship['vessel']}”{voy}", src.get("vessel")))
    elif ship.get("flight"):
        rows.append(("Carrying Vessel / Flight", ship["flight"], src.get("flight")))
    if ship.get("port_of_loading"):
        rows.append(("Port of Loading", title(ship["port_of_loading"]), src.get("port_of_loading")))
    if ship.get("port_of_discharge"):
        rows.append(("Port of Discharge", title(ship["port_of_discharge"]), src.get("port_of_discharge")))
    lines = ship.get("consignment") or []
    if lines:
        total = sum(l["cartons"] for l in lines if l.get("cartons"))
        parts = []
        for l in lines:
            what = " ".join(x for x in [l.get("variety"), f"Count {l['count']}" if l.get("count") else None] if x) or l.get("description", "")
            parts.append(f"{what}: {l['cartons']:,} boxes")
        fruit = next((l.get("fruit") for l in lines if l.get("fruit")), None)
        head = f"Fresh {title(fruit)} — {total:,} boxes" if fruit else f"{total:,} boxes"
        rows.append(("Cargo Declared", head + "; " + "; ".join(parts), "invoice"))
    net, gross = _kg(ship.get("total_net_kg")), _kg(ship.get("total_gross_kg"))
    if net or gross:
        rows.append(("Net / Gross Weight", " / ".join(x for x in [net and f"Net {net}", gross and f"Gross {gross}"] if x),
                     src.get("total_net_kg") or src.get("total_gross_kg")))
    return [{"label": l, "value": v, "source": s} for l, v, s in rows if v]
