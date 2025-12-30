"""Priority service - transaction health scoring and priority management."""

from datetime import date, datetime, timedelta
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import (
    TransactionModel,
    DeadlineModel,
    DocumentModel,
    CommunicationLogModel,
)


class HealthStatus:
    """Transaction health status constants."""

    CRITICAL = "critical"  # Red - Immediate attention needed
    ATTENTION = "attention"  # Yellow - Issues need addressing
    ON_TRACK = "on_track"  # Green - Everything proceeding normally


class PriorityLevel:
    """Priority level constants."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# Scoring weights for health calculation
HEALTH_WEIGHTS = {
    "days_to_closing": {
        "0-3": 30,   # Very close to closing
        "4-7": 20,   # Close to closing
        "8-14": 10,  # Approaching closing
        "15+": 0,    # Comfortable timeline
    },
    "overdue_deadline": 25,  # Per overdue deadline
    "due_soon_deadline": 10,  # Per deadline due in 3 days
    "pending_review": 10,     # Per document pending review
    "missing_required_doc": 15,  # Per missing required document
    "stalled_communication": 10,  # Communication awaiting response > 48h
}

# Status thresholds
CRITICAL_THRESHOLD = 70
ATTENTION_THRESHOLD = 40


class PriorityService:
    """
    Service for calculating transaction priority and health scores.

    Handles:
    - Calculating health scores based on multiple factors
    - Determining transaction status (critical/attention/on_track)
    - Generating priority-sorted transaction lists
    - Identifying issues that need attention
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate_health(
        self,
        transaction_id: UUID,
    ) -> tuple[int, str, list[str]]:
        """
        Calculate health score for a transaction.

        Returns:
            tuple: (score 0-100, status, list of issues)
        """
        score = 0
        issues: list[str] = []

        # Get transaction
        tx_stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        tx_result = await self.session.execute(tx_stmt)
        transaction = tx_result.scalar_one_or_none()

        if not transaction:
            return 0, HealthStatus.ON_TRACK, []

        today = date.today()

        # Factor 1: Days to closing
        if transaction.closing_date:
            days_to_close = (transaction.closing_date - today).days
            if days_to_close <= 3:
                score += HEALTH_WEIGHTS["days_to_closing"]["0-3"]
                issues.append(f"Closing in {days_to_close} days")
            elif days_to_close <= 7:
                score += HEALTH_WEIGHTS["days_to_closing"]["4-7"]
            elif days_to_close <= 14:
                score += HEALTH_WEIGHTS["days_to_closing"]["8-14"]

        # Factor 2: Overdue deadlines
        overdue_stmt = select(func.count()).select_from(DeadlineModel).where(
            and_(
                DeadlineModel.transaction_id == transaction_id,
                DeadlineModel.due_date < today,
                DeadlineModel.status.notin_(["completed", "waived"]),
            )
        )
        overdue_result = await self.session.execute(overdue_stmt)
        overdue_count = overdue_result.scalar() or 0

        if overdue_count > 0:
            score += overdue_count * HEALTH_WEIGHTS["overdue_deadline"]
            issues.append(f"{overdue_count} overdue deadline(s)")

        # Factor 3: Deadlines due soon (within 3 days)
        due_soon_date = today + timedelta(days=3)
        due_soon_stmt = select(func.count()).select_from(DeadlineModel).where(
            and_(
                DeadlineModel.transaction_id == transaction_id,
                DeadlineModel.due_date >= today,
                DeadlineModel.due_date <= due_soon_date,
                DeadlineModel.status.notin_(["completed", "waived"]),
            )
        )
        due_soon_result = await self.session.execute(due_soon_stmt)
        due_soon_count = due_soon_result.scalar() or 0

        if due_soon_count > 0:
            score += due_soon_count * HEALTH_WEIGHTS["due_soon_deadline"]
            issues.append(f"{due_soon_count} deadline(s) due within 3 days")

        # Factor 4: Documents pending review
        pending_stmt = select(func.count()).select_from(DocumentModel).where(
            and_(
                DocumentModel.transaction_id == transaction_id,
                DocumentModel.status == "needs_review",
            )
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_count = pending_result.scalar() or 0

        if pending_count > 0:
            score += pending_count * HEALTH_WEIGHTS["pending_review"]
            issues.append(f"{pending_count} document(s) need review")

        # Factor 5: Stalled communications (if table exists)
        try:
            stalled_cutoff = datetime.now() - timedelta(hours=48)
            stalled_stmt = select(func.count()).select_from(CommunicationLogModel).where(
                and_(
                    CommunicationLogModel.transaction_id == transaction_id,
                    CommunicationLogModel.direction == "outbound",
                    CommunicationLogModel.status == "pending_response",
                    CommunicationLogModel.sent_at < stalled_cutoff,
                )
            )
            stalled_result = await self.session.execute(stalled_stmt)
            stalled_count = stalled_result.scalar() or 0

            if stalled_count > 0:
                score += stalled_count * HEALTH_WEIGHTS["stalled_communication"]
                issues.append(f"{stalled_count} communication(s) awaiting response")
        except Exception:
            # Table might not exist yet
            pass

        # Cap score at 100
        score = min(score, 100)

        # Determine status
        if score >= CRITICAL_THRESHOLD:
            status = HealthStatus.CRITICAL
        elif score >= ATTENTION_THRESHOLD:
            status = HealthStatus.ATTENTION
        else:
            status = HealthStatus.ON_TRACK

        return score, status, issues

    async def update_transaction_health(
        self,
        transaction_id: UUID,
    ) -> TransactionModel | None:
        """
        Calculate and persist health score for a transaction.

        Returns:
            Updated transaction model
        """
        score, status, _ = await self.calculate_health(transaction_id)

        stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if transaction:
            transaction.priority_score = score
            transaction.health_status = status
            await self.session.flush()

        return transaction

    async def get_pulse_dashboard(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Get priority-based dashboard data.

        Returns transactions grouped by health status with issue summaries.
        """
        # Get active transactions
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.organization_id == organization_id,
                TransactionModel.status.in_(["active", "pending", "pending_close"]),
                TransactionModel.deleted_at.is_(None),
            )
        ).order_by(TransactionModel.priority_score.desc())

        result = await self.session.execute(stmt)
        transactions = result.scalars().all()

        critical = []
        attention = []
        on_track = []

        for tx in transactions:
            # Recalculate health if needed
            score, status, issues = await self.calculate_health(tx.id)

            tx_data = {
                "id": str(tx.id),
                "address": tx.property_address.get("street", "") if tx.property_address else "",
                "city": tx.property_address.get("city", "") if tx.property_address else "",
                "status": tx.status,
                "closing_date": str(tx.closing_date) if tx.closing_date else None,
                "priority_score": score,
                "health_status": status,
                "issues": issues,
                "purchase_price": float(tx.purchase_price) if tx.purchase_price else None,
            }

            if status == HealthStatus.CRITICAL:
                critical.append(tx_data)
            elif status == HealthStatus.ATTENTION:
                attention.append(tx_data)
            else:
                on_track.append(tx_data)

        return {
            "organization_id": str(organization_id),
            "summary": {
                "critical": len(critical),
                "attention": len(attention),
                "on_track": len(on_track),
                "total": len(transactions),
            },
            "critical": critical,
            "attention": attention,
            "on_track": on_track[:10],  # Limit on_track to recent 10
            "generated_at": datetime.now().isoformat(),
        }

    async def get_needs_attention(
        self,
        organization_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get transactions that need immediate attention.

        Returns list sorted by priority score (highest first).
        """
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.organization_id == organization_id,
                TransactionModel.status.in_(["active", "pending", "pending_close"]),
                TransactionModel.deleted_at.is_(None),
                TransactionModel.health_status.in_([HealthStatus.CRITICAL, HealthStatus.ATTENTION]),
            )
        ).order_by(TransactionModel.priority_score.desc()).limit(limit)

        result = await self.session.execute(stmt)
        transactions = result.scalars().all()

        items = []
        for tx in transactions:
            _, _, issues = await self.calculate_health(tx.id)
            items.append({
                "id": str(tx.id),
                "address": tx.property_address.get("street", "") if tx.property_address else "",
                "status": tx.status,
                "health_status": tx.health_status,
                "priority_score": tx.priority_score,
                "closing_date": str(tx.closing_date) if tx.closing_date else None,
                "issues": issues,
            })

        return items

    async def batch_update_health(
        self,
        organization_id: UUID,
    ) -> int:
        """
        Update health scores for all active transactions in an organization.

        Useful for scheduled background updates.

        Returns:
            Number of transactions updated
        """
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.organization_id == organization_id,
                TransactionModel.status.in_(["active", "pending", "pending_close"]),
                TransactionModel.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(stmt)
        transactions = result.scalars().all()

        count = 0
        for tx in transactions:
            await self.update_transaction_health(tx.id)
            count += 1

        return count


def get_priority_service(session: AsyncSession) -> PriorityService:
    """Factory function for PriorityService."""
    return PriorityService(session)
