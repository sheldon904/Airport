"""Audit logging service for compliance tracking."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import AuditLogModel

logger = structlog.get_logger()


class AuditAction(str, Enum):
    """Enumeration of auditable actions."""

    # Authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    PASSWORD_CHANGED = "user.password_changed"
    PASSWORD_RESET_REQUESTED = "user.password_reset_requested"
    PASSWORD_RESET_COMPLETED = "user.password_reset_completed"
    LOGIN_FAILED = "user.login_failed"

    # Organization
    ORG_CREATED = "organization.created"
    ORG_UPDATED = "organization.updated"
    ORG_USER_ADDED = "organization.user_added"
    ORG_USER_REMOVED = "organization.user_removed"

    # Transaction
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_STATUS_CHANGED = "transaction.status_changed"
    TRANSACTION_DELETED = "transaction.deleted"
    TRANSACTION_VIEWED = "transaction.viewed"

    # Document
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_VERIFIED = "document.verified"
    DOCUMENT_REJECTED = "document.rejected"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_DOWNLOADED = "document.downloaded"

    # Deadline
    DEADLINE_CREATED = "deadline.created"
    DEADLINE_UPDATED = "deadline.updated"
    DEADLINE_COMPLETED = "deadline.completed"
    DEADLINE_MISSED = "deadline.missed"
    DEADLINE_REMINDER_SENT = "deadline.reminder_sent"

    # Agent
    AGENT_EXECUTION_STARTED = "agent.execution_started"
    AGENT_EXECUTION_COMPLETED = "agent.execution_completed"
    AGENT_EXECUTION_FAILED = "agent.execution_failed"
    AGENT_REVIEW_REQUIRED = "agent.review_required"

    # Report
    REPORT_GENERATED = "report.generated"
    REPORT_DOWNLOADED = "report.downloaded"

    # Compliance
    COMPLIANCE_CHECK_PASSED = "compliance.check_passed"
    COMPLIANCE_CHECK_FAILED = "compliance.check_failed"
    COMPLIANCE_OVERRIDE = "compliance.override"


class AuditEntry(BaseModel):
    """Audit log entry data."""

    action: AuditAction
    user_id: UUID | None = None
    organization_id: UUID | None = None
    transaction_id: UUID | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    agent_type: str | None = None
    details: dict[str, Any] = {}
    ip_address: str | None = None
    user_agent: str | None = None


class AuditService:
    """
    Service for recording audit logs.

    Provides compliance-grade audit trail for all significant actions
    in the system. All audit entries are immutable once created.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        action: AuditAction,
        *,
        user_id: UUID | None = None,
        organization_id: UUID | None = None,
        transaction_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        agent_type: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLogModel:
        """
        Record an audit log entry.

        This method is intentionally fire-and-forget safe - it logs
        errors but doesn't raise exceptions to avoid disrupting
        business operations.
        """
        try:
            audit_log = AuditLogModel(
                id=uuid4(),
                transaction_id=transaction_id,
                user_id=user_id,
                action=action.value,
                agent_type=agent_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc),
            )

            self.session.add(audit_log)
            await self.session.flush()

            # Also log to structured log for real-time monitoring
            logger.info(
                "audit_logged",
                action=action.value,
                user_id=str(user_id) if user_id else None,
                organization_id=str(organization_id) if organization_id else None,
                transaction_id=str(transaction_id) if transaction_id else None,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
            )

            return audit_log

        except Exception as e:
            # Never fail the main operation due to audit logging
            logger.error(
                "audit_log_failed",
                action=action.value,
                error=str(e),
            )
            # Return a mock entry for type safety
            return AuditLogModel(
                id=uuid4(),
                action=action.value,
                details={"error": "Failed to persist audit log"},
            )

    async def log_auth_action(
        self,
        action: AuditAction,
        user_id: UUID | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Log an authentication-related action."""
        return await self.log(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={**(details or {}), "success": success},
        )

    async def log_transaction_action(
        self,
        action: AuditAction,
        transaction_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Log a transaction-related action."""
        return await self.log(
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            transaction_id=transaction_id,
            resource_type="transaction",
            resource_id=transaction_id,
            details=details,
        )

    async def log_document_action(
        self,
        action: AuditAction,
        document_id: UUID,
        transaction_id: UUID,
        user_id: UUID | None,
        organization_id: UUID,
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Log a document-related action."""
        return await self.log(
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            transaction_id=transaction_id,
            resource_type="document",
            resource_id=document_id,
            details=details,
        )

    async def log_agent_action(
        self,
        action: AuditAction,
        agent_type: str,
        transaction_id: UUID,
        organization_id: UUID,
        execution_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Log an AI agent action."""
        return await self.log(
            action=action,
            organization_id=organization_id,
            transaction_id=transaction_id,
            agent_type=agent_type,
            resource_type="agent_execution",
            resource_id=execution_id,
            details=details,
        )

    async def get_transaction_history(
        self,
        transaction_id: UUID,
        limit: int = 100,
    ) -> list[AuditLogModel]:
        """Get audit history for a transaction."""
        from sqlalchemy import select

        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.transaction_id == transaction_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_history(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> list[AuditLogModel]:
        """Get audit history for a user."""
        from sqlalchemy import select

        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


def get_audit_service(session: AsyncSession) -> AuditService:
    """Factory function for AuditService."""
    return AuditService(session)
