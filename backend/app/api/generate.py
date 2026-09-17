"""
Generate and download DOCX / PDF from a report's Block State.
Master Spec §10.6, §10.7 (download button), CRITICAL-RULES §4.

Week 2 additions:
  - Optimistic concurrency on PATCH /block-state (version check, HTTP 409 on conflict)
  - PDF download via LibreOffice headless (GET /{id}/download/pdf)
  - Numeric traceability gate on every download (HTTP 422 if untraceable numbers found)
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_actor
from app.database import get_db
from app.models.report import Report
from app.models.asset import Asset
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html
from app.render.pdf.engine import render_pdf, LibreOfficeNotAvailableError
from app.compute.traceability import check_traceability
from app.services.audit import AuditService

router = APIRouter()


def _sanitize_photo_groups_for_render(block_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures that empty photo groups (e.g. unpopulated placeholder groups like pg1
    from template defaults) do not trigger assertion failures during preview/download.
    Per Master Spec §10.2, only groups that contain at least one photo are rendered.
    If no photos are uploaded yet, the photo plate renders '[No photos in this series]'.
    """
    state = copy.deepcopy(block_state)
    for block in state.get("blocks", []):
        if block.get("type") == "photo_plate":
            groups = block.get("groups", [])
            block["groups"] = [g for g in groups if g.get("asset_ids")]
    return state


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PatchBlockStateRequest(BaseModel):
    """
    Patch block_state with optimistic concurrency.
    The client must supply the version it last read.
    If the DB version has advanced (another writer beat this one), 409 is returned.
    """
    block_state: Dict[str, Any]
    version: int = Field(ge=1, description="Last known version of the report")


class PatchBlockStateResponse(BaseModel):
    status: str
    report_id: str
    new_version: int


# ---------------------------------------------------------------------------
# HTML Preview
# ---------------------------------------------------------------------------

@router.get("/{report_id}/preview/html")
async def preview_html(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Response:
    """
    Generate and return the A4-styled HTML preview for a report.
    compute() is called fresh inside render_html() — guaranteed zero drift with DOCX.
    """
    report = await _get_report_or_404(report_id, db)
    sanitized_state = _sanitize_photo_groups_for_render(report.block_state)

    try:
        html_content = render_html(sanitized_state)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"HTML preview generation failed: {exc}",
        )

    return Response(
        content=html_content,
        media_type="text/html; charset=utf-8",
        headers={"Content-Type": "text/html; charset=utf-8"},
    )


@router.get("/{report_id}/preview/pdf")
async def preview_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Response:
    """
    Generate and return PDF for in-browser Proof View display.
    Renders DOCX, converts via headless LibreOffice, and serves as inline application/pdf.
    """
    report = await _get_report_or_404(report_id, db)
    sanitized_state = _sanitize_photo_groups_for_render(report.block_state)

    try:
        docx_bytes = render_docx(sanitized_state)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"DOCX generation failed: {exc}",
        )


    try:
        pdf_bytes = render_pdf(docx_bytes)
    except LibreOfficeNotAvailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LibreOffice is not available for PDF preview: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF preview conversion failed: {exc}",
        )

    # Merge annexures if present
    blocks = report.block_state.get("blocks", [])
    annexures_block = next((b for b in blocks if b.get("type") == "annexures"), None)
    if annexures_block:
        from app.render.annexures import merge_pdf_annexures
        pdf_bytes = merge_pdf_annexures(
            body_pdf_bytes=pdf_bytes,
            annexures_block=annexures_block,
            assets=report.block_state.get("assets", {}),
        )

    safe_number = report.report_number.replace("/", "-").replace(" ", "_")
    filename = f"{safe_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# DOCX Download
# ---------------------------------------------------------------------------

@router.get("/{report_id}/download/docx")
async def download_docx(
    report_id: str,
    force: bool = Query(False, description="Bypass traceability gate (logged to audit)"),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Response:
    """
    Generate and return the DOCX file for a report.
    compute() is called fresh inside render_docx() — never uses stored derived values.
    Traceability gate runs before serving; pass ?force=true to bypass (logged).
    """
    report = await _get_report_or_404(report_id, db)
    sanitized_state = _sanitize_photo_groups_for_render(report.block_state)

    try:
        docx_bytes = render_docx(sanitized_state)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"DOCX generation failed: {exc}"
        )

    # Numeric traceability gate
    if not force:
        result = check_traceability(sanitized_state, docx_bytes)
        if not result.passed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "traceability_gate_failed",
                    "message": (
                        "One or more numbers in the rendered document cannot be traced "
                        "to the block state. This prevents download of an unchecked report."
                    ),
                    "untraceable": result.untraceable,
                    "total_checked": result.total_checked,
                    "hint": "Review the flagged numbers, correct the block state, or use ?force=true to bypass.",
                },
            )
    else:
        # Forced bypass — record in audit trail
        await AuditService.record_async(
            session=db,
            actor=actor,
            action="TRACEABILITY_GATE_BYPASSED",
            report_id=report.id,
            path="download/docx",
            before=None,
            after={"format": "docx", "force": True},
        )
        await db.commit()

    safe_number = report.report_number.replace("/", "-").replace(" ", "_")
    filename = f"{safe_number}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# PDF Download
# ---------------------------------------------------------------------------

@router.get("/{report_id}/download/pdf")
async def download_pdf(
    report_id: str,
    force: bool = Query(False, description="Bypass traceability gate (logged to audit)"),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Response:
    """
    Generate DOCX, convert to PDF via LibreOffice headless, and return it.
    Traceability gate runs on the DOCX before conversion.
    """
    report = await _get_report_or_404(report_id, db)
    sanitized_state = _sanitize_photo_groups_for_render(report.block_state)

    # Generate DOCX first (needed for gate + as input to LibreOffice)
    try:
        docx_bytes = render_docx(sanitized_state)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"DOCX generation failed (needed for PDF conversion): {exc}"
        )

    # Numeric traceability gate (on DOCX — same content goes to PDF)
    if not force:
        result = check_traceability(sanitized_state, docx_bytes)

        if not result.passed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "traceability_gate_failed",
                    "message": (
                        "One or more numbers in the rendered document cannot be traced "
                        "to the block state. PDF download is blocked."
                    ),
                    "untraceable": result.untraceable,
                    "total_checked": result.total_checked,
                    "hint": "Review the flagged numbers or use ?force=true to bypass.",
                },
            )
    else:
        await AuditService.record_async(
            session=db,
            actor=actor,
            action="TRACEABILITY_GATE_BYPASSED",
            report_id=report.id,
            path="download/pdf",
            before=None,
            after={"format": "pdf", "force": True},
        )
        await db.commit()

    # Convert DOCX → PDF via LibreOffice headless
    try:
        pdf_bytes = render_pdf(docx_bytes)
    except LibreOfficeNotAvailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LibreOffice is not available for PDF conversion: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF conversion failed: {exc}",
        )

    # Merge annexures if present
    blocks = report.block_state.get("blocks", [])
    annexures_block = next((b for b in blocks if b.get("type") == "annexures"), None)
    if annexures_block:
        from app.render.annexures import merge_pdf_annexures
        pdf_bytes = merge_pdf_annexures(
            body_pdf_bytes=pdf_bytes,
            annexures_block=annexures_block,
            assets=report.block_state.get("assets", {}),
        )

    safe_number = report.report_number.replace("/", "-").replace(" ", "_")
    filename = f"{safe_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# PATCH Block State (Optimistic Concurrency)
# ---------------------------------------------------------------------------

@router.patch("/{report_id}/block-state", response_model=PatchBlockStateResponse)
async def update_block_state(
    report_id: str,
    payload: PatchBlockStateRequest,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> PatchBlockStateResponse:
    """
    Replace the block_state of a report with optimistic concurrency control.

    - The client must send the `version` it last read.
    - If the DB's current version differs → HTTP 409 Conflict.
    - On success, version is incremented and returned.
    - _computed keys are stripped before saving (CRITICAL-RULES §1).
    - Before/after is logged to the immutable audit trail.
    """
    report = await _get_report_or_404(report_id, db)

    # Optimistic concurrency check
    current_version = report.version if report.version is not None else 1
    if payload.version != current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "version_conflict",
                "message": (
                    "The report has been modified by another request since you last read it. "
                    f"You submitted version={payload.version} but current version={current_version}. "
                    "Re-fetch the report and reapply your changes."
                ),
                "current_version": current_version,
                "submitted_version": payload.version,
            },
        )

    # Strip any _computed keys from the incoming state — never store derived values
    new_state = _strip_computed(payload.block_state)
    new_version = current_version + 1
    old_state = report.block_state

    stmt = (
        sql_update(Report)
        .where(Report.id == report.id)
        .values(
            block_state=new_state,
            version=new_version,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(stmt)

    await AuditService.record_async(
        session=db,
        actor=actor,
        action="BLOCK_STATE_UPDATE",
        report_id=report.id,
        path="block_state",
        before=old_state,
        after=new_state,
    )

    await db.commit()

    return PatchBlockStateResponse(
        status="updated",
        report_id=report_id,
        new_version=new_version,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_computed(state: Any) -> Any:
    """Recursively remove _computed keys from a block state dict."""
    if isinstance(state, dict):
        return {k: _strip_computed(v) for k, v in state.items() if k != "_computed"}
    if isinstance(state, list):
        return [_strip_computed(item) for item in state]
    return state


async def _get_report_or_404(report_id: str, db: AsyncSession) -> Report:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report_id format, expected UUID",
        )
    stmt = select(Report).where(Report.id == rid)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Ensure block_state has assets from database so photos always resolve
    stmt_assets = select(Asset).where(Asset.report_id == report.id)
    res_assets = await db.execute(stmt_assets)
    asset_rows = res_assets.scalars().all()
    if asset_rows:
        state_copy = dict(report.block_state) if report.block_state else {"blocks": []}
        assets_dict = dict(state_copy.get("assets", {}))
        for a in asset_rows:
            aid = str(a.id)
            if aid not in assets_dict:
                assets_dict[aid] = {
                    "id": aid,
                    "sha256": a.sha256,
                    "original_path": a.original_path,
                    "derived_paths": a.derived_paths,
                    "url": f"/api/reports/{report_id}/assets/{aid}/image",
                }
        state_copy["assets"] = assets_dict
        report.block_state = state_copy

    return report
