"""Compliance report generation service."""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.repositories.transaction import TransactionRepository
from packages.db.repositories.document import DocumentRepository
from packages.db.repositories.deadline import DeadlineRepository

logger = structlog.get_logger()


class ReportType(str, Enum):
    """Types of compliance reports."""

    TRANSACTION_SUMMARY = "transaction_summary"
    DEADLINE_STATUS = "deadline_status"
    DOCUMENT_CHECKLIST = "document_checklist"
    COMPLIANCE_AUDIT = "compliance_audit"
    ORGANIZATION_OVERVIEW = "organization_overview"


class ReportFormat(str, Enum):
    """Output formats for reports."""

    HTML = "html"
    JSON = "json"


class DeadlineStatus(str, Enum):
    """Deadline compliance status."""

    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    WAIVED = "waived"


class DocumentStatus(str, Enum):
    """Document completeness status."""

    RECEIVED = "received"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    MISSING = "missing"


class PartyInfo(BaseModel):
    """Party information for report."""

    role: str
    name: str
    email: str | None = None
    phone: str | None = None


class DeadlineInfo(BaseModel):
    """Deadline information for report."""

    id: str
    name: str
    due_date: date
    status: DeadlineStatus
    days_remaining: int
    is_statutory: bool = False
    completed_at: datetime | None = None
    notes: str | None = None


class DocumentInfo(BaseModel):
    """Document information for report."""

    id: str
    document_type: str
    filename: str
    status: DocumentStatus
    uploaded_at: datetime
    verified_at: datetime | None = None
    extraction_confidence: float | None = None
    needs_review_reason: str | None = None


class ComplianceMetrics(BaseModel):
    """Compliance metrics summary."""

    total_deadlines: int = 0
    completed_deadlines: int = 0
    overdue_deadlines: int = 0
    upcoming_deadlines: int = 0
    deadline_compliance_rate: float = 0.0

    total_documents: int = 0
    verified_documents: int = 0
    pending_documents: int = 0
    needs_review_documents: int = 0
    document_completion_rate: float = 0.0

    overall_compliance_score: float = 0.0
    risk_level: str = "low"  # low, medium, high


class TransactionSummaryReport(BaseModel):
    """Transaction summary report data."""

    report_id: str
    report_type: str = ReportType.TRANSACTION_SUMMARY.value
    generated_at: datetime
    generated_by: str | None = None

    # Transaction info
    transaction_id: str
    property_address: dict[str, str]
    transaction_type: str
    status: str
    purchase_price: float | None = None
    effective_date: date | None = None
    closing_date: date | None = None
    days_to_closing: int | None = None

    # Parties
    parties: list[PartyInfo] = []

    # Compliance
    metrics: ComplianceMetrics
    deadlines: list[DeadlineInfo] = []
    documents: list[DocumentInfo] = []

    # Warnings and notes
    warnings: list[str] = []
    notes: str | None = None


class OrganizationOverviewReport(BaseModel):
    """Organization-wide overview report."""

    report_id: str
    report_type: str = ReportType.ORGANIZATION_OVERVIEW.value
    generated_at: datetime
    organization_id: str
    organization_name: str

    # Summary stats
    total_transactions: int = 0
    active_transactions: int = 0
    pending_close_transactions: int = 0
    closed_this_month: int = 0

    # Compliance overview
    overall_compliance_rate: float = 0.0
    transactions_at_risk: int = 0

    # Recent activity
    upcoming_closings: list[dict[str, Any]] = []
    overdue_deadlines: list[dict[str, Any]] = []
    documents_needing_review: int = 0


class ReportService:
    """
    Service for generating compliance reports.

    Generates various reports for transaction coordinators including:
    - Transaction summaries
    - Deadline status reports
    - Document checklists
    - Compliance audit reports
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.document_repo = DocumentRepository(session)
        self.deadline_repo = DeadlineRepository(session)

    async def generate_transaction_summary(
        self,
        transaction_id: UUID,
        user_name: str | None = None,
    ) -> TransactionSummaryReport:
        """
        Generate a comprehensive transaction summary report.

        Includes property details, parties, deadlines, documents,
        and compliance metrics.
        """
        # Fetch transaction with relations
        transaction = await self.transaction_repo.get_with_relations(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Get deadlines
        deadlines = await self.deadline_repo.get_by_transaction(transaction_id)

        # Get documents
        documents = await self.document_repo.get_by_transaction(transaction_id)

        # Calculate days to closing
        days_to_closing = None
        if transaction.closing_date:
            delta = transaction.closing_date - date.today()
            days_to_closing = delta.days

        # Build deadline info
        deadline_infos = []
        completed_deadlines = 0
        overdue_deadlines = 0
        upcoming_deadlines = 0

        for dl in deadlines:
            days_remaining = (dl.due_date - date.today()).days

            if dl.status == "completed":
                status = DeadlineStatus.COMPLETED
                completed_deadlines += 1
            elif dl.status == "waived":
                status = DeadlineStatus.WAIVED
                completed_deadlines += 1
            elif days_remaining < 0:
                status = DeadlineStatus.OVERDUE
                overdue_deadlines += 1
            elif days_remaining <= 3:
                status = DeadlineStatus.DUE_SOON
                upcoming_deadlines += 1
            else:
                status = DeadlineStatus.ON_TRACK
                upcoming_deadlines += 1

            deadline_infos.append(
                DeadlineInfo(
                    id=str(dl.id),
                    name=dl.name,
                    due_date=dl.due_date,
                    status=status,
                    days_remaining=days_remaining,
                    is_statutory=dl.deadline_type.startswith("statutory_"),
                    completed_at=dl.completed_at,
                    notes=dl.notes,
                )
            )

        # Sort deadlines by due date
        deadline_infos.sort(key=lambda d: d.due_date)

        # Build document info
        document_infos = []
        verified_docs = 0
        pending_docs = 0
        needs_review_docs = 0

        for doc in documents:
            if doc.status == "verified":
                status = DocumentStatus.VERIFIED
                verified_docs += 1
            elif doc.needs_review_reason:
                status = DocumentStatus.NEEDS_REVIEW
                needs_review_docs += 1
            elif doc.status == "extracted":
                status = DocumentStatus.RECEIVED
                verified_docs += 1
            else:
                status = DocumentStatus.PENDING
                pending_docs += 1

            document_infos.append(
                DocumentInfo(
                    id=str(doc.id),
                    document_type=doc.document_type,
                    filename=doc.filename,
                    status=status,
                    uploaded_at=doc.uploaded_at,
                    verified_at=doc.verified_at,
                    extraction_confidence=doc.extraction_confidence,
                    needs_review_reason=doc.needs_review_reason,
                )
            )

        # Calculate metrics
        total_deadlines = len(deadlines)
        deadline_compliance = (
            completed_deadlines / total_deadlines if total_deadlines > 0 else 1.0
        )

        total_documents = len(documents)
        document_completion = (
            verified_docs / total_documents if total_documents > 0 else 0.0
        )

        # Overall compliance score (weighted average)
        overall_score = (deadline_compliance * 0.6 + document_completion * 0.4) * 100

        # Determine risk level
        if overdue_deadlines > 0 or overall_score < 50:
            risk_level = "high"
        elif upcoming_deadlines > 0 and days_to_closing and days_to_closing < 7:
            risk_level = "medium"
        elif overall_score < 80:
            risk_level = "medium"
        else:
            risk_level = "low"

        metrics = ComplianceMetrics(
            total_deadlines=total_deadlines,
            completed_deadlines=completed_deadlines,
            overdue_deadlines=overdue_deadlines,
            upcoming_deadlines=upcoming_deadlines,
            deadline_compliance_rate=deadline_compliance * 100,
            total_documents=total_documents,
            verified_documents=verified_docs,
            pending_documents=pending_docs,
            needs_review_documents=needs_review_docs,
            document_completion_rate=document_completion * 100,
            overall_compliance_score=overall_score,
            risk_level=risk_level,
        )

        # Build parties list
        parties = [
            PartyInfo(
                role=p.get("role", "unknown"),
                name=p.get("name", "Unknown"),
                email=p.get("email"),
                phone=p.get("phone"),
            )
            for p in (transaction.parties or [])
        ]

        # Generate warnings
        warnings = []
        if overdue_deadlines > 0:
            warnings.append(f"{overdue_deadlines} deadline(s) are overdue")
        if needs_review_docs > 0:
            warnings.append(f"{needs_review_docs} document(s) need review")
        if days_to_closing is not None and days_to_closing < 0:
            warnings.append("Closing date has passed")
        elif days_to_closing is not None and days_to_closing <= 7:
            warnings.append(f"Closing in {days_to_closing} days")

        return TransactionSummaryReport(
            report_id=str(uuid4()),
            generated_at=datetime.utcnow(),
            generated_by=user_name,
            transaction_id=str(transaction_id),
            property_address=transaction.property_address,
            transaction_type=transaction.transaction_type,
            status=transaction.status,
            purchase_price=float(transaction.purchase_price) if transaction.purchase_price else None,
            effective_date=transaction.effective_date,
            closing_date=transaction.closing_date,
            days_to_closing=days_to_closing,
            parties=parties,
            metrics=metrics,
            deadlines=deadline_infos,
            documents=document_infos,
            warnings=warnings,
        )

    async def generate_organization_overview(
        self,
        organization_id: UUID,
        organization_name: str,
    ) -> OrganizationOverviewReport:
        """Generate organization-wide overview report."""
        # Get transaction counts
        total = await self.transaction_repo.count_by_organization(organization_id)
        active = await self.transaction_repo.count_by_organization(
            organization_id, status="active"
        )
        pending_close = await self.transaction_repo.count_by_organization(
            organization_id, status="pending_close"
        )
        closed_month = await self.transaction_repo.count_closed_this_month(organization_id)

        # Get upcoming closings
        upcoming = await self.transaction_repo.get_active_with_upcoming_closing(
            organization_id, within_days=14
        )
        upcoming_closings = [
            {
                "id": str(t.id),
                "address": t.property_address.get("street", "Unknown"),
                "closing_date": str(t.closing_date) if t.closing_date else None,
                "days_remaining": (t.closing_date - date.today()).days if t.closing_date else None,
            }
            for t in upcoming
        ]

        # Get overdue deadlines count
        all_deadlines = await self.deadline_repo.get_overdue_by_organization(organization_id)
        overdue_deadlines = [
            {
                "id": str(d.id),
                "name": d.name,
                "due_date": str(d.due_date),
                "transaction_id": str(d.transaction_id),
            }
            for d in all_deadlines[:10]  # Limit to 10
        ]

        # Calculate overall compliance rate
        transactions_at_risk = len([d for d in all_deadlines])

        # Get documents needing review
        docs_review = await self.document_repo.count_needing_review_by_organization(
            organization_id
        )

        compliance_rate = 100.0
        if total > 0:
            compliance_rate = ((total - transactions_at_risk) / total) * 100

        return OrganizationOverviewReport(
            report_id=str(uuid4()),
            generated_at=datetime.utcnow(),
            organization_id=str(organization_id),
            organization_name=organization_name,
            total_transactions=total,
            active_transactions=active,
            pending_close_transactions=pending_close,
            closed_this_month=closed_month,
            overall_compliance_rate=compliance_rate,
            transactions_at_risk=transactions_at_risk,
            upcoming_closings=upcoming_closings,
            overdue_deadlines=overdue_deadlines,
            documents_needing_review=docs_review,
        )

    def render_html_report(self, report: TransactionSummaryReport) -> str:
        """Render transaction summary report as HTML."""
        # Format property address
        addr = report.property_address
        address_str = f"{addr.get('street', '')}"
        if addr.get('unit'):
            address_str += f" {addr['unit']}"
        address_str += f", {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zip_code', '')}"

        # Risk badge color
        risk_colors = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}
        risk_color = risk_colors.get(report.metrics.risk_level, "#6b7280")

        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Transaction Summary - {address_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1f2937; line-height: 1.5; padding: 2rem; max-width: 900px; margin: 0 auto; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        h2 {{ font-size: 1.25rem; margin: 1.5rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e5e7eb; }}
        h3 {{ font-size: 1rem; margin: 1rem 0 0.5rem; }}
        .header {{ margin-bottom: 2rem; }}
        .meta {{ color: #6b7280; font-size: 0.875rem; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }}
        .card {{ background: #f9fafb; border-radius: 0.5rem; padding: 1rem; }}
        .card-title {{ font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem; }}
        .card-value {{ font-size: 1.5rem; font-weight: 600; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem 0; }}
        .metric {{ text-align: center; padding: 1rem; background: #f3f4f6; border-radius: 0.5rem; }}
        .metric-value {{ font-size: 1.75rem; font-weight: 700; }}
        .metric-label {{ font-size: 0.75rem; color: #6b7280; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; font-size: 0.875rem; }}
        .status {{ padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 500; }}
        .status-on_track {{ background: #dcfce7; color: #166534; }}
        .status-due_soon {{ background: #fef3c7; color: #92400e; }}
        .status-overdue {{ background: #fee2e2; color: #991b1b; }}
        .status-completed {{ background: #dbeafe; color: #1e40af; }}
        .warnings {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem; margin: 1rem 0; }}
        .warning-item {{ margin: 0.25rem 0; }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; font-size: 0.75rem; color: #9ca3af; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{address_str}</h1>
        <p class="meta">
            Transaction ID: {report.transaction_id} |
            Generated: {report.generated_at.strftime('%B %d, %Y at %I:%M %p')}
            {f' by {report.generated_by}' if report.generated_by else ''}
        </p>
        <p style="margin-top: 0.5rem;">
            <span class="badge" style="background: {risk_color}; color: white;">
                {report.metrics.risk_level.upper()} RISK
            </span>
            <span class="badge" style="background: #e5e7eb;">
                {report.status.upper().replace('_', ' ')}
            </span>
        </p>
    </div>
"""

        # Warnings section
        if report.warnings:
            html += """
    <div class="warnings">
        <strong>Attention Required:</strong>
"""
            for warning in report.warnings:
                html += f'        <div class="warning-item">⚠️ {warning}</div>\n'
            html += "    </div>\n"

        # Metrics section
        html += f"""
    <h2>Compliance Overview</h2>
    <div class="metrics">
        <div class="metric">
            <div class="metric-value" style="color: {'#22c55e' if report.metrics.overall_compliance_score >= 80 else '#f59e0b' if report.metrics.overall_compliance_score >= 50 else '#ef4444'}">
                {report.metrics.overall_compliance_score:.0f}%
            </div>
            <div class="metric-label">Overall Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.metrics.completed_deadlines}/{report.metrics.total_deadlines}</div>
            <div class="metric-label">Deadlines Complete</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.metrics.verified_documents}/{report.metrics.total_documents}</div>
            <div class="metric-label">Documents Verified</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.days_to_closing if report.days_to_closing is not None else 'N/A'}</div>
            <div class="metric-label">Days to Close</div>
        </div>
    </div>

    <h2>Transaction Details</h2>
    <div class="grid">
        <div class="card">
            <div class="card-title">Purchase Price</div>
            <div class="card-value">${report.purchase_price:,.2f}</div>
        </div>
        <div class="card">
            <div class="card-title">Closing Date</div>
            <div class="card-value">{report.closing_date.strftime('%B %d, %Y') if report.closing_date else 'TBD'}</div>
        </div>
    </div>
"""

        # Parties section
        if report.parties:
            html += """
    <h2>Parties</h2>
    <table>
        <thead>
            <tr>
                <th>Role</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
            </tr>
        </thead>
        <tbody>
"""
            for party in report.parties:
                html += f"""
            <tr>
                <td>{party.role.replace('_', ' ').title()}</td>
                <td>{party.name}</td>
                <td>{party.email or '-'}</td>
                <td>{party.phone or '-'}</td>
            </tr>
"""
            html += """
        </tbody>
    </table>
"""

        # Deadlines section
        html += """
    <h2>Deadline Timeline</h2>
    <table>
        <thead>
            <tr>
                <th>Deadline</th>
                <th>Due Date</th>
                <th>Days</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
"""
        for dl in report.deadlines:
            status_class = f"status-{dl.status.value}"
            days_text = f"{dl.days_remaining}d" if dl.days_remaining >= 0 else f"{abs(dl.days_remaining)}d ago"
            html += f"""
            <tr>
                <td>{dl.name}{'*' if dl.is_statutory else ''}</td>
                <td>{dl.due_date.strftime('%m/%d/%Y')}</td>
                <td>{days_text}</td>
                <td><span class="status {status_class}">{dl.status.value.replace('_', ' ').upper()}</span></td>
            </tr>
"""
        html += """
        </tbody>
    </table>
    <p class="meta">* Statutory deadline</p>
"""

        # Documents section
        html += """
    <h2>Document Checklist</h2>
    <table>
        <thead>
            <tr>
                <th>Document Type</th>
                <th>Filename</th>
                <th>Status</th>
                <th>Uploaded</th>
            </tr>
        </thead>
        <tbody>
"""
        for doc in report.documents:
            status_class = f"status-{doc.status.value}"
            html += f"""
            <tr>
                <td>{doc.document_type.replace('_', ' ').title()}</td>
                <td>{doc.filename}</td>
                <td><span class="status {status_class}">{doc.status.value.replace('_', ' ').upper()}</span></td>
                <td>{doc.uploaded_at.strftime('%m/%d/%Y')}</td>
            </tr>
"""
        html += """
        </tbody>
    </table>
"""

        # Footer
        html += f"""
    <div class="footer">
        <p>This report was generated by Airport Transaction Coordinator. Report ID: {report.report_id}</p>
        <p>This report is for informational purposes only and does not constitute legal advice.</p>
    </div>
</body>
</html>
"""
        return html


def get_report_service(session: AsyncSession) -> ReportService:
    """Factory function for ReportService."""
    return ReportService(session)
