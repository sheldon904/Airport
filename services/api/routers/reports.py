"""Compliance report generation endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from packages.core.services.audit import AuditAction, AuditService
from packages.core.services.report import (
    ReportFormat,
    ReportService,
    ReportType,
    TransactionSummaryReport,
    OrganizationOverviewReport,
)
from services.api.dependencies import (
    CurrentUserDep,
    DbSessionDep,
    TransactionServiceDep,
)

router = APIRouter()


# === Request/Response Models ===


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    report_type: ReportType = ReportType.TRANSACTION_SUMMARY
    format: ReportFormat = ReportFormat.JSON


class ReportResponse(BaseModel):
    """Generic report response wrapper."""

    report_id: str
    report_type: str
    generated_at: datetime
    format: str


# === Endpoints ===


@router.post(
    "/transactions/{transaction_id}",
    response_model=TransactionSummaryReport,
    summary="Generate transaction summary report",
)
async def generate_transaction_report(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    db: DbSessionDep,
    transaction_service: TransactionServiceDep,
    format: ReportFormat = ReportFormat.JSON,
) -> TransactionSummaryReport | Response:
    """
    Generate a comprehensive transaction summary report.

    Includes:
    - Property details and parties
    - Compliance metrics and risk assessment
    - Deadline timeline with status
    - Document checklist with verification status

    Returns JSON by default, or HTML if format=html.
    """
    # Verify user has access to this transaction
    transaction = await transaction_service.get_transaction(
        transaction_id=transaction_id,
        organization_id=current_user.organization_id,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Generate report
    report_service = ReportService(db)
    report = await report_service.generate_transaction_summary(
        transaction_id=transaction_id,
        user_name=current_user.full_name,
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.REPORT_GENERATED,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        resource_type="report",
        details={
            "report_type": ReportType.TRANSACTION_SUMMARY.value,
            "format": format.value,
            "report_id": report.report_id,
        },
    )
    await db.commit()

    # Return HTML if requested
    if format == ReportFormat.HTML:
        html_content = report_service.render_html_report(report)
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'inline; filename="transaction-report-{transaction_id}.html"'
            },
        )

    return report


@router.get(
    "/transactions/{transaction_id}/download",
    summary="Download transaction report as HTML",
)
async def download_transaction_report(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    db: DbSessionDep,
    transaction_service: TransactionServiceDep,
) -> Response:
    """
    Download a transaction summary report as an HTML file.

    Suitable for printing or saving offline.
    """
    # Verify user has access to this transaction
    transaction = await transaction_service.get_transaction(
        transaction_id=transaction_id,
        organization_id=current_user.organization_id,
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Generate report
    report_service = ReportService(db)
    report = await report_service.generate_transaction_summary(
        transaction_id=transaction_id,
        user_name=current_user.full_name,
    )

    # Render HTML
    html_content = report_service.render_html_report(report)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.REPORT_DOWNLOADED,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        resource_type="report",
        details={
            "report_type": ReportType.TRANSACTION_SUMMARY.value,
            "report_id": report.report_id,
        },
    )
    await db.commit()

    # Build filename from address
    addr = transaction.property_address
    filename = f"report-{addr.get('street', 'transaction').replace(' ', '-')}.html"

    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get(
    "/organization",
    response_model=OrganizationOverviewReport,
    summary="Generate organization overview report",
)
async def generate_organization_report(
    current_user: CurrentUserDep,
    db: DbSessionDep,
) -> OrganizationOverviewReport:
    """
    Generate an organization-wide overview report.

    Includes:
    - Transaction counts and status summary
    - Overall compliance rate
    - Upcoming closings
    - Overdue deadlines
    - Documents needing review

    Requires admin or broker role.
    """
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or broker role required",
        )

    # Get organization name (would need to fetch from DB in real implementation)
    organization_name = "Your Organization"

    # Generate report
    report_service = ReportService(db)
    report = await report_service.generate_organization_overview(
        organization_id=current_user.organization_id,
        organization_name=organization_name,
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.REPORT_GENERATED,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        resource_type="report",
        details={
            "report_type": ReportType.ORGANIZATION_OVERVIEW.value,
            "report_id": report.report_id,
        },
    )
    await db.commit()

    return report


@router.get(
    "/dashboard",
    summary="Get dashboard metrics",
)
async def get_dashboard_metrics(
    current_user: CurrentUserDep,
    db: DbSessionDep,
) -> dict:
    """
    Get quick dashboard metrics for the current user's organization.

    Returns counts and key metrics for the dashboard display.
    """
    from packages.db.repositories.transaction import TransactionRepository
    from packages.db.repositories.document import DocumentRepository
    from packages.db.repositories.deadline import DeadlineRepository

    transaction_repo = TransactionRepository(db)
    document_repo = DocumentRepository(db)
    deadline_repo = DeadlineRepository(db)

    org_id = current_user.organization_id

    # Get counts
    active_transactions = await transaction_repo.count_by_organization(
        org_id, status="active"
    )
    pending_close = await transaction_repo.count_by_organization(
        org_id, status="pending_close"
    )
    total_active = active_transactions + pending_close

    # Get documents needing review
    docs_review = await document_repo.count_needing_review_by_organization(org_id)

    # Get upcoming deadlines (next 7 days)
    upcoming_deadlines = await deadline_repo.count_upcoming_by_organization(org_id, days=7)

    # Get overdue deadlines
    overdue = await deadline_repo.get_overdue_by_organization(org_id)

    # Closed this month
    closed_month = await transaction_repo.count_closed_this_month(org_id)

    # Get upcoming closings
    upcoming_closings = await transaction_repo.get_active_with_upcoming_closing(
        org_id, within_days=14
    )

    return {
        "active_transactions": total_active,
        "pending_deadlines": upcoming_deadlines,
        "documents_needing_review": docs_review,
        "completed_this_month": closed_month,
        "overdue_deadlines": len(overdue),
        "upcoming_closings": [
            {
                "id": str(t.id),
                "address": t.property_address.get("street", "Unknown"),
                "closing_date": str(t.closing_date) if t.closing_date else None,
            }
            for t in upcoming_closings[:5]
        ],
    }
