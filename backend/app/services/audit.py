"""
Audit Logging Service for Immutable Evidentiary Action Logging.
Enforces Master Spec §9 & CRITICAL-RULES §5:
Every mutation records actor, action, path, and before/after state in the same transaction.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.models.audit import Audit


class AuditService:
    @staticmethod
    async def record_async(
        session: AsyncSession,
        actor: str,
        action: str,
        report_id: Optional[uuid.UUID] = None,
        path: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> Audit:
        """Records an audit event asynchronously in the current database transaction."""
        entry = Audit(
            report_id=report_id,
            at=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            path=path,
            before=before,
            after=after,
        )
        session.add(entry)
        return entry

    @staticmethod
    def record_sync(
        session: Session,
        actor: str,
        action: str,
        report_id: Optional[uuid.UUID] = None,
        path: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> Audit:
        """Records an audit event synchronously in the current database transaction."""
        entry = Audit(
            report_id=report_id,
            at=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            path=path,
            before=before,
            after=after,
        )
        session.add(entry)
        return entry
