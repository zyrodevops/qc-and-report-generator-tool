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
from app.ingest.tally_ocr import parse_tally_image
from app.ingest.tally_knowledge_base import list_available_sample_tallies, KNOWN_TALLY_CATALOG
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
# Tally Sheet OCR Ingestion (PaddleOCR + Knowledge Base Corroboration)
# ---------------------------------------------------------------------------

@router.get("/{report_id}/import/tally-samples")
async def get_sample_tallies(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> List[Dict[str, Any]]:
    """Return available sample tally sheets from client archive for 1-click test & prefill."""
    await _get_report_or_404(report_id, db)
    return list_available_sample_tallies()


@router.post("/{report_id}/import/tally-ocr")
async def import_tally_ocr(
    report_id: str,
    file: Optional[UploadFile] = File(default=None),
    sample_id: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Upload a cold-storage handwritten tally sheet photo, or select a sample tally ID.
    Runs local OCR (EasyOCR primary, with RapidOCR, PaddleOCR, Tesseract fallbacks)
    preprocessing and extraction for headers, QC readings, and defect tables,
    corroborating with known client tally datasets.
    """
    await _get_report_or_404(report_id, db)
    
    if sample_id:
        from pathlib import Path
        sample_item = next((s for s in KNOWN_TALLY_CATALOG if s["id"].upper() == sample_id.upper()), None)
        if not sample_item:
            raise HTTPException(status_code=404, detail=f"Sample tally ID {sample_id} not found")
        candidates = [
            Path("sample-data/tally_sheets/Marine cargo/Tally sheets") / sample_item["source_photo"],
            Path(__file__).resolve().parents[2] / "sample-data/tally_sheets/Marine cargo/Tally sheets" / sample_item["source_photo"],
            Path(__file__).resolve().parents[3] / "sample-data/tally_sheets/Marine cargo/Tally sheets" / sample_item["source_photo"],
        ]
        photo_path = next((p for p in candidates if p.exists()), None)
        if not photo_path:
            raise HTTPException(status_code=404, detail=f"Sample photo file {sample_item['source_photo']} not found")
        file_bytes = photo_path.read_bytes()
        filename = sample_item["source_photo"]
    elif file:
        file_bytes = await file.read()
        filename = file.filename or "tally_sheet.jpg"
    else:
        raise HTTPException(status_code=400, detail="Either 'file' or 'sample_id' must be provided")

    extracted = parse_tally_image(
        image_bytes=file_bytes,
        filename=filename,
    )
    return extracted


@router.post("/{report_id}/import/tally-ocr/apply")
async def apply_tally_ocr(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Apply verified tally OCR data to report block_state.
    Updates particulars, measurements, and table blocks with provenance tag 'ocr_verified'.
    """
    report = await _get_report_or_404(report_id, db)
    
    headers = payload.get("headers", {})
    table_data = payload.get("table", {})
    target_block_id = payload.get("block_id")

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
                        row["provenance"] = "ocr_verified"
                    elif ("consignee" in lbl or "party" in lbl or "applicant" in lbl) and headers.get("party_name"):
                        row["value"] = headers["party_name"]
                        row["provenance"] = "ocr_verified"
                    elif "survey" in lbl and "date" in lbl and headers.get("survey_date"):
                        row["value"] = headers["survey_date"]
                        row["provenance"] = "ocr_verified"
                    elif "destuff" in lbl and "date" in lbl and headers.get("destuff_date"):
                        row["value"] = headers["destuff_date"]
                        row["provenance"] = "ocr_verified"
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
                        row["provenance"] = "ocr_verified"
                    elif "brix" in subj and (headers.get("brix_min") is not None or headers.get("brix_max") is not None):
                        if headers.get("brix_min") is not None:
                            row["min"] = str(headers["brix_min"])
                        if headers.get("brix_max") is not None:
                            row["max"] = str(headers["brix_max"])
                        row["provenance"] = "ocr_verified"
                    elif ("ambient" in subj or "cold room" in subj or "storage" in subj) and headers.get("room_temp") is not None:
                        row["min"] = str(headers["room_temp"])
                        row["provenance"] = "ocr_verified"
                b["rows"] = rows

    # 3. Update Table Block
    if table_data and table_data.get("rows"):
        table_updated = False
        for b in blocks:
            if b.get("type") == "table" and (not target_block_id or b.get("id") == target_block_id):
                if table_data.get("categories"):
                    b["categories"] = table_data["categories"]
                # Map rows and ensure string values for Decimal conversion
                mapped_rows = []
                for r in table_data["rows"]:
                    row_vals = {}
                    for k, v in r.get("values", {}).items():
                        row_vals[k] = str(v)
                    mapped_rows.append({
                        "group": r.get("group", "Sample"),
                        "boxes_opened": r.get("boxes_opened", 1),
                        "values": row_vals,
                        "provenance": "ocr_verified",
                    })
                b["rows"] = mapped_rows
                b["provenance"] = "ocr_verified"
                table_updated = True
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
        after={"provenance": "ocr_verified"},
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

