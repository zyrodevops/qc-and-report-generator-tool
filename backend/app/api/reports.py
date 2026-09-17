"""
Reports API endpoints for Report Creation and Listing with Atomic Sequencing and Audit Trails.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_actor, get_current_user, UserSession
from app.database import get_db
from app.models.report import Report, allocate_report_number_async
from app.models.template import Template
from app.models.asset import Asset
from app.services.audit import AuditService

router = APIRouter()


class CreateReportRequest(BaseModel):
    template_id: str
    family: str = "marine_cargo"
    year: int = Field(default=2026, ge=2000, le=2100)
    commodity: Optional[str] = None
    state: Optional[str] = "FINAL"
    selected_sections: Optional[List[str]] = None
    block_state: Dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    id: str
    report_number: str
    family: str
    state: str
    status: str
    template_id: str
    version: int = 1
    block_state: Dict[str, Any]
    created_at: str
    updated_at: str


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: CreateReportRequest,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
):
    # The report type must be one that is actually seeded.
    #
    # This used to create a template on the fly for any id it was handed, with
    # an empty block sequence, so that early tests would not block. The effect
    # in practice was that a stale or mistyped id silently produced a new report
    # type — 'mca-qc-v1' and 'tpl_qc_mandarin_v1' both reached the database this
    # way — and a report built on one renders as an empty document, because
    # there are no blocks to render. Refusing here keeps the report types to the
    # six that are seeded and turns a typo into an error the caller can see.
    tmpl_stmt = select(Template).where(Template.id == payload.template_id)
    tmpl_res = await db.execute(tmpl_stmt)
    template = tmpl_res.scalars().first()

    if not template:
        known = (await db.execute(select(Template.id).order_by(Template.id))).scalars().all()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Unknown report type '{payload.template_id}'.",
                "available": list(known),
            },
        )

    if not template.block_sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Report type '{payload.template_id}' has no sections defined, so it "
                "would produce an empty document."
            ),
        )

    # 1. Atomically allocate gapless sequential report number
    report_number = await allocate_report_number_async(db, year=payload.year)

    # 2. Populate default block_state if none provided
    initial_block_state = payload.block_state
    report_state = (payload.state or "FINAL").upper()
    if not initial_block_state or not initial_block_state.get("blocks"):
        from app.seeds.defaults import get_default_block_state
        initial_block_state = get_default_block_state(
            template_id=template.id,
            commodity_key=payload.commodity,
            state=report_state,
            selected_sections=payload.selected_sections,
        )

    # 3. Instantiate Report
    report = Report(
        id=uuid.uuid4(),
        report_number=report_number,
        family=payload.family,
        state=report_state,
        status="DRAFT",
        template_id=template.id,
        block_state=initial_block_state,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.flush()

    # 4. Record audit event in the same transaction
    await AuditService.record_async(
        session=db,
        actor=actor,
        action="REPORT_CREATE",
        report_id=report.id,
        path="",
        before=None,
        after={"report_number": report.report_number, "status": report.status},
    )

    await db.commit()
    await db.refresh(report)

    version_val = getattr(report, "version", 1) or 1

    return ReportResponse(
        id=str(report.id),
        report_number=report.report_number,
        family=report.family,
        state=report.state,
        status=report.status,
        template_id=report.template_id,
        version=version_val,
        block_state=report.block_state,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    stmt = select(Report).order_by(Report.created_at.desc())
    res = await db.execute(stmt)
    reports = res.scalars().all()

    return [
        ReportResponse(
            id=str(r.id),
            report_number=r.report_number,
            family=r.family,
            state=r.state,
            status=r.status,
            template_id=r.template_id,
            version=getattr(r, "version", 1) or 1,
            block_state=r.block_state,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> ReportResponse:
    """
    Fetch a single report by ID.
    Returns full metadata, optimistic concurrency version, and raw block_state.
    """
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    version_val = getattr(
        report, "version", report.block_state.get("metadata", {}).get("version", 1)
    )
    if version_val is None:
        version_val = 1

    # Enrich block_state with assets from DB so photos are always available
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
        report_block_state = state_copy
    else:
        report_block_state = report.block_state

    return ReportResponse(
        id=str(report.id),
        report_number=report.report_number,
        family=report.family,
        state=report.state,
        status=report.status,
        template_id=report.template_id,
        version=version_val,
        block_state=report_block_state,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )
