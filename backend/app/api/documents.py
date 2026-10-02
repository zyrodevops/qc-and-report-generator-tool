"""
Shipment documents: upload, read, and — once the surveyor has checked them —
fill the report.

POST /api/reports/{id}/documents/read   files -> what each document says, put
                                        together and checked; nothing is saved
                                        into the report yet
POST /api/reports/{id}/documents/apply  the surveyor's confirmed values ->
                                        Particulars, Sea / Air, the requested
                                        temperature and the recorders

The files themselves are kept (as the photos are), so the recorder readings
can be drawn later and the documents can be attached.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.assets import _get_report_or_404
from app.config import settings
from app.core.auth import get_current_actor
from app.database import get_db
from app.ingest.documents.merge import KIND_LABELS, merge, particulars
from app.ingest.documents.readers import read_file
from app.models.asset import Asset
from app.services.audit import AuditService

router = APIRouter()

# The documents' particulars under the names a general cargo cover uses
# (as the client's general cargo covers name them).
GC_COVER_LABEL = {
    "Exporter / Shipper": "Shipper",
    "Consignee": "Consignees",
    "Bill of Lading / AWB No.": "Bill of Lading No. & Date",
    "Invoice No.": "Invoice No. & Date",
    "Container / Carriage Unit": "Container Nos.",
    "Seal No.": "Seal Nos.",
    "Carrying Vessel / Flight": "Vessel / Voyage",
    "Cargo Declared": "Consignment",
}

MAX_FILES = 40
MAX_BYTES = 40 * 1024 * 1024


def _store(report_id: str, data: bytes, filename: str) -> Dict[str, Any]:
    sha = hashlib.sha256(data).hexdigest()
    folder = Path(settings.UPLOAD_DIR) / report_id / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha[:16]}.pdf"
    if not path.exists():
        path.write_bytes(data)
    return {"sha256": sha, "path": str(path), "folder": folder}


@router.post("/{report_id}/documents/read")
async def read_documents(
    report_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    report = await _get_report_or_404(report_id, db)
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_FILES} documents at a time.")

    docs: List[Dict[str, Any]] = []
    for up in files:
        data = await up.read()
        name = up.filename or "document.pdf"
        if not data:
            docs.append({"filename": name, "kind": "unsupported", "status": "The file is empty."})
            continue
        if len(data) > MAX_BYTES:
            docs.append({"filename": name, "kind": "unsupported", "status": "The file is larger than 40 MB."})
            continue
        # A bundle comes back as its documents, each saying which pages it is.
        results = read_file(data, name)
        stored = _store(report_id, data, name)
        # One record per report: the same file uploaded to two reports is two
        # documents (it was one, and the second report could not open it).
        asset_id = f"doc_{stored['sha256'][:24]}_{str(report.id).replace('-', '')[:12]}"
        derived: Dict[str, Any] = {"filename": name, "kind": results[0].get("kind") if len(results) == 1 else "bundle",
                                   "parts": [{"kind": r.get("kind"), "pages": r.get("page_numbers")} for r in results]}
        for result in results:
            readings = result.pop("readings", None)
            if readings:
                rpath = stored["folder"] / f"{stored['sha256'][:16]}.readings.json"
                rpath.write_text(json.dumps(readings), encoding="utf-8")
                derived["readings"] = str(rpath)
                result["readings"] = readings  # for merge's count only
            if result.get("kind") == "recorder":
                from app.render.recorder_chart import extract_recorder_graph
                graph_bytes = extract_recorder_graph(data)
                if graph_bytes:
                    gpath = stored["folder"] / f"{stored['sha256'][:16]}.graph.png"
                    gpath.write_bytes(graph_bytes)
                    derived["graph"] = str(gpath)
        existing = await db.get(Asset, asset_id)
        if existing is None:
            db.add(Asset(id=asset_id, report_id=report.id, kind="document", sha256=stored["sha256"],
                         original_path=stored["path"], derived_paths=derived, exif={}))
        else:
            existing.derived_paths = derived
        for result in results:
            shown = f"{name} ({result['page_range']})" if result.get("page_range") else name
            docs.append({"asset_id": asset_id, "filename": shown, "file": name, **result})

    await AuditService.record_async(
        session=db, actor=actor, action="DOCUMENTS_READ", report_id=report.id, path="documents",
        before=None, after={"files": [d["filename"] for d in docs]},
    )
    await db.commit()

    merged = merge(docs)
    report_mode = ((report.block_state or {}).get("transport") or {}).get("mode")
    doc_mode = merged["shipment"].get("mode")
    if report_mode and doc_mode and report_mode != doc_mode:
        merged["notes"].append(
            f"This report was created as {report_mode}, but the {KIND_LABELS.get(merged['shipment'].get('document_kind'), 'document')} "
            f"is for a {doc_mode} shipment. Check the report type."
        )
    summary = []
    for d in docs:
        entry = {"asset_id": d.get("asset_id"), "filename": d["filename"], "kind": d.get("kind"),
                 "kind_label": KIND_LABELS.get(d.get("kind"), d.get("kind")), "status": d.get("status"),
                 "pages": d.get("page_numbers"), "scan": bool(d.get("scan"))}
        if d.get("kind") == "recorder":
            entry["summary"] = d.get("summary")
            entry["readings"] = len(d.get("readings") or [])
        else:
            entry["fields"] = {k: v.get("value") for k, v in (d.get("fields") or {}).items()}
        summary.append(entry)
    gc = ((report.block_state or {}).get("metadata") or {}).get("report_kind") == "general_cargo"
    return {
        "documents": summary,
        "shipment": merged["shipment"],
        "particulars": particulars(merged["shipment"], general_cargo=gc),
        "conflicts": merged["conflicts"],
        "notes": merged["notes"],
    }


@router.post("/{report_id}/documents/read-scan")
async def read_scan(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Scanned weight slips or lorry receipts, read by the online reader
    (app/services/scan_reader.py). Only a proposal: nothing is written to the
    report here; the surveyor checks every value first.
    payload: {"asset_id", "pages": [1, 2, ...], "kind": "weight_slip" | "lorry_receipt"}
    """
    from app.ingest.documents.pages import page_images
    from app.services.scan_reader import read_scans

    report = await _get_report_or_404(report_id, db)
    asset = await db.get(Asset, payload.get("asset_id"))
    if asset is None or str(asset.report_id) != str(report.id) or asset.kind != "document":
        raise HTTPException(status_code=404, detail="No such document in this report.")
    base = Path(settings.UPLOAD_DIR).resolve()
    path = Path(asset.original_path).resolve()
    if base not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="The document file is missing.")
    pages = [int(p) for p in payload.get("pages") or [] if str(p).isdigit()][:60]
    images = page_images(path.read_bytes(), pages)
    result = await read_scans(str(payload.get("kind") or ""), images)
    await AuditService.record_async(
        session=db, actor=actor, action="DOCUMENTS_SCAN_READ", report_id=report.id, path="documents",
        before=None, after={"asset_id": asset.id, "pages": pages, "kind": payload.get("kind"), "model": result.get("model")},
    )
    await db.commit()
    return result


@router.get("/{report_id}/recorders/{asset_id}/chart.png")
async def recorder_chart(
    report_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
):
    """The graph of one recorder's readings, as the report will print it."""
    from fastapi.responses import Response
    from app.render.recorder_chart import chart_for, extract_recorder_graph

    report = await _get_report_or_404(report_id, db)
    block = next((b for b in (report.block_state or {}).get("blocks", []) if b.get("type") == "temperature_recorders"), None)
    rec = next((r for r in (block or {}).get("recorders", []) if r.get("asset_id") == asset_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="No such recorder in this report.")
    png = chart_for(rec, block.get("set_point_c"))
    if not png:
        asset = await db.get(Asset, asset_id)
        if asset and asset.original_path and Path(asset.original_path).exists():
            png = extract_recorder_graph(asset.original_path)
    if not png:
        raise HTTPException(status_code=404, detail="This recorder has no readings to draw.")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


def _fill_seals_table(state: Dict[str, Any], ship: Dict[str, Any]) -> None:
    """The containers and their seal numbers as per the documents, into the seals table if it is still empty."""
    table = next((b for b in state.get("blocks", []) if b.get("type") == "gc_table" and b.get("kind") == "seals"), None)
    if table is None or any(any(str(v or "").strip() for v in r.values()) for r in table.get("rows") or []):
        return
    rows = [{"container": c["container"], "size": c.get("type") or "", "seal_doc": c.get("seal") or "", "seal_found": ""}
            for c in ship.get("containers") or [] if c.get("container")]
    if rows:
        table["rows"] = rows


def tare_is_of(slip_tare: Any, bl_tare: Any) -> str:
    """
    Whose tare a weight slip's tare is: the container's when it is the B/L's
    tare (within 50 kg), or, without one, when it is a container's size
    (under 5 t); the truck's otherwise. Only a first guess: the surveyor sets it.
    """
    def kg(v: Any):
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None

    t, b = kg(slip_tare), kg(bl_tare)
    if t is None:
        return "truck"
    if b is not None:
        return "container" if abs(t - b) <= 50 else "truck"
    return "container" if t < 5000 else "truck"


def _apply_weight_slips(state: Dict[str, Any], slips: List[Dict[str, Any]], shipment_containers: List[Dict[str, Any]]) -> None:
    """
    Weight slips the surveyor checked, into the survey paragraphs of their
    containers: weighbridge, slip no. and date, gross, and the tare as the
    container's or the truck's, as the surveyor set it ("tare_of"). A
    paragraph is added for a container that has none. Figures the surveyor
    already typed are not replaced.
    """
    if not slips:
        return
    from app.seeds.general_cargo import survey_unit

    blocks = state.get("blocks", [])
    containers = {c["container"]: c for c in shipment_containers or [] if c.get("container")}
    for s in slips:
        cno = str(s.get("container_no") or "").replace(" ", "").upper()
        if not cno:
            continue
        unit = next((b for b in blocks if b.get("type") == "survey_unit" and str(b.get("container") or "").replace(" ", "").upper() == cno), None)
        if unit is None:
            units = [b for b in blocks if b.get("type") == "survey_unit"]
            empty = next((u for u in units if not u.get("container") and not (u.get("additional_text") or "").strip()
                          and not u.get("weights")), None)
            if empty is not None:
                unit = empty
                unit["container"] = cno
            else:
                n = 1 + max([int(str(u["id"]).rsplit("_", 1)[-1]) for u in units if str(u.get("id", "")).rsplit("_", 1)[-1].isdigit()] or [0])
                unit = survey_unit(n, container=cno)
                at = (blocks.index(units[-1]) + 1) if units else len(blocks)
                blocks.insert(at, unit)
        w = dict(unit.get("weights") or {})
        doc = containers.get(cno) or {}
        tare_of = s.get("tare_of") or tare_is_of(s.get("tare_kg"), doc.get("tare_kg"))
        slip_tare = ("tare_container" if tare_of == "container" else "tare_truck", s.get("tare_kg"))
        for key, value in (("weighbridge", s.get("weighbridge")), ("slip_no", s.get("slip_no")), ("date", s.get("date")),
                           ("gross", s.get("gross_kg")), slip_tare,
                           ("tare_container", doc.get("tare_kg")),
                           ("declared", doc.get("pl_gross_kg") or doc.get("gross_kg"))):
            if value not in (None, "") and not str(w.get(key) or "").strip():
                w[key] = str(value)
        w.setdefault("basis", "Packing List" if doc.get("pl_gross_kg") else "B/L")
        unit["weights"] = w
    state["blocks"] = blocks


@router.post("/{report_id}/documents/apply")
async def apply_documents(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Write the values the surveyor confirmed. Only rows he kept are written;
    a Particulars row is replaced, never merged with what was there.
    """
    report = await _get_report_or_404(report_id, db)
    rows_in: List[Dict[str, Any]] = [
        r for r in (payload.get("particulars") or [])
        if str(r.get("value", "")).strip() or r.get("type") == "table" or "headers" in r or "rows" in r
    ]
    ship: Dict[str, Any] = payload.get("shipment") or {}

    state = dict(report.block_state or {})
    blocks = list(state.get("blocks", []))
    gc = (state.get("metadata") or {}).get("report_kind") == "general_cargo"
    def _is_consignment(row: Dict[str, Any]) -> bool:
        lbl = str(row.get("label", "")).strip().lower()
        return lbl.startswith("consignment") or row.get("type") == "table" or "headers" in row

    def _matches_label(r_lbl: str, t_lbl: str) -> bool:
        r_clean = r_lbl.strip().lower()
        t_clean = t_lbl.strip().lower()
        if r_clean == t_clean:
            return True
        if r_clean in ("container no.", "container nos.") and t_clean in ("container no.", "container nos."):
            return True
        return False

    for b in blocks:
        if b.get("type") != "particulars":
            continue
        rows = list(b.get("rows", []))

        # Partition incoming rows into consignment tables and regular particulars fields
        consignment_in = [r for r in rows_in if _is_consignment(r)]
        other_in = [r for r in rows_in if not _is_consignment(r)]

        # 1. Update or append non-consignment fields
        for r in other_in:
            label = str(r["label"]).strip()
            if gc:
                # A general cargo cover names these fields its own way.
                label = GC_COVER_LABEL.get(label, label)
                if label == "Bill of Lading No. & Date" and str(r.get("value", "")).upper().startswith(("AWB", "AIR")):
                    label = "Air Waybill No. & Date"
            val = r.get("value", "")
            val_list = val if isinstance(val, list) else [str(val).strip()]
            new = {"label": label, "value": val_list, "provenance": "document_verified"}
            hit = next((row for row in rows if _matches_label(str(row.get("label", "")), label)), None)
            if hit is not None:
                rows[rows.index(hit)] = {**hit, **new}
            else:
                rows.append(new)

        # 2. Update consignment tables
        # When consignment table(s) are present in the documents (whether 1 or multiple containers),
        # they must replace any existing placeholder consignment rows and be sequentially stacked
        # immediately before "Nature of Packing".
        if consignment_in:
            formatted_consignment: List[Dict[str, Any]] = []
            for r in consignment_in:
                label = str(r["label"]).strip()
                headers = r.get("headers") or ["Commodity", "Sizes", "Total Boxes"]
                headers = [str(h).replace("Toal Boxes", "Total Boxes") for h in headers]
                sub_rows = r.get("rows") or r.get("items") or []
                footer = r.get("footer", "")
                val = r.get("value") or ([footer] if footer else [])
                val_list = val if isinstance(val, list) else [str(val).strip()]
                formatted_consignment.append({
                    **r,
                    "label": label,
                    "type": "table",
                    "headers": headers,
                    "rows": sub_rows,
                    "footer": footer,
                    "value": val_list,
                    "provenance": "document_verified",
                })

            # Strip all previous consignment rows (placeholders or old container tables)
            new_rows = [row for row in rows if not _is_consignment(row)]

            # Locate insertion point directly before Nature of Packing in new_rows
            packing_idx = next((i for i, row in enumerate(new_rows) if "nature of packing" in str(row.get("label", "")).strip().lower()), len(new_rows))

            new_rows[packing_idx:packing_idx] = formatted_consignment
            rows = new_rows

        b["rows"] = rows
        break
    state["blocks"] = blocks

    transport = dict(state.get("transport") or {})
    conts = [c.get("container") for c in ship.get("containers") or [] if c.get("container")]
    for key, value in (("container_no", ", ".join(conts)), ("vessel", ship.get("vessel") or ship.get("flight")),
                       ("voyage", ship.get("voyage")), ("origin", ship.get("port_of_loading")),
                       ("destination", ship.get("port_of_discharge"))):
        if value:
            transport[key] = value
    if ship.get("document_number"):
        transport["document"] = {"kind": "AIR_WAYBILL" if ship.get("mode") == "AIR" else "BILL_OF_LADING",
                                 "number": ship["document_number"]}
    state["transport"] = transport

    meta = dict(state.get("metadata") or {})
    meta["shipment"] = {
        "document_kind": ship.get("document_kind"),
        "document_number": ship.get("document_number"),
        "mode": ship.get("mode"),
        "requested_temperature_c": ship.get("requested_temperature_c"),
        "containers": ship.get("containers") or [],
        "consignment": ship.get("consignment") or [],
    }
    meta["recorders"] = [
        {k: r.get(k) for k in ("asset_id", "filename", "container", "summary")}
        for r in ship.get("recorders") or []
    ]
    if gc:
        # What general cargo wording and tables take from the documents: the
        # CFS, the dates of the voyage, customs, each container's weights.
        meta["shipment"].update({k: ship.get(k) for k in (
            "cfs", "arrival_date", "discharged_date", "delivered_date", "loaded_on_board_date", "customs_broker",
            "bill_of_entry", "shipping_bill", "inward_date", "out_of_charge_date", "invoice_value", "insurer",
            "policy_number", "insured_value") if ship.get(k)})
        # A lorry receipt the surveyor checked: when and to where the cargo was trucked.
        lrs = [r for r in ship.get("lorry_receipts") or [] if isinstance(r, dict)]
        if lrs:
            meta["shipment"]["lorry_receipts"] = lrs
            first = lrs[0]
            if first.get("date"):
                meta["shipment"].setdefault("dispatch_date", first["date"])
            if first.get("to_place"):
                meta["shipment"].setdefault("delivery_place", first["to_place"])
        _fill_seals_table(state, ship)
        _apply_weight_slips(state, payload.get("weight_slips") or [], ship.get("containers") or [])
    state["metadata"] = meta

    # The recorder section: the devices' own summary and a graph each. Put
    # after the cause of loss, where the client discusses the printouts.
    recs = []
    base = Path(settings.UPLOAD_DIR).resolve()
    for r in ship.get("recorders") or []:
        asset = await db.get(Asset, r.get("asset_id")) if r.get("asset_id") else None
        rfile = (asset.derived_paths or {}).get("readings") if asset else None
        gfile = (asset.derived_paths or {}).get("graph") if asset else None
        rel = None
        if rfile:
            p = Path(rfile).resolve()
            rel = str(p.relative_to(base)) if base in p.parents else None
        grel = None
        if gfile:
            gp = Path(gfile).resolve()
            grel = str(gp.relative_to(base)) if base in gp.parents else None
        s = r.get("summary") or {}
        recs.append({
            "asset_id": r.get("asset_id"), "container": r.get("container"), "readings_file": rel,
            "graph_file": grel,
            **{k: s.get(k) for k in ("device_id", "start", "stop", "start_iso", "stop_iso", "trip_length",
                                     "highest_c", "lowest_c", "average_c", "mkt_c", "data_points",
                                     "interval", "utc_offset")},
        })
    if recs:
        blocks = state["blocks"]
        existing = next((b for b in blocks if b.get("type") == "temperature_recorders"), None)
        block = {
            **(existing or {"id": "b_recorders", "type": "temperature_recorders",
                            "title": "TEMPERATURE RECORDER SUMMARY", "show_chart": True, "included": True}),
            "recorders": recs,
            "set_point_c": ship.get("requested_temperature_c"),
        }
        if existing is not None:
            blocks[blocks.index(existing)] = block
        else:
            at = next((i + 1 for i, b in enumerate(blocks)
                       if b.get("type") == "narrative" and "CAUSE OF LOSS" in str(b.get("section", "")).upper()), None)
            if at is None:
                at = next((i for i, b in enumerate(blocks) if b.get("type") == "fixed_text"), len(blocks))
            blocks.insert(at, block)
        state["blocks"] = blocks

    report.block_state = state
    flag_modified(report, "block_state")
    if getattr(report, "version", None) is not None:
        report.version += 1
    await AuditService.record_async(
        session=db, actor=actor, action="DOCUMENTS_APPLY", report_id=report.id, path="particulars",
        before=None, after={"rows": [r["label"] for r in rows_in]},
    )
    await db.commit()
    await db.refresh(report)
    return {"status": "success", "version": report.version, "block_state": report.block_state}
