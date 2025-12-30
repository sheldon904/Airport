"""Audit log API endpoints.

Provides access to audit trail data for compliance and monitoring.
Supports search, filtering, and export functionality.
"""

from datetime import datetime, date, timezone
from typing import Annotated
from uuid import UUID
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.session import get_db
from packages.db.models import AuditLogModel, TransactionModel
from services.api.dependencies import CurrentUserDep, AdminUserDep

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    transaction_id: UUID | None
    user_id: UUID | None
    action: str
    agent_type: str | None
    resource_type: str | None
    resource_id: UUID | None
    details: dict
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    property_address: str | None = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditSummary(BaseModel):
    """Summary statistics for audit logs."""

    total_logs: int
    actions_by_type: dict[str, int]
    logs_by_agent: dict[str, int]
    logs_today: int
    logs_this_week: int


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: AdminUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    transaction_id: UUID | None = Query(None, description="Filter by transaction ID"),
    action: str | None = Query(None, description="Filter by action type"),
    agent_type: str | None = Query(None, description="Filter by agent type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    start_date: date | None = Query(None, description="Start date filter"),
    end_date: date | None = Query(None, description="End date filter"),
    search: str | None = Query(None, description="Search in action and details"),
) -> AuditLogListResponse:
    """
    List audit logs with filtering and pagination.

    Only accessible by admin users. Returns audit logs for the user's organization.
    """
    # Build base query - join with transactions to filter by organization
    base_query = (
        select(AuditLogModel)
        .outerjoin(TransactionModel, AuditLogModel.transaction_id == TransactionModel.id)
        .where(
            or_(
                TransactionModel.organization_id == current_user.organization_id,
                AuditLogModel.transaction_id.is_(None),  # Include logs without transactions
            )
        )
    )

    # Apply filters
    filters = []

    if transaction_id:
        filters.append(AuditLogModel.transaction_id == transaction_id)
    if action:
        filters.append(AuditLogModel.action.ilike(f"%{action}%"))
    if agent_type:
        filters.append(AuditLogModel.agent_type == agent_type)
    if resource_type:
        filters.append(AuditLogModel.resource_type == resource_type)
    if start_date:
        filters.append(AuditLogModel.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(AuditLogModel.created_at <= datetime.combine(end_date, datetime.max.time()))
    if search:
        filters.append(
            or_(
                AuditLogModel.action.ilike(f"%{search}%"),
                AuditLogModel.details.cast(str).ilike(f"%{search}%"),
            )
        )

    if filters:
        base_query = base_query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = (
        base_query
        .order_by(desc(AuditLogModel.created_at))
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response with property address if available
    items = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "transaction_id": log.transaction_id,
            "user_id": log.user_id,
            "action": log.action,
            "agent_type": log.agent_type,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
            "property_address": None,
        }
        if log.transaction:
            addr = log.transaction.property_address
            if addr:
                log_dict["property_address"] = f"{addr.get('street', '')}, {addr.get('city', '')}"
        items.append(AuditLogResponse(**log_dict))

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/summary", response_model=AuditSummary)
async def get_audit_summary(
    current_user: AdminUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    transaction_id: UUID | None = Query(None, description="Filter by transaction"),
) -> AuditSummary:
    """
    Get summary statistics for audit logs.

    Returns counts by action type, agent type, and time periods.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), datetime.min.time())
    week_start = today_start - timedelta(days=7)

    # Base query for organization
    base_filter = (
        select(AuditLogModel)
        .outerjoin(TransactionModel, AuditLogModel.transaction_id == TransactionModel.id)
        .where(
            or_(
                TransactionModel.organization_id == current_user.organization_id,
                AuditLogModel.transaction_id.is_(None),
            )
        )
    )

    if transaction_id:
        base_filter = base_filter.where(AuditLogModel.transaction_id == transaction_id)

    # Get total count
    total_query = select(func.count()).select_from(base_filter.subquery())
    total_result = await db.execute(total_query)
    total_logs = total_result.scalar() or 0

    # Get actions by type
    action_query = (
        select(AuditLogModel.action, func.count(AuditLogModel.id))
        .select_from(base_filter.subquery().alias("base"))
        .join(AuditLogModel, AuditLogModel.id == base_filter.subquery().c.id)
        .group_by(AuditLogModel.action)
    )
    # Simplified query for action counts
    action_result = await db.execute(
        select(AuditLogModel.action, func.count(AuditLogModel.id))
        .group_by(AuditLogModel.action)
    )
    actions_by_type = {row[0]: row[1] for row in action_result.all()}

    # Get logs by agent type
    agent_result = await db.execute(
        select(AuditLogModel.agent_type, func.count(AuditLogModel.id))
        .where(AuditLogModel.agent_type.isnot(None))
        .group_by(AuditLogModel.agent_type)
    )
    logs_by_agent = {row[0]: row[1] for row in agent_result.all()}

    # Get today's count
    today_result = await db.execute(
        select(func.count(AuditLogModel.id))
        .where(AuditLogModel.created_at >= today_start)
    )
    logs_today = today_result.scalar() or 0

    # Get this week's count
    week_result = await db.execute(
        select(func.count(AuditLogModel.id))
        .where(AuditLogModel.created_at >= week_start)
    )
    logs_this_week = week_result.scalar() or 0

    return AuditSummary(
        total_logs=total_logs,
        actions_by_type=actions_by_type,
        logs_by_agent=logs_by_agent,
        logs_today=logs_today,
        logs_this_week=logs_this_week,
    )


@router.get("/transaction/{transaction_id}", response_model=list[AuditLogResponse])
async def get_transaction_audit_logs(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AuditLogResponse]:
    """
    Get all audit logs for a specific transaction.

    Returns the complete audit trail for compliance review.
    """
    # Verify user has access to transaction
    tx_result = await db.execute(
        select(TransactionModel)
        .where(
            TransactionModel.id == transaction_id,
            TransactionModel.organization_id == current_user.organization_id,
        )
    )
    transaction = tx_result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Get audit logs
    result = await db.execute(
        select(AuditLogModel)
        .where(AuditLogModel.transaction_id == transaction_id)
        .order_by(desc(AuditLogModel.created_at))
    )
    logs = result.scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            transaction_id=log.transaction_id,
            user_id=log.user_id,
            action=log.action,
            agent_type=log.agent_type,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/export")
async def export_audit_logs(
    current_user: AdminUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    transaction_id: UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> StreamingResponse:
    """
    Export audit logs to CSV or JSON format.

    Useful for compliance reporting and external analysis.
    """
    # Build query with filters
    query = (
        select(AuditLogModel)
        .outerjoin(TransactionModel, AuditLogModel.transaction_id == TransactionModel.id)
        .where(
            or_(
                TransactionModel.organization_id == current_user.organization_id,
                AuditLogModel.transaction_id.is_(None),
            )
        )
    )

    filters = []
    if transaction_id:
        filters.append(AuditLogModel.transaction_id == transaction_id)
    if start_date:
        filters.append(AuditLogModel.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(AuditLogModel.created_at <= datetime.combine(end_date, datetime.max.time()))

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(desc(AuditLogModel.created_at))

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Transaction ID", "User ID", "Action", "Agent Type",
            "Resource Type", "Resource ID", "Details", "IP Address",
            "User Agent", "Created At"
        ])

        for log in logs:
            writer.writerow([
                str(log.id),
                str(log.transaction_id) if log.transaction_id else "",
                str(log.user_id) if log.user_id else "",
                log.action,
                log.agent_type or "",
                log.resource_type or "",
                str(log.resource_id) if log.resource_id else "",
                str(log.details),
                log.ip_address or "",
                log.user_agent or "",
                log.created_at.isoformat(),
            ])

        output.seek(0)
        filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        # Generate JSON
        import json

        data = [
            {
                "id": str(log.id),
                "transaction_id": str(log.transaction_id) if log.transaction_id else None,
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "agent_type": log.agent_type,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

        filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@router.get("/actions")
async def get_action_types(
    current_user: AdminUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """
    Get list of distinct action types in audit logs.

    Useful for populating filter dropdowns.
    """
    result = await db.execute(
        select(AuditLogModel.action)
        .distinct()
        .order_by(AuditLogModel.action)
    )
    return [row[0] for row in result.all()]


@router.get("/agents")
async def get_agent_types(
    current_user: AdminUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """
    Get list of distinct agent types in audit logs.

    Useful for filtering by AI agent activity.
    """
    result = await db.execute(
        select(AuditLogModel.agent_type)
        .where(AuditLogModel.agent_type.isnot(None))
        .distinct()
        .order_by(AuditLogModel.agent_type)
    )
    return [row[0] for row in result.all()]
