"""
Asset Model for Bit-Exact Photo Originals, Derived Images, and EXIF Metadata.
Enforces CRITICAL-RULES §3: Never recompress or overwrite an original photo.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    derived_paths: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    exif: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    report: Mapped["Report"] = relationship("Report", back_populates="assets")

    __table_args__ = (
        Index("ix_assets_report_id", "report_id"),
        Index("ix_assets_sha256", "sha256"),
        Index("ix_assets_kind", "kind"),
        {"extend_existing": True},
    )
