"""
Standard wording for the narrative sections.

POST /api/clauses/pick — for one section of one report, the topics that
section carries in the client's reports ("Pulp temperature", "No recorder
data", "Packing List" …), in the order they usually come. Each carries that
topic's sentences as the client writes them for this fruit and this transport
mode, with another report's facts blanked (see app/seeds/clause_library.py).
One click adds a topic; several can go into one section.

This replaces a clause library and a "taxonomy" of causes and scenarios that
were written by a model and presented as the client's wording: checked against
the corpus, 0 of 150 cause/next-step sentences and 4 of 42 scenario sentences
appeared in any real report.

The surveyor is not shown statistics about his archive, and nothing is added
for him: the response is ordered, and that is all.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_actor
from app.database import get_db
from app.seeds.clause_library import TOPICS, csv_fruit_key, load_library, offer

router = APIRouter()

FORM_SECTIONS = {t.form_section for t in TOPICS}


class PickRequest(BaseModel):
    section: str
    commodity: Optional[str] = None
    # SEA or AIR, from the report type. Wording is taken from reports of the same kind.
    mode: Optional[str] = None
    # Values this report already has; blanks they answer are filled in.
    values: Dict[str, Any] = Field(default_factory=dict)
    # Tally columns with a count above zero, for choosing cause-of-loss wording.
    defects: List[str] = Field(default_factory=list)


@router.post("/clauses/pick")
async def pick_clauses(
    payload: PickRequest,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor),
) -> Dict[str, Any]:
    section = payload.section.strip().lower()
    fruit = csv_fruit_key(payload.commodity)
    rows, links = await load_library(db)
    if section not in FORM_SECTIONS or not rows or not fruit:
        # General cargo is out of scope: its archive belongs to another firm.
        return {"section": section, "topics": [], "available": bool(rows)}
    topics = offer(rows, form_section=section, fruit=fruit, mode=payload.mode, values=payload.values,
                   defects=payload.defects, links=links)
    return {"section": section, "available": True, "topics": topics}
