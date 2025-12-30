"""SQLAlchemy ORM models for Airport."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class OrganizationModel(Base):
    """Brokerage or team organization."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="FL")

    # Subscription
    subscription_tier: Mapped[str] = mapped_column(String(50), default="starter")
    subscription_status: Mapped[str] = mapped_column(String(50), default="active")

    # Settings
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    compliance_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(back_populates="organization")
    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="organization")


class UserModel(Base):
    """User account (agent, broker, admin)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="agent")  # agent, admin, broker

    # Profile
    phone: Mapped[str | None] = mapped_column(String(20))
    license_number: Mapped[str | None] = mapped_column(String(50))

    # Preferences
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_email", "email"),
    )


class TransactionModel(Base):
    """Real estate transaction.

    Supports soft delete via deleted_at column. Transactions marked as deleted
    preserve all relationships (documents, deadlines, audit logs) for compliance.
    """

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(String(50), default="draft")
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Property
    property_address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    year_built: Mapped[int | None] = mapped_column()

    # Transaction Metadata (for conditional compliance)
    is_hoa: Mapped[bool] = mapped_column(Boolean, default=False)
    is_condo: Mapped[bool] = mapped_column(Boolean, default=False)
    is_financed: Mapped[bool] = mapped_column(Boolean, default=True)

    # Key Dates
    effective_date: Mapped[date | None] = mapped_column(Date)
    closing_date: Mapped[date | None] = mapped_column(Date)

    # Parties (stored as JSONB for flexibility)
    parties: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)

    # Soft delete support for compliance (preserves audit trail)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Priority and health tracking
    priority_score: Mapped[int] = mapped_column(Integer, default=50)
    health_status: Mapped[str] = mapped_column(String(20), default="on_track")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(back_populates="transactions")
    documents: Mapped[list["DocumentModel"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    deadlines: Mapped[list["DeadlineModel"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    checklist: Mapped["ChecklistModel | None"] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLogModel"]] = relationship(
        back_populates="transaction"  # No cascade - audit logs preserved on delete
    )

    @property
    def is_deleted(self) -> bool:
        """Check if transaction is soft-deleted."""
        return self.deleted_at is not None

    __table_args__ = (
        Index("ix_transactions_organization_id", "organization_id"),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_closing_date", "closing_date"),
        Index("ix_transactions_deleted_at", "deleted_at"),
    )


class DocumentModel(Base):
    """Transaction document."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Document info
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    file_size: Mapped[int | None] = mapped_column()

    # Extraction
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    extraction_confidence: Mapped[float | None] = mapped_column()
    needs_review_reason: Mapped[str | None] = mapped_column(Text)

    # Privacy - PII redaction
    redacted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pii_detected: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Access control
    access_level: Mapped[str] = mapped_column(String(50), default="organization")
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)

    # Verification
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(back_populates="documents")

    __table_args__ = (
        Index("ix_documents_transaction_id", "transaction_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
    )


class DeadlineModel(Base):
    """Transaction deadline."""

    __tablename__ = "deadlines"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

    # Deadline info
    deadline_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="upcoming")

    # Reminders
    reminder_days: Mapped[list[int]] = mapped_column(JSONB, default=lambda: [7, 3, 1])
    last_reminder_sent: Mapped[datetime | None] = mapped_column(DateTime)

    # Completion
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(back_populates="deadlines")

    __table_args__ = (
        Index("ix_deadlines_transaction_id", "transaction_id"),
        Index("ix_deadlines_due_date", "due_date"),
        Index("ix_deadlines_status", "status"),
        Index("ix_deadlines_completed_by", "completed_by"),
    )


class ChecklistModel(Base):
    """Transaction compliance checklist."""

    __tablename__ = "checklists"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Template reference
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Items stored as JSONB for flexibility
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transaction: Mapped["TransactionModel"] = relationship(back_populates="checklist")


class AuditLogModel(Base):
    """Audit trail for compliance.

    IMPORTANT: Audit logs use SET NULL on transaction deletion to preserve
    compliance records. This is required for:
    - RESPA/TRID compliance (3 years minimum retention)
    - Florida broker records (5 years per F.S. 475.5015)
    - General compliance audit requirements
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Event info
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str | None] = mapped_column(String(50))  # If triggered by AI agent
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))

    # Details
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    transaction: Mapped["TransactionModel | None"] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_transaction_id", "transaction_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_user_id", "user_id"),
    )


class JobQueueModel(Base):
    """Background job queue entry."""

    __tablename__ = "job_queue"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_job_queue_status_scheduled", "status", "scheduled_at"),
        Index("ix_job_queue_job_type", "job_type"),
    )


class CommunicationLogModel(Base):
    """Communication log for tracking transaction communications.

    Tracks all inbound and outbound communications related to transactions,
    enabling queries like "where are we with the deposit receipt?"
    """

    __tablename__ = "communication_log"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    # Message details
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # 'inbound', 'outbound'
    channel: Mapped[str] = mapped_column(String(20), default="email")
    subject: Mapped[str | None] = mapped_column(String(500))
    body_preview: Mapped[str | None] = mapped_column(String(500))
    full_body: Mapped[str | None] = mapped_column(Text)

    # Participants
    sender: Mapped[str | None] = mapped_column(String(255))
    recipients: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Categorization
    topic: Mapped[str | None] = mapped_column(String(100))

    # Status
    status: Mapped[str] = mapped_column(String(50), default="sent")

    # Related entities
    related_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    related_deadline_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("deadlines.id", ondelete="SET NULL")
    )

    # Extra data
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_communication_log_transaction_id", "transaction_id"),
        Index("ix_communication_log_organization_id", "organization_id"),
        Index("ix_communication_log_topic", "topic"),
        Index("ix_communication_log_created_at", "created_at"),
    )


class ContactModel(Base):
    """Contact for lightweight CRM functionality.

    Stores contacts extracted from transactions and allows tracking
    interaction history across multiple transactions.
    """

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    # Contact info
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_type: Mapped[str] = mapped_column(String(50), default="other")
    company: Mapped[str | None] = mapped_column(String(255))

    # Source tracking
    source: Mapped[str] = mapped_column(String(50), default="manual")

    # Transaction history
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_transaction_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    last_transaction_date: Mapped[date | None] = mapped_column(Date)

    # Organization and categorization
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_contacts_organization_id", "organization_id"),
        Index("ix_contacts_email", "email"),
        Index("ix_contacts_contact_type", "contact_type"),
    )
