"""
Report Sequences Model for Concurrency-Safe, Gapless Annual Report Numbering.
"""

from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ReportSequence(Base):
    __tablename__ = "report_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_val: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("current_val >= 0", name="chk_report_sequences_val"),
        CheckConstraint("year >= 2000 AND year <= 2100", name="chk_report_sequences_year"),
        {"extend_existing": True},
    )
