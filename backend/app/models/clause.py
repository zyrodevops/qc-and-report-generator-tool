"""
Clause Model for Surveyor Legal and Narrative Clause Library.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    text_with_slots: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_clauses_key_version"),
        Index("ix_clauses_key", "key"),
        {"extend_existing": True},
    )
