"""
Generate and download DOCX (and eventually PDF) from a report's Block State.
Master Spec §10.6, §10.7 (download button), CRITICAL-RULES §4.

The download endpoint:
1. Fetches the report's block_state from the DB.
2. Calls compute(block_state) — derived values computed fresh, never stored.
3. Calls render_docx() — injects into the DOCX template.
4. Returns the file as a download response.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_actor
from app.database import get_db
from app.models.report import Report
from app.render.docx.engine import render_docx

router = APIRouter()


@router.get("/{report_id}/download/docx")
async def download_docx(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Response:
    """
    Generate and return the DOCX file for a report.
    compute() is called fresh inside render_docx() — never uses stored derived values.
    """
    report = await _get_report_or_404(report_id, db)

    try:
        docx_bytes = render_docx(report.block_state)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"DOCX generation failed: {exc}"
        )

    safe_number = report.report_number.replace("/", "-").replace(" ", "_")
    filename = f"{safe_number}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{report_id}/block-state")
async def update_block_state(
    report_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    """
    Replace or patch the block_state of a report.
    Logs the before/after to the immutable audit trail.
    CRITICAL: Computed values must NOT be stored — strip _computed keys before saving.
    """
    report = await _get_report_or_404(report_id, db)

    # Strip any _computed keys from the incoming state — never store derived values
    new_state = _strip_computed(payload)

    old_state = report.block_state

    from sqlalchemy import update as sql_update
    from datetime import datetime, timezone
    stmt = (
        sql_update(Report)
        .where(Report.id == report.id)
        .values(block_state=new_state, updated_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)

    from app.services.audit import AuditService
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
    return {"status": "updated", "report_id": report_id}


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
        raise HTTPException(status_code=400, detail="Invalid report_id")
    stmt = select(Report).where(Report.id == rid)
    res = await db.execute(stmt)
    report = res.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

