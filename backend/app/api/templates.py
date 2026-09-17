"""
Report templates API.

The report-type dropdown used to be a hardcoded list in the frontend, which drifted
from the database: it still referenced the hyphenated duplicate ids after those were
removed, so creating a report would have failed on the template foreign key.

The dropdown now reads from here, so there is one source of truth.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.template import Template

router = APIRouter()

# Order the dropdown by what the client actually produces most.
# Perishable Final Survey Report is 95.4% of the fruit archive; QC is the short path.
_ORDER = [
    "perishable_sea_survey",
    "perishable_air_survey",
    "perishable_qc_sea",
    "perishable_qc_air",
    "general_cargo_sea_survey",
    "general_cargo_air_survey",
]


@router.get("/templates")
async def list_templates(
    family: Optional[str] = Query(None, description="QC_REPORT | SURVEY_REPORT"),
    mode: Optional[str] = Query(None, description="SEA | AIR"),
    db: AsyncSession = Depends(get_db),
):
    """Report types available in the New Report dialog."""
    stmt = select(Template)
    if family:
        stmt = stmt.where(Template.family == family.upper())
    if mode:
        stmt = stmt.where(Template.mode == mode.upper())

    rows = (await db.execute(stmt)).scalars().all()

    # Only offer the canonical six. Test fixtures and older experiments leave
    # stray rows behind (mca-qc-v1, tpl_qc_mandarin_v1) with empty block
    # sequences; those must never reach the dropdown.
    rows = [t for t in rows if t.id in _ORDER and t.block_sequence]

    def rank(t: Template) -> int:
        return _ORDER.index(t.id)

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "family": t.family,
                "mode": t.mode,
                # PERISHABLE templates take a commodity; general cargo does not.
                "requires_commodity": t.id.startswith("perishable"),
                "block_count": len(t.block_sequence or []),
            }
            for t in sorted(rows, key=rank)
        ]
    }
