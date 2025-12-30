"""Communication log service - tracks all transaction communications."""

from datetime import datetime, timedelta
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import CommunicationLogModel


class CommunicationDirection:
    """Communication direction constants."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CommunicationChannel:
    """Communication channel constants."""

    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    PORTAL = "portal"
    IN_PERSON = "in_person"


class CommunicationStatus:
    """Communication status constants."""

    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    PENDING_RESPONSE = "pending_response"
    RESPONDED = "responded"


# Topic keywords for auto-categorization
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "earnest_money": [
        "deposit", "earnest", "escrow", "receipt", "emd", "good faith"
    ],
    "inspection": [
        "inspection", "inspector", "repair", "defect", "condition", "wdo",
        "termite", "pest", "home inspection"
    ],
    "financing": [
        "loan", "lender", "mortgage", "approval", "underwriting", "pre-approval",
        "financing", "bank", "credit", "rate lock"
    ],
    "appraisal": [
        "appraisal", "appraiser", "value", "valuation", "fha", "va"
    ],
    "title": [
        "title", "commitment", "search", "lien", "encumbrance", "clear to close",
        "closing disclosure", "cd", "settlement"
    ],
    "closing": [
        "closing", "settlement", "walkthrough", "walk-through", "final", "keys",
        "possession", "wire", "funds"
    ],
    "hoa": [
        "hoa", "association", "condo", "estoppel", "assessment", "fees"
    ],
    "insurance": [
        "insurance", "homeowners", "hazard", "flood", "wind", "policy", "binder"
    ],
    "survey": [
        "survey", "surveyor", "boundary", "easement", "encroachment"
    ],
    "disclosure": [
        "disclosure", "seller disclosure", "spd", "lead paint", "radon"
    ],
}


class CommunicationLogService:
    """
    Service for logging and tracking transaction communications.

    Handles:
    - Recording inbound and outbound communications
    - Auto-categorizing communications by topic
    - Tracking communication status and responses
    - Generating communication summaries and timelines
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_communication(
        self,
        *,
        transaction_id: UUID | None,
        organization_id: UUID,
        direction: str,
        channel: str = CommunicationChannel.EMAIL,
        sender: str,
        recipients: list[str],
        subject: str | None = None,
        body: str,
        topic: str | None = None,
        status: str = CommunicationStatus.SENT,
        related_document_id: UUID | None = None,
        related_deadline_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommunicationLogModel:
        """
        Log a communication.

        Args:
            transaction_id: Associated transaction (optional for org-level comms)
            organization_id: Organization ID
            direction: 'inbound' or 'outbound'
            channel: Communication channel (email, sms, etc.)
            sender: Sender email/phone
            recipients: List of recipient emails/phones
            subject: Message subject
            body: Message body
            topic: Topic category (auto-detected if not provided)
            status: Communication status
            related_document_id: Related document if applicable
            related_deadline_id: Related deadline if applicable
            metadata: Additional metadata

        Returns:
            Created CommunicationLogModel
        """
        # Auto-detect topic if not provided
        if topic is None:
            topic = self.categorize_communication(subject or "", body)

        # Create body preview (first 500 chars)
        body_preview = body[:500] if len(body) > 500 else body

        log_entry = CommunicationLogModel(
            id=uuid4(),
            transaction_id=transaction_id,
            organization_id=organization_id,
            direction=direction,
            channel=channel,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_preview=body_preview,
            full_body=body,
            topic=topic,
            status=status,
            related_document_id=related_document_id,
            related_deadline_id=related_deadline_id,
            metadata=metadata or {},
            sent_at=datetime.now() if status == CommunicationStatus.SENT else None,
            created_at=datetime.now(),
        )

        self.session.add(log_entry)
        await self.session.flush()

        return log_entry

    def categorize_communication(self, subject: str, body: str) -> str:
        """
        Auto-categorize a communication based on content.

        Returns the most likely topic or 'general' if no match.
        """
        text = f"{subject} {body}".lower()

        # Count keyword matches per topic
        scores: dict[str, int] = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[topic] = score

        if scores:
            # Return topic with highest score
            return max(scores, key=scores.get)  # type: ignore

        return "general"

    async def get_transaction_communications(
        self,
        transaction_id: UUID,
        *,
        topic: str | None = None,
        direction: str | None = None,
        channel: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[CommunicationLogModel]:
        """Get communications for a transaction with optional filters."""
        conditions = [CommunicationLogModel.transaction_id == transaction_id]

        if topic:
            conditions.append(CommunicationLogModel.topic == topic)
        if direction:
            conditions.append(CommunicationLogModel.direction == direction)
        if channel:
            conditions.append(CommunicationLogModel.channel == channel)
        if since:
            conditions.append(CommunicationLogModel.created_at >= since)

        stmt = (
            select(CommunicationLogModel)
            .where(and_(*conditions))
            .order_by(CommunicationLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_communication_summary(
        self,
        transaction_id: UUID,
    ) -> dict[str, Any]:
        """
        Get a summary of communications for a transaction.

        Useful for answering "where are we with..." questions.

        Returns:
            Summary by topic with counts and last activity
        """
        # Get all communications for transaction
        comms = await self.get_transaction_communications(transaction_id, limit=1000)

        summary: dict[str, dict[str, Any]] = {}
        total_inbound = 0
        total_outbound = 0

        for comm in comms:
            topic = comm.topic or "general"

            if topic not in summary:
                summary[topic] = {
                    "count": 0,
                    "last_outbound": None,
                    "last_inbound": None,
                    "awaiting_response": False,
                    "last_subject": None,
                }

            summary[topic]["count"] += 1

            if comm.direction == CommunicationDirection.OUTBOUND:
                total_outbound += 1
                if summary[topic]["last_outbound"] is None:
                    summary[topic]["last_outbound"] = comm.sent_at or comm.created_at
                    summary[topic]["last_subject"] = comm.subject
            else:
                total_inbound += 1
                if summary[topic]["last_inbound"] is None:
                    summary[topic]["last_inbound"] = comm.created_at

            # Check if awaiting response (outbound sent, no inbound since)
            if summary[topic]["last_outbound"]:
                last_out = summary[topic]["last_outbound"]
                last_in = summary[topic]["last_inbound"]
                if last_in is None or last_in < last_out:
                    summary[topic]["awaiting_response"] = True

        return {
            "transaction_id": str(transaction_id),
            "total_communications": len(comms),
            "total_inbound": total_inbound,
            "total_outbound": total_outbound,
            "by_topic": summary,
            "generated_at": datetime.now().isoformat(),
        }

    async def find_communications_about(
        self,
        transaction_id: UUID,
        query: str,
    ) -> Sequence[CommunicationLogModel]:
        """
        Search communications for a transaction by keyword/topic.

        Useful for queries like "where are we with the deposit receipt?"
        """
        # First, try to match a topic
        query_lower = query.lower()
        matched_topic = None

        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                matched_topic = topic
                break

        if matched_topic:
            return await self.get_transaction_communications(
                transaction_id,
                topic=matched_topic,
                limit=20,
            )

        # Fall back to full-text search in subject/body
        stmt = (
            select(CommunicationLogModel)
            .where(
                and_(
                    CommunicationLogModel.transaction_id == transaction_id,
                    or_(
                        CommunicationLogModel.subject.ilike(f"%{query}%"),
                        CommunicationLogModel.body_preview.ilike(f"%{query}%"),
                    ),
                )
            )
            .order_by(CommunicationLogModel.created_at.desc())
            .limit(20)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_responses(
        self,
        organization_id: UUID,
        *,
        older_than_hours: int = 48,
    ) -> Sequence[CommunicationLogModel]:
        """
        Get outbound communications that haven't received a response.

        Useful for identifying stalled communications.
        """
        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        stmt = (
            select(CommunicationLogModel)
            .where(
                and_(
                    CommunicationLogModel.organization_id == organization_id,
                    CommunicationLogModel.direction == CommunicationDirection.OUTBOUND,
                    CommunicationLogModel.status == CommunicationStatus.PENDING_RESPONSE,
                    CommunicationLogModel.sent_at < cutoff,
                )
            )
            .order_by(CommunicationLogModel.sent_at.asc())
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_as_responded(
        self,
        communication_id: UUID,
    ) -> CommunicationLogModel | None:
        """Mark a communication as having received a response."""
        stmt = select(CommunicationLogModel).where(
            CommunicationLogModel.id == communication_id
        )
        result = await self.session.execute(stmt)
        comm = result.scalar_one_or_none()

        if comm:
            comm.status = CommunicationStatus.RESPONDED
            await self.session.flush()

        return comm

    async def get_communication_timeline(
        self,
        transaction_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get a timeline of all communications for a transaction.

        Returns a chronological list suitable for display.
        """
        comms = await self.get_transaction_communications(
            transaction_id,
            limit=100,
        )

        # Reverse to get chronological order
        comms = list(reversed(comms))

        return [
            {
                "id": str(c.id),
                "timestamp": (c.sent_at or c.created_at).isoformat(),
                "direction": c.direction,
                "channel": c.channel,
                "topic": c.topic,
                "subject": c.subject,
                "preview": c.body_preview[:100] if c.body_preview else None,
                "sender": c.sender,
                "recipients": c.recipients,
                "status": c.status,
            }
            for c in comms
        ]


def get_communication_log_service(session: AsyncSession) -> CommunicationLogService:
    """Factory function for CommunicationLogService."""
    return CommunicationLogService(session)
