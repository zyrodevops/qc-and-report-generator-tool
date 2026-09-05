"""
Assets API — Photo upload, management, and column-mapping for spreadsheet import.
Master Spec §10.2, §10.4, CRITICAL-RULES §3.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_actor
from app.database import get_db
from app.ingest.photos import process_photo_upload, verify_original_integrity
from app.ingest.spreadsheet import parse_spreadsheet, build_column_mapping_preview
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
        "exif_integrity": "INTACT",
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

