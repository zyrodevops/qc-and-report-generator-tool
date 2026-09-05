"""
Audit Model for Strictly Immutable, Evidentiary Action Logging.
Enforces Master Spec §9 and §10.8: Insert-only audit trail.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Audit(Base):
    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="RESTRICT"),
        nullable=True,
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    before: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    report: Mapped[Optional["Report"]] = relationship("Report", back_populates="audits")

    __table_args__ = (
        Index("ix_audit_report_id", "report_id"),
        Index("ix_audit_at", "at"),
        Index("ix_audit_actor", "actor"),
        Index("ix_audit_action", "action"),
        {"extend_existing": True},
    )
