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
from app.ingest.documents.readers import read_document
from app.models.asset import Asset
from app.services.audit import AuditService

router = APIRouter()

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
        result = read_document(data, name)
        stored = _store(report_id, data, name)
        asset_id = f"doc_{stored['sha256'][:24]}"
        derived: Dict[str, Any] = {"filename": name, "kind": result.get("kind")}
        readings = result.pop("readings", None)
        if readings:
            rpath = stored["folder"] / f"{stored['sha256'][:16]}.readings.json"
            rpath.write_text(json.dumps(readings), encoding="utf-8")
            derived["readings"] = str(rpath)
            result["readings"] = readings  # for merge's count only
        existing = await db.get(Asset, asset_id)
        if existing is None:
            db.add(Asset(id=asset_id, report_id=report.id, kind="document", sha256=stored["sha256"],
                         original_path=stored["path"], derived_paths=derived, exif={}))
        else:
            existing.derived_paths = derived
        docs.append({"asset_id": asset_id, "filename": name, **result})

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
                 "kind_label": KIND_LABELS.get(d.get("kind"), d.get("kind")), "status": d.get("status")}
        if d.get("kind") == "recorder":
            entry["summary"] = d.get("summary")
            entry["readings"] = len(d.get("readings") or [])
        else:
            entry["fields"] = {k: v.get("value") for k, v in (d.get("fields") or {}).items()}
        summary.append(entry)
    return {
        "documents": summary,
        "shipment": merged["shipment"],
        "particulars": particulars(merged["shipment"]),
        "conflicts": merged["conflicts"],
        "notes": merged["notes"],
    }


@router.get("/{report_id}/recorders/{asset_id}/chart.png")
async def recorder_chart(
    report_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
):
    """The graph of one recorder's readings, as the report will print it."""
    from fastapi.responses import Response
    from app.render.recorder_chart import chart_for

    report = await _get_report_or_404(report_id, db)
    block = next((b for b in (report.block_state or {}).get("blocks", []) if b.get("type") == "temperature_recorders"), None)
    rec = next((r for r in (block or {}).get("recorders", []) if r.get("asset_id") == asset_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="No such recorder in this report.")
    png = chart_for(rec, block.get("set_point_c"))
    if not png:
        raise HTTPException(status_code=404, detail="This recorder has no readings to draw.")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


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
    rows_in: List[Dict[str, Any]] = [r for r in (payload.get("particulars") or []) if str(r.get("value", "")).strip()]
    ship: Dict[str, Any] = payload.get("shipment") or {}

    state = dict(report.block_state or {})
    blocks = list(state.get("blocks", []))
    for b in blocks:
        if b.get("type") != "particulars":
            continue
        rows = list(b.get("rows", []))
        for r in rows_in:
            label = str(r["label"]).strip()
            hit = next((row for row in rows if str(row.get("label", "")).strip().lower() == label.lower()), None)
            new = {"label": label, "value": [str(r["value"]).strip()], "provenance": "document_verified"}
            if hit is not None:
                rows[rows.index(hit)] = {**hit, **new}
            else:
                rows.append(new)
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
    state["metadata"] = meta

    # The recorder section: the devices' own summary and a graph each. Put
    # after the cause of loss, where the client discusses the printouts.
    recs = []
    base = Path(settings.UPLOAD_DIR).resolve()
    for r in ship.get("recorders") or []:
        asset = await db.get(Asset, r.get("asset_id")) if r.get("asset_id") else None
        rfile = (asset.derived_paths or {}).get("readings") if asset else None
        rel = None
        if rfile:
            p = Path(rfile).resolve()
            rel = str(p.relative_to(base)) if base in p.parents else None
        s = r.get("summary") or {}
        recs.append({
            "asset_id": r.get("asset_id"), "container": r.get("container"), "readings_file": rel,
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
