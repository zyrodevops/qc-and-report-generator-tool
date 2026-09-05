"""
Report Model and Concurrency-Safe Report Number Allocation.
Enforces Master Spec §9: M-<n>-<year> sequential numbering per year,
safe under concurrent requests via row-level locks on report_sequences.

Remediated for Milestone M1 Iteration 2:
- Removed _in_memory_sequences and _seq_lock completely.
- allocate_report_number and allocate_report_number_async raise DatabaseConnectionError
  (subclass of RuntimeError) on any database failure.
- Zero silent fallbacks.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DatabaseConnectionError(RuntimeError):
    """Raised when database connection or sequence allocation fails."""
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    template_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("templates.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    block_state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
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

    template: Mapped["Template"] = relationship("Template", back_populates="reports")
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="report", cascade="all, delete-orphan"
    )
    audits: Mapped[List["Audit"]] = relationship("Audit", back_populates="report")

    __table_args__ = (
        UniqueConstraint("report_number", name="uq_reports_report_number"),
        Index("ix_reports_family", "family"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_created_at", created_at.desc()),
        Index(
            "ix_reports_block_state_gin",
            "block_state",
            postgresql_using="gin",
            postgresql_ops={"block_state": "jsonb_path_ops"},
        ),
        {"extend_existing": True},
    )


def allocate_report_number(year: int = 2026, session: Optional[Any] = None) -> str:
    """
    Atomically allocates the next consecutive gapless report number for the given year.
    Uses PostgreSQL ON CONFLICT (year) DO UPDATE row-level lock.
    Format: 'M-<n>-<year>'

    Raises:
        DatabaseConnectionError: If database execution fails. Never falls back to memory.
    """
    stmt = text("""
        INSERT INTO report_sequences (year, current_val)
        VALUES (:year, 1)
        ON CONFLICT (year)
        DO UPDATE SET current_val = report_sequences.current_val + 1
        RETURNING current_val;
    """)

    if session is not None:
        try:
            result = session.execute(stmt, {"year": year})
            next_val = result.scalar_one()
            return f"M-{next_val}-{year}"
        except Exception as exc:
            raise DatabaseConnectionError(
                f"Database sequence allocation failed for year {year}: {exc}"
            ) from exc

    # No session passed: attempt via sync database engine
    try:
        from app.database import sync_engine
        with sync_engine.begin() as conn:
            result = conn.execute(stmt, {"year": year})
            next_val = result.scalar_one()
            return f"M-{next_val}-{year}"
    except Exception as exc:
        raise DatabaseConnectionError(
            f"Database sequence allocation failed for year {year}: {exc}"
        ) from exc


async def allocate_report_number_async(session: AsyncSession, year: int = 2026) -> str:
    """
    Async version for FastAPI route handlers within an active async transaction.

    Raises:
        DatabaseConnectionError: If database execution fails.
    """
    stmt = text("""
        INSERT INTO report_sequences (year, current_val)
        VALUES (:year, 1)
        ON CONFLICT (year)
        DO UPDATE SET current_val = report_sequences.current_val + 1
        RETURNING current_val;
    """)
    try:
        result = await session.execute(stmt, {"year": year})
        next_val = result.scalar_one()
        return f"M-{next_val}-{year}"
    except Exception as exc:
        raise DatabaseConnectionError(
            f"Database async sequence allocation failed for year {year}: {exc}"
        ) from exc
