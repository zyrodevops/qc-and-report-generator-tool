"""
Template Model defining canonical report document block layouts.
"""

from datetime import datetime, timezone
from typing import Any, List
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    block_sequence: Mapped[List[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    reports: Mapped[List["Report"]] = relationship("Report", back_populates="template")

    __table_args__ = (
        Index("ix_templates_family_mode", "family", "mode"),
        Index("ix_templates_family", "family"),
        {"extend_existing": True},
    )
