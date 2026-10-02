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
    "other_report": "Other report", "scanned": "Scanned pages", "unknown": "Not recognised", "unsupported": "Not a PDF",
    # general cargo
    "insurance": "Insurance certificate", "bill_of_entry": "Bill of Entry", "shipping_bill": "Shipping Bill",
    "eir": "EIR", "container_tracking": "Container tracking", "weight_slip": "Weight slips",
    "lorry_receipt": "Lorry receipt / consignment note", "letter_of_protest": "Letter of protest",
    "booking_confirmation": "Booking confirmation", "certificate_of_origin": "Certificate of origin",
    "sales_contract": "Sales contract", "inspection_certificate": "Inspection certificate",
    "proforma_invoice": "Proforma invoice", "other_certificate": "Certificate", "email": "Email",
    "exif_sheet": "Photo EXIF sheet",
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
# Short words that are words, not codes: "Frutas De La Sierra", "Ram Ji Traders".
_SHORT_WORDS = {"DE", "DA", "DO", "DI", "DU", "LA", "LE", "EL", "JI", "OF", "Y", "E", "AL", "EN", "ET", "TO"}


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
    if not lines:
        for pl in packings:
            for l in pl.get("lines", []):
                lines.append({k: l.get(k) for k in ("cartons", "variety", "count", "fruit", "kg_per_carton", "description", "container")})
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
    _merge_general_cargo(docs, ship, conts, conflicts, put)
    ship["containers"] = list(conts.values())
    if not transport:
        notes.append("No B/L or waybill was uploaded, so the voyage, the parties and Sea / Air could not be read.")
    return {"shipment": ship, "conflicts": conflicts, "notes": notes}


def _same_or_range(dates: List[str]) -> Optional[str]:
    """One date when all containers share it, else "first – last" as read."""
    ds = [d for d in dates if d]
    if not ds:
        return None
    uniq = list(dict.fromkeys(ds))
    return uniq[0] if len(uniq) == 1 else f"{uniq[0]} – {uniq[-1]}"


def _merge_general_cargo(docs: List[Dict[str, Any]], ship: Dict[str, Any], conts: Dict[str, Dict[str, Any]],
                         conflicts: List[Dict[str, Any]], put) -> None:
    """
    What the general cargo documents add: the insurance, customs, the
    invoice value, and for each container its packing-list weights, the
    B/L tare, the seal on the bill of entry, the EIR and the tracking dates.
    Where the bill of entry's seal differs from the B/L's, both are shown.
    """
    for d in docs:
        kind = d.get("kind")
        if kind == "insurance":
            for key in ("insurer", "policy_number", "certificate_number", "insured_value", "assured"):
                put(key, _v(d, key), d)
        elif kind == "invoice":
            put("invoice_value", _v(d, "invoice_value"), d)
        elif kind in ("bill_of_entry", "shipping_bill"):
            no, date = (_v(d, "be_number"), _v(d, "be_date")) if kind == "bill_of_entry" else (_v(d, "sb_number"), _v(d, "sb_date"))
            if no:
                put(kind, {"number": no, "date": date}, d)
            put("customs_broker", _v(d, "customs_broker"), d)
            if kind == "bill_of_entry":
                put("inward_date", _v(d, "inward_date"), d)
                put("out_of_charge_date", _v(d, "ooc_date"), d)
            for c in d.get("containers") or []:
                entry = conts.setdefault(c["container"], {"container": c["container"], "from": d.get("filename")})
                if entry.get("seal") and _norm_seal(entry["seal"]) != _norm_seal(c["seal"]):
                    conflicts.append({"field": f"Seal of {c['container']}",
                                      "values": [{"value": entry["seal"], "from": entry.get("from")},
                                                 {"value": c["seal"], "from": d.get("filename")}]})
                elif not entry.get("seal"):
                    entry["seal"] = c["seal"]
        elif kind == "packing_list":
            for w in d.get("container_weights") or []:
                entry = conts.setdefault(w["container"], {"container": w["container"], "from": d.get("filename")})
                for k in ("net_kg", "gross_kg"):
                    if w.get(k):
                        entry[f"pl_{k}"] = w[k]
            if not ship.get("total_net_kg"):
                put("total_net_kg", _v(d, "total_net_kg"), d)
            if not ship.get("total_gross_kg"):
                put("total_gross_kg", _v(d, "total_gross_kg"), d)
        elif kind == "eir":
            for e in d.get("eirs") or []:
                entry = conts.setdefault(e["container"], {"container": e["container"], "from": d.get("filename")})
                entry["eir"] = {k: e.get(k) for k in ("out", "in", "movement", "destination", "seal", "truck", "remarks") if e.get(k)}
        elif kind == "container_tracking":
            for t in d.get("tracking") or []:
                entry = conts.setdefault(t["container"], {"container": t["container"], "from": d.get("filename")})
                entry["tracking"] = {k: t.get(k) for k in ("loaded_on_board", "arrival", "discharged", "to_consignee",
                                                           "status", "status_date", "status_place") if t.get(k)}
    # For the whole shipment, when the containers agree.
    tracked = [c.get("tracking") or {} for c in conts.values()]
    for key, field in (("loaded_on_board_date", "loaded_on_board"), ("arrival_date", "arrival"),
                       ("discharged_date", "discharged"), ("delivered_date", "to_consignee")):
        v = _same_or_range([t.get(field) for t in tracked])
        if v:
            ship[key] = v
    dests = [re.sub(r"\s+", " ", (c.get("eir") or {}).get("destination", "")).strip() for c in conts.values()]
    dests = [x for x in dests if x]
    if dests:
        ship["cfs"] = max(set(dests), key=dests.count)


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


def particulars(ship: Dict[str, Any], general_cargo: bool = False) -> List[Dict[str, Any]]:
    """
    The Particulars rows the documents can fill, worded as the client's
    reports word them. Only rows with something to show are returned. A
    general cargo cover has more fields (the insurance, customs, the dates of
    the voyage), named as his general cargo reports name them.
    """
    rows: List[Tuple[str, Optional[str], str]] = []
    src = ship.get("sources", {})
    if general_cargo:
        if ship.get("insurer"):
            rows.append(("Insurers", ship["insurer"], src.get("insurer")))
        if ship.get("policy_number"):
            rows.append(("Policy No.", ship["policy_number"], src.get("policy_number")))
        if ship.get("certificate_number"):
            rows.append(("Certificate No.", ship["certificate_number"], src.get("certificate_number")))
        if ship.get("insured_value"):
            rows.append(("Insured Value", ship["insured_value"], src.get("insured_value")))
        if ship.get("assured"):
            rows.append(("Assured", title(ship["assured"]), src.get("assured")))
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
        if ship.get("invoice_value"):
            rows.append(("Invoice Value", ship["invoice_value"], src.get("invoice_value")))
        conts = ship.get("containers") or []
        if conts:
            n = len(conts)
            size = next((re.search(r"(20|40|45)", c.get("type", "")).group(1) for c in conts if re.search(r"(20|40|45)", c.get("type", ""))), None)
            kind = f" ({n} × {size}')" if size else ""
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
        for key, label in (("bill_of_entry", "Bill of Entry No. & Date"), ("shipping_bill", "Shipping Bill No. & Date")):
            doc = ship.get(key)
            if doc:
                rows.append((label, doc["number"] + (f" dated {doc['date']}" if doc.get("date") else ""), src.get(key)))
        for key, label in (("arrival_date", "Date of Arrival"), ("discharged_date", "Discharged Date"),
                           ("delivered_date", "Cargo Departed from CFS")):
            if ship.get(key):
                rows.append((label, ship[key], "container tracking"))
        return [{"label": l, "value": v, "source": s} for l, v, s in rows if v]

    # Perishable Fruits: 14-field layout matching latest 2026 reports
    fruit_rows: List[Dict[str, Any]] = []
    # 1. Policy No.
    fruit_rows.append({
        "label": "Policy No.",
        "value": ship.get("policy_number") or "Information not furnished",
        "source": src.get("policy_number"),
    })
    # 2. Insurer
    fruit_rows.append({
        "label": "Insurer",
        "value": ship.get("insurer") or "Information not furnished",
        "source": src.get("insurer"),
    })
    # 3. Sum Insured
    fruit_rows.append({
        "label": "Sum Insured",
        "value": ship.get("insured_value") or "Information not furnished",
        "source": src.get("insured_value"),
    })
    # 4. Shipper
    shipper_val = ship["shipper"]["shown"] if ship.get("shipper") else "[Shipper Name, Address, Country]"
    fruit_rows.append({
        "label": "Shipper",
        "value": shipper_val,
        "source": src.get("shipper"),
    })
    # 5. Consignees
    consignee_val = ship["consignee"]["shown"] if ship.get("consignee") else "[Consignee Name, Address, City, India]"
    fruit_rows.append({
        "label": "Consignees",
        "value": consignee_val,
        "source": src.get("consignee"),
    })
    # 6. Comm. Invoice No.
    inv_no = ship.get("invoice_number")
    if inv_no:
        dated = f" dated {ship['invoice_date']}" if ship.get("invoice_date") else ""
        fruit_rows.append({
            "label": "Comm. Invoice No.",
            "value": f"{inv_no}{dated}",
            "source": src.get("invoice_number"),
        })
    else:
        fruit_rows.append({
            "label": "Comm. Invoice No.",
            "value": "Information not furnished",
            "source": None,
        })
    # 7. Invoice Value
    fruit_rows.append({
        "label": "Invoice Value",
        "value": ship.get("invoice_value") or "Information not furnished",
        "source": src.get("invoice_value"),
    })
    # 8. Bill of Lading No.
    bl_no = ship.get("document_number")
    dated = f" dated {ship['document_date']}" if ship.get("document_date") else ""
    fruit_rows.append({
        "label": "Bill of Lading No.",
        "value": f"{bl_no}{dated}" if bl_no else "[B/L No. dated Date]",
        "source": src.get("document_number"),
    })
    # 9. Vessel Name
    vessel = ship.get("vessel") or ship.get("flight")
    voy = f" Voyage No. {ship['voyage']}" if ship.get("voyage") else ""
    fruit_rows.append({
        "label": "Vessel Name",
        "value": f"“{vessel}”{voy}" if vessel else "[Vessel Name / Flight No.]",
        "source": src.get("vessel"),
    })
    # 10. Voyage as per B/L
    pol = title(ship["port_of_loading"]) if ship.get("port_of_loading") else "[Port of Loading]"
    pod = title(ship["port_of_discharge"]) if ship.get("port_of_discharge") else "[Port of Discharge]"
    fruit_rows.append({
        "label": "Voyage as per B/L",
        "value": f"{pol} to {pod}",
        "source": src.get("port_of_loading"),
    })
    # 11. Date of arrival
    arr = ship.get("arrival_date") or "[Date of arrival at Terminal]"
    fruit_rows.append({
        "label": "Date of arrival",
        "value": arr,
        "source": src.get("arrival_date"),
    })
    # 12. Container Nos.
    conts = ship.get("containers") or []
    if conts:
        n = len(conts)
        size = next((re.search(r"(20|40|45)", c.get("type", "")).group(1) for c in conts if re.search(r"(20|40|45)", c.get("type", ""))), "40")
        types = next((c.get("type") for c in conts if c.get("type")), f"{size}RH")
        kind = f" ({n}x{size}' Reefer)" if n > 1 else f" (1x{size}' Reefer / {types})"
        c_label = "Container Nos." if n > 1 else "Container No."
        c_text = " & ".join(c["container"] for c in conts) if n == 2 else ", ".join(c["container"] for c in conts)
        fruit_rows.append({
            "label": c_label,
            "value": f"{c_text}{kind}",
            "source": conts[0].get("from"),
        })
    else:
        fruit_rows.append({
            "label": "Container No.",
            "value": "[Container No.] (1x40' Reefer / 40RH)",
            "source": None,
        })
    # 13. Consignment
    lines = ship.get("consignment") or []
    fruit_name = next((l.get("fruit") for l in lines if l.get("fruit")), "")
    fruit_col = f"Fresh {title(fruit_name)} Variety" if fruit_name else "Commodity / Variety"
    net = _kg(ship.get("total_net_kg"))
    gross = _kg(ship.get("total_gross_kg"))
    if len(conts) > 1:
        for c in conts:
            cno = c.get("container", "")
            c_lines = [l for l in lines if l.get("container") == cno] or lines
            sub_rows = []
            c_tot = 0
            for l in c_lines:
                var = l.get("variety") or l.get("description") or f"Fresh {title(fruit_name)}"
                cnt = str(l.get("count") or l.get("size") or "-")
                bx = l.get("cartons") or 0
                if isinstance(bx, int):
                    c_tot += bx
                    bx_str = f"{bx:,}"
                else:
                    bx_str = str(bx)
                sub_rows.append({"col1": var, "col2": cnt, "col3": bx_str})
            c_gross = c.get("gross_kg") or ship.get("total_gross_kg") or ""
            footer = f"Total: {c_tot:,} boxes" + (f" (Gross Weight: {c_gross} kg)" if c_gross else "")
            fruit_rows.append({
                "label": f"Consignment # {cno}",
                "type": "table",
                "headers": ["Commodity", "Sizes", "Total Boxes"],
                "rows": sub_rows or [{"col1": f"Fresh {title(fruit_name)}", "col2": "-", "col3": "-"}],
                "footer": footer,
                "source": "invoice / packing list",
                "value": [footer],
            })
    else:
        sub_rows = []
        tot = 0
        for l in lines:
            var = l.get("variety") or l.get("description") or f"Fresh {title(fruit_name)}"
            cnt = str(l.get("count") or l.get("size") or "-")
            bx = l.get("cartons") or 0
            if isinstance(bx, int):
                tot += bx
                bx_str = f"{bx:,}"
            else:
                bx_str = str(bx)
            sub_rows.append({"col1": var, "col2": cnt, "col3": bx_str})
        weights = " / ".join(x for x in [net and f"Net Weight: {net}", gross and f"Gross Weight: {gross}"] if x)
        pallets = next((c.get("pallets") for c in conts if c.get("pallets")), ship.get("pallets"))
        pallets_str = f" on {pallets} Pallets" if pallets else ""
        footer = f"Total: {tot:,} boxes{pallets_str}" + (f" {weights}" if weights else "")
        fruit_rows.append({
            "label": "Consignment",
            "type": "table",
            "headers": [fruit_col, "Count / Size", "Total Boxes"],
            "rows": sub_rows or [{"col1": f"Fresh {title(fruit_name)}", "col2": "-", "col3": "-"}],
            "footer": footer,
            "source": "invoice / packing list",
            "value": [footer],
        })
    # 14. Nature of Packing
    packing_text = ship.get("nature_of_packing")
    if not packing_text:
        fn = fruit_name.lower()
        if "apple" in fn:
            packing_text = "Fresh Apples packed in slotted cardboard trays; such 4/5 trays packed inside the ventilated polyethylene sheet and further packed into a ventilated 3-ply corrugated cardboard box. Such boxes were reportedly stuffed inside a 40' Reefer container."
        elif "pear" in fn:
            packing_text = "Fresh Pear fruits packed in slotted EPS trays; such 4 trays packed inside the ventilated polyethylene sheet and further packed into a ventilated 3-ply corrugated cardboard box. Such boxes reportedly placed onto pallets and corners protected with cardboard sheet and fastened with nylon straps at equal intervals."
        elif "mandarin" in fn or "orange" in fn or "citrus" in fn:
            packing_text = "Fresh Mandarin fruits packed in a open top ventilated corrugated cardboard box. Such cartons were reportedly placed on wooden pallets and secured with plastic straps. Such various pallets stuffed inside 40' Reefer container."
        elif "grape" in fn:
            packing_text = "Bunch of fresh grapes packed in non-woven bag (Uvasys-used to prevent post-harvest fungal decay during transportation and storage), such bag packed inside ventilated plastic box. Stuffed inside 40' Reefer container."
        elif "plum" in fn:
            packing_text = "Fresh Plum packed in plastic crate / boxes, stuffed inside 40' High Cube Reefer Containers."
        else:
            packing_text = f"Fresh {title(fruit_name)} fruits packed in standard export packaging, stuffed inside 40' Reefer container." if fruit_name else "[Packaging details as per packing list / survey]"
    if net or gross:
        w_line = " / ".join(x for x in [net and f"Net Weight: {net}", gross and f"Gross Weight: {gross}"] if x)
        if packing_text.strip() == "[Packaging details as per packing list / survey]":
            packing_text = w_line
        else:
            packing_text += f"\n{w_line}."
    fruit_rows.append({
        "label": "Nature of Packing",
        "value": packing_text,
        "source": "packing list",
    })
    return fruit_rows
