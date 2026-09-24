"""
Assets API — Photo upload, management, and column-mapping for spreadsheet import.
Master Spec §10.2, §10.4, CRITICAL-RULES §3.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_actor
from app.database import get_db
from app.ingest.photos import process_photo_upload, verify_original_integrity
from app.ingest.spreadsheet import parse_spreadsheet, build_column_mapping_preview
from app.ingest.tally.categories import build_categories, unit_for
from app.ingest.tally.cloud_reader import cloud_reader_configured
from app.ingest.tally.pipeline import available_engines, read_tally_sheet
from app.ingest.tally.spreadsheet_grid import read_spreadsheet_as_grid
from app.ingest.tally.validation import ValidationEngine
from app.models.asset import Asset
from app.models.report import Report
from app.services.audit import AuditService

router = APIRouter()


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------

@router.post("/{report_id}/assets/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    report_id: str,
    file: UploadFile = File(...),
    series_id: str = Form(default="survey"),
    provenance: str = Form(default="own_survey"),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Upload a photo and store it bit-exact.
    CRITICAL: Original is never recompressed. SHA-256 recorded at upload.
    Derived display (800px) and report (1600px) copies generated separately.
    """
    # Verify report exists
    report = await _get_report_or_404(report_id, db)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    asset_record = process_photo_upload(
        file_bytes=file_bytes,
        original_filename=file.filename or "upload.jpg",
        upload_dir=settings.UPLOAD_DIR,
        derived_dir=settings.DERIVED_DIR,
        report_id=report_id,
    )

    # Persist to assets table
    db_asset = Asset(
        id=str(asset_record["id"]),
        report_id=uuid.UUID(report_id),
        kind="photo",
        sha256=asset_record["sha256"],
        original_path=asset_record["original_path"],
        derived_paths=asset_record["derived_paths"],
        exif=asset_record["exif"],
    )
    db.add(db_asset)

    # Sync asset into report.block_state so renderers and preview can access it
    current_state = dict(report.block_state) if report.block_state else {}
    if "assets" not in current_state or not isinstance(current_state["assets"], dict):
        current_state["assets"] = {}
    
    asset_url = f"/api/reports/{report_id}/assets/{asset_record['id']}/image"
    current_state["assets"][asset_record["id"]] = {
        "id": asset_record["id"],
        "sha256": asset_record["sha256"],
        "original_path": asset_record["original_path"],
        "derived_paths": asset_record["derived_paths"],
        "url": asset_url,
    }
    report.block_state = current_state
    flag_modified(report, "block_state")

    await AuditService.record_async(
        session=db,
        actor=actor,
        action="ASSET_UPLOAD",
        report_id=report.id,
        path=f"assets.{asset_record['id']}",
        before=None,
        after={"sha256": asset_record["sha256"], "series_id": series_id},
    )

    await db.commit()

    return {
        "id": asset_record["id"],
        "sha256": asset_record["sha256"],
        "series_id": series_id,
        "provenance": provenance,
        "original_path": asset_record["original_path"],
        "derived_paths": asset_record["derived_paths"],
        "url": asset_url,
        "exif_integrity": "INTACT",
    }


@router.post("/{report_id}/assets/photos/batch", status_code=status.HTTP_201_CREATED)
async def upload_photos_batch(
    report_id: str,
    files: List[UploadFile] = File(...),
    series_id: str = Form(default="survey"),
    provenance: str = Form(default="own_survey"),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Batch upload multiple photos, storing each bit-exact.
    CRITICAL: Originals are never recompressed. SHA-256 recorded at upload.
    Derived display (800px) and report (1600px) copies generated separately.
    """
    report = await _get_report_or_404(report_id, db)
    if not files:
        raise HTTPException(status_code=400, detail="No files provided in batch upload")

    current_state = dict(report.block_state) if report.block_state else {}
    if "assets" not in current_state or not isinstance(current_state["assets"], dict):
        current_state["assets"] = {}

    results: List[Dict[str, Any]] = []
    for f in files:
        file_bytes = await f.read()
        if not file_bytes:
            continue

        asset_record = process_photo_upload(
            file_bytes=file_bytes,
            original_filename=f.filename or "upload.jpg",
            upload_dir=settings.UPLOAD_DIR,
            derived_dir=settings.DERIVED_DIR,
            report_id=report_id,
        )

        db_asset = Asset(
            id=str(asset_record["id"]),
            report_id=uuid.UUID(report_id),
            kind="photo",
            sha256=asset_record["sha256"],
            original_path=asset_record["original_path"],
            derived_paths=asset_record["derived_paths"],
            exif=asset_record["exif"],
        )
        db.add(db_asset)

        asset_url = f"/api/reports/{report_id}/assets/{asset_record['id']}/image"
        current_state["assets"][asset_record["id"]] = {
            "id": asset_record["id"],
            "sha256": asset_record["sha256"],
            "original_path": asset_record["original_path"],
            "derived_paths": asset_record["derived_paths"],
            "url": asset_url,
        }

        await AuditService.record_async(
            session=db,
            actor=actor,
            action="ASSET_UPLOAD",
            report_id=report.id,
            path=f"assets.{asset_record['id']}",
            before=None,
            after={"sha256": asset_record["sha256"], "series_id": series_id, "batch": True},
        )

        results.append({
            "id": asset_record["id"],
            "sha256": asset_record["sha256"],
            "series_id": series_id,
            "provenance": provenance,
            "original_path": asset_record["original_path"],
            "derived_paths": asset_record["derived_paths"],
            "url": asset_url,
            "exif_integrity": "INTACT",
        })

    report.block_state = current_state
    flag_modified(report, "block_state")
    await db.commit()

    return {
        "count": len(results),
        "assets": results,
    }


@router.get("/{report_id}/assets/{asset_id}/verify")
async def verify_photo_integrity(
    report_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """Re-verify a stored photo's SHA-256 matches the recorded value."""
    stmt = select(Asset).where(
        Asset.id == uuid.UUID(asset_id),
        Asset.report_id == uuid.UUID(report_id),
    )
    res = await db.execute(stmt)
    asset = res.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    record = {
        "sha256": asset.sha256,
        "original_path": asset.original_path,
    }
    intact = verify_original_integrity(record)
    return {"asset_id": asset_id, "integrity": "INTACT" if intact else "TAMPERED"}


@router.get("/{report_id}/assets/{asset_id}/image")
async def get_asset_image(
    report_id: str,
    asset_id: str,
    kind: str = "display",
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve the uploaded photo image for in-browser preview and UI display."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    stmt = select(Asset).where(
        Asset.id == str(asset_id),
        Asset.report_id == rid,
    )
    res = await db.execute(stmt)
    asset = res.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Resolve file path: display copy (800px) > report copy (1600px) > original
    file_path = None
    if kind == "display" and asset.derived_paths:
        file_path = asset.derived_paths.get("display")
    elif kind == "report" and asset.derived_paths:
        file_path = asset.derived_paths.get("report")

    if not file_path or not Path(file_path).exists():
        file_path = asset.original_path

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    img_bytes = Path(file_path).read_bytes()
    return Response(
        content=img_bytes,
        media_type="image/jpeg",
        headers={
            "Content-Type": "image/jpeg",
            "Cache-Control": "public, max-age=86400",
        },
    )


# ---------------------------------------------------------------------------
# Spreadsheet import
# ---------------------------------------------------------------------------

@router.post("/{report_id}/import/spreadsheet")
async def import_spreadsheet(
    report_id: str,
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Upload a .csv or .xlsx and return headers + raw rows for the column-mapping UI.
    Formula cells are returned as their computed values (data_only=True).
    """
    await _get_report_or_404(report_id, db)
    file_bytes = await file.read()
    result = parse_spreadsheet(
        file_bytes=file_bytes,
        filename=file.filename or "upload.xlsx",
        sheet_name=sheet_name,
    )
    # Return mapping preview for the UI
    mapping_preview = build_column_mapping_preview(result["headers"])
    return {
        "headers": result["headers"],
        "sheet_names": result["sheet_names"],
        "active_sheet": result["active_sheet"],
        "row_count": len(result["rows"]),
        "sample_rows": result["rows"][:5],
        "column_mapping_preview": mapping_preview,
    }


@router.post("/{report_id}/import/spreadsheet/apply")
async def apply_spreadsheet_mapping(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Apply a column mapping to raw spreadsheet data and return mapped rows
    suitable for merging into a table block's rows.
    payload: {file_bytes_b64, filename, sheet_name, column_map, block_id}
    """
    import base64
    file_b64 = payload.get("file_bytes_b64", "")
    file_bytes = base64.b64decode(file_b64)
    column_map: Dict[str, str] = payload.get("column_map", {})
    filename = payload.get("filename", "upload.xlsx")
    sheet_name = payload.get("sheet_name")

    result = parse_spreadsheet(
        file_bytes=file_bytes,
        filename=filename,
        sheet_name=sheet_name,
        column_map=column_map,
    )
    return {
        "mapped_rows": result.get("mapped_rows", []),
        "column_map_applied": column_map,
    }


# ---------------------------------------------------------------------------
# Tally sheet ingestion for the Verification Workbench
# ---------------------------------------------------------------------------

def _report_commodity(report: Report) -> Optional[str]:
    """The commodity a report was created for, as recorded in its block state."""
    state = report.block_state or {}
    meta = state.get("metadata") or {}
    val = meta.get("commodity")
    return str(val) if val else None


@router.get("/{report_id}/import/tally/capabilities")
async def tally_capabilities(
    report_id: str,
    commodity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    What this deployment can do with a tally sheet, and which columns this
    commodity's grid should have.

    The workbench asks for this before showing the upload box so it can tell the
    surveyor plainly that no OCR engine is installed, rather than letting him
    upload a sheet and wonder why nothing came back.
    """
    report = await _get_report_or_404(report_id, db)
    key = commodity or _report_commodity(report)
    engines = available_engines()
    cloud = cloud_reader_configured()

    return {
        "commodity": key,
        "unit": unit_for(key),
        "categories": build_categories(key),
        "ocr_engines": engines,
        "ocr_available": bool(engines),
        # The cloud reader is the main path when a key is set; the local engines
        # are what runs otherwise.
        "cloud_reader": cloud,
        "cloud_sends_header": bool(settings.TALLY_CLOUD_SEND_FULL_SHEET),
        "reader": "cloud" if cloud else ("local" if engines else "none"),
    }


@router.post("/{report_id}/import/tally-spreadsheet")
async def import_tally_spreadsheet(
    report_id: str,
    file: UploadFile = File(...),
    commodity: Optional[str] = Form(default=None),
    sheet_name: Optional[str] = Form(default=None),
    column_map_json: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Load a CSV or Excel tally into the Verification Workbench.

    The same grid and the same row checks as a photographed sheet, because a
    spreadsheet from the cold store is no more authoritative than a notebook
    page: its column headings are whatever that cold store calls them, and any
    column that cannot be matched is put in front of the surveyor rather than
    dropped.

    Call it again with column_map_json once he has mapped the leftovers.
    """
    import json as _json

    report = await _get_report_or_404(report_id, db)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    column_map: Optional[Dict[str, str]] = None
    if column_map_json:
        try:
            parsed = _json.loads(column_map_json)
            if isinstance(parsed, dict):
                column_map = {str(k): str(v) for k, v in parsed.items()}
        except ValueError:
            raise HTTPException(status_code=400, detail="column_map_json is not valid JSON")

    try:
        return read_spreadsheet_as_grid(
            file_bytes=file_bytes,
            filename=file.filename or "tally.xlsx",
            commodity=commodity or _report_commodity(report),
            sheet_name=sheet_name,
            column_map=column_map,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{report_id}/import/tally-ocr")
async def import_tally_ocr(
    report_id: str,
    file: UploadFile = File(...),
    commodity: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Read a photographed tally sheet into a grid for the workbench.

    The hosted vision model reads it when a key is configured, because it is the
    only reader that handles a sideways photo of a pen-filled form. The local
    engines run otherwise. Either way the result is a draft: the surveyor checks
    it against the sheet, and the row arithmetic has to tie out before any of it
    reaches the report.
    """
    report = await _get_report_or_404(report_id, db)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    return await read_tally_sheet(
        image_bytes=file_bytes,
        filename=file.filename or "tally_sheet.jpg",
        commodity=commodity or _report_commodity(report),
    )


def _figure(v: Any, unit: str) -> Optional[Any]:
    """
    A cell value as the server stores it: an int count, or a 3-dp Decimal for kg.

    This used to be int(v) for everything, so a grapes weight of 0.820 either
    raised and was silently dropped (as text) or became 0 (as a float). Both
    changed the report without anyone seeing it happen.
    """
    from decimal import Decimal, InvalidOperation

    if v is None or isinstance(v, bool) or str(v).strip() == "":
        return None
    if (unit or "pcs").lower() == "kg":
        try:
            d = Decimal(str(v).strip())
        except InvalidOperation:
            return None
        return d.quantize(Decimal("0.001")) if d >= 0 else None
    try:
        d = Decimal(str(v).strip())
    except InvalidOperation:
        return None
    # A count must be whole; 2.5 is a typo, not a count, so it is not rounded.
    if d < 0 or d != d.to_integral_value():
        return None
    return int(d)


def _recheck_rows(rows: List[Dict[str, Any]], unit: str = "pcs") -> List[Dict[str, Any]]:
    """
    Recompute every row's sum and its agreement with the written total.

    Done on the server on the way in, never taken from the request. The browser
    computes the same figures live so the surveyor sees them as he types, but a
    total that reaches the database has to be one this process derived from the
    cell values sitting beside it, or the check is only as trustworthy as
    whatever last posted to the endpoint.
    """
    checked: List[Dict[str, Any]] = []
    for row in rows:
        values: Dict[str, Any] = {}
        for k, v in (row.get("values") or {}).items():
            fv = _figure(v, unit)
            if fv is not None:
                values[k] = fv

        stated_int = _figure(row.get("stated_total"), unit)

        computed, check = ValidationEngine.validate_row_total(values, stated_int)
        status = {"PASSED": "OK", "FAILED": "MISMATCH", "SKIPPED": "UNCHECKED"}[check.status]

        new_row = dict(row)
        new_row.update({
            "values": values,
            "stated_total": stated_int,
            "computed_total": computed,
            "check": {
                "status": status,
                "delta": (computed - stated_int) if stated_int is not None else None,
                "message": check.message,
            },
        })
        checked.append(new_row)
    return checked


@router.post("/{report_id}/import/tally-ocr/apply")
async def apply_tally_ocr(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Write the grid the surveyor checked in the workbench into the report.

    This is the point at which the data stops being a machine reading and
    becomes the surveyor's figures, so it is tagged 'surveyor_verified'. Rows
    whose cells still disagree with the written total are refused: a mismatch
    means one of the two numbers is wrong, and carrying it into the report would
    put an arithmetic error into a document that goes out under an IRDAI licence.
    """
    report = await _get_report_or_404(report_id, db)

    headers = payload.get("headers", {})
    table_data = payload.get("table", {})
    target_block_id = payload.get("block_id")

    rows_in = table_data.get("rows") or []
    table_unit = str(table_data.get("unit") or "pcs")
    rechecked = _recheck_rows(rows_in, table_unit)

    mismatched = [
        f"{r.get('group') or f'row {i + 1}'} ({r['check']['delta']:+})"
        for i, r in enumerate(rechecked)
        if r["check"]["status"] == "MISMATCH"
    ]
    if mismatched:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "These rows do not add up to the total written on the sheet. "
                    "Correct the cells or the total before applying."
                ),
                "rows": mismatched,
            },
        )

    state = dict(report.block_state) if report.block_state else {"blocks": []}
    blocks = list(state.get("blocks", []))

    # 1. Update Particulars Block
    if headers:
        for b in blocks:
            if b.get("type") == "particulars":
                rows = list(b.get("rows", []))
                for row in rows:
                    lbl = str(row.get("label", "")).lower()
                    if "container" in lbl and headers.get("container_number"):
                        row["value"] = headers["container_number"]
                        row["provenance"] = "surveyor_verified"
                    elif ("consignee" in lbl or "party" in lbl or "applicant" in lbl) and headers.get("party_name"):
                        row["value"] = headers["party_name"]
                        row["provenance"] = "surveyor_verified"
                    elif "survey" in lbl and "date" in lbl and headers.get("survey_date"):
                        row["value"] = headers["survey_date"]
                        row["provenance"] = "surveyor_verified"
                    elif "destuff" in lbl and "date" in lbl and headers.get("destuff_date"):
                        row["value"] = headers["destuff_date"]
                        row["provenance"] = "surveyor_verified"
                b["rows"] = rows

    # 2. Update Measurements Block
    if headers:
        for b in blocks:
            if b.get("type") == "measurements":
                rows = list(b.get("rows", []))
                for row in rows:
                    subj = str(row.get("subject", "")).lower()
                    if "pulp" in subj and (headers.get("pulp_temp_min") is not None or headers.get("pulp_temp_max") is not None):
                        if headers.get("pulp_temp_min") is not None:
                            row["min"] = str(headers["pulp_temp_min"])
                        if headers.get("pulp_temp_max") is not None:
                            row["max"] = str(headers["pulp_temp_max"])
                        row["provenance"] = "surveyor_verified"
                    elif "brix" in subj and (headers.get("brix_min") is not None or headers.get("brix_max") is not None):
                        if headers.get("brix_min") is not None:
                            row["min"] = str(headers["brix_min"])
                        if headers.get("brix_max") is not None:
                            row["max"] = str(headers["brix_max"])
                        row["provenance"] = "surveyor_verified"
                    elif ("ambient" in subj or "cold room" in subj or "storage" in subj) and headers.get("room_temp") is not None:
                        row["min"] = str(headers["room_temp"])
                        row["provenance"] = "surveyor_verified"
                b["rows"] = rows

    # 3. Update the tally table block
    if rechecked:
        for b in blocks:
            if b.get("type") == "table" and (not target_block_id or b.get("id") == target_block_id):
                if table_data.get("categories"):
                    b["categories"] = table_data["categories"]
                if table_data.get("unit"):
                    b["unit"] = table_data["unit"]

                # Values are stored as strings because the renderer converts
                # them with Decimal; going via float would reintroduce the
                # rounding the report is supposed to be free of.
                b["rows"] = [
                    {
                        "group": r.get("group") or f"Row {i + 1}",
                        "boxes_opened": r.get("boxes_opened", 1),
                        "values": {k: str(v) for k, v in r["values"].items()},
                        # A kg total is a Decimal, which JSONB cannot hold; as
                        # text it keeps its three places, as the cells do.
                        "stated_total": (
                            str(r["stated_total"])
                            if r["stated_total"] is not None and not isinstance(r["stated_total"], int)
                            else r["stated_total"]
                        ),
                        "provenance": "surveyor_verified",
                    }
                    for i, r in enumerate(rechecked)
                ]
                b["provenance"] = "surveyor_verified"
                break

    state["blocks"] = blocks
    report.block_state = state
    flag_modified(report, "block_state")
    if hasattr(report, "version") and report.version is not None:
        report.version += 1

    await AuditService.record_async(
        session=db,
        actor=actor,
        action="TALLY_OCR_INGEST",
        report_id=report.id,
        path="blocks",
        before=None,
        after={"provenance": "surveyor_verified"},
    )

    await db.commit()
    await db.refresh(report)

    return {
        "status": "success",
        "report_id": str(report.id),
        "version": getattr(report, "version", 1),
        "block_state": report.block_state,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_report_or_404(report_id: str, db: AsyncSession) -> Report:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")
    stmt = select(Report).where(Report.id == rid)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

