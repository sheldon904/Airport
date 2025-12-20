"""Core domain models for Airport transaction coordinator."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# === Enums ===


class TransactionStatus(str, Enum):
    """Transaction lifecycle states."""

    DRAFT = "draft"
    PENDING = "pending"  # Contract received, awaiting extraction
    ACTIVE = "active"  # Under contract, tracking deadlines
    PENDING_CLOSE = "pending_close"  # Approaching close date
    CLOSED = "closed"  # Successfully closed
    CANCELLED = "cancelled"  # Transaction fell through
    ON_HOLD = "on_hold"  # Temporarily paused


class TransactionType(str, Enum):
    """Type of real estate transaction."""

    PURCHASE = "purchase"
    SALE = "sale"
    DUAL = "dual"  # Same agent represents both sides


class DocumentType(str, Enum):
    """Categories of transaction documents."""

    # Contract Documents
    PURCHASE_CONTRACT = "purchase_contract"
    AMENDMENT = "amendment"
    ADDENDUM = "addendum"
    COUNTEROFFER = "counteroffer"

    # Disclosures
    SELLER_DISCLOSURE = "seller_disclosure"
    LEAD_PAINT = "lead_paint"
    HOA_DISCLOSURE = "hoa_disclosure"
    PROPERTY_TAX = "property_tax"

    # Financial
    PRE_APPROVAL = "pre_approval"
    PROOF_OF_FUNDS = "proof_of_funds"
    EARNEST_MONEY = "earnest_money"

    # Inspections
    INSPECTION_REPORT = "inspection_report"
    APPRAISAL = "appraisal"
    SURVEY = "survey"

    # Title & Closing
    TITLE_COMMITMENT = "title_commitment"
    CLOSING_DISCLOSURE = "closing_disclosure"
    DEED = "deed"

    # Other
    CORRESPONDENCE = "correspondence"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing states."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DeadlineType(str, Enum):
    """Types of transaction deadlines."""

    # Contract Dates
    EFFECTIVE_DATE = "effective_date"
    CLOSING_DATE = "closing_date"

    # Contingencies
    INSPECTION_PERIOD = "inspection_period"
    FINANCING_CONTINGENCY = "financing_contingency"
    APPRAISAL_CONTINGENCY = "appraisal_contingency"
    SALE_CONTINGENCY = "sale_contingency"

    # Financial
    EARNEST_MONEY_DUE = "earnest_money_due"
    ADDITIONAL_DEPOSIT = "additional_deposit"

    # Disclosures
    DISCLOSURE_DEADLINE = "disclosure_deadline"

    # Title
    TITLE_REVIEW_PERIOD = "title_review_period"

    # Custom
    CUSTOM = "custom"


class DeadlineStatus(str, Enum):
    """Deadline tracking states."""

    UPCOMING = "upcoming"
    DUE_SOON = "due_soon"  # Within 3 days
    OVERDUE = "overdue"
    COMPLETED = "completed"
    WAIVED = "waived"
    EXTENDED = "extended"


class PartyRole(str, Enum):
    """Roles in a transaction."""

    BUYER = "buyer"
    SELLER = "seller"
    BUYER_AGENT = "buyer_agent"
    SELLER_AGENT = "seller_agent"
    LENDER = "lender"
    TITLE_COMPANY = "title_company"
    INSPECTOR = "inspector"
    APPRAISER = "appraiser"
    ATTORNEY = "attorney"
    OTHER = "other"


class ChecklistItemStatus(str, Enum):
    """Status of checklist items."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


# === Domain Models ===


class Party(BaseModel):
    """A party involved in the transaction."""

    id: UUID
    role: PartyRole
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    license_number: str | None = None  # For agents
    notes: str | None = None


class Address(BaseModel):
    """Property or mailing address."""

    street: str
    unit: str | None = None
    city: str
    state: str
    zip_code: str
    county: str | None = None

    @property
    def full_address(self) -> str:
        """Format as single line address."""
        parts = [self.street]
        if self.unit:
            parts.append(f"Unit {self.unit}")
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)


class Deadline(BaseModel):
    """A tracked deadline in the transaction."""

    id: UUID
    transaction_id: UUID
    deadline_type: DeadlineType
    name: str
    date: date
    status: DeadlineStatus = DeadlineStatus.UPCOMING
    source_document_id: UUID | None = None
    notes: str | None = None
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    reminder_days: list[int] = Field(default_factory=lambda: [7, 3, 1])


class Document(BaseModel):
    """A document in the transaction."""

    id: UUID
    transaction_id: UUID
    document_type: DocumentType
    filename: str
    storage_path: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    extracted_data: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    needs_review_reason: str | None = None
    uploaded_at: datetime
    uploaded_by: UUID
    verified_at: datetime | None = None
    verified_by: UUID | None = None


class ChecklistItem(BaseModel):
    """An item in the transaction checklist."""

    id: UUID
    name: str
    description: str | None = None
    status: ChecklistItemStatus = ChecklistItemStatus.NOT_STARTED
    required: bool = True
    document_id: UUID | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    notes: str | None = None


class Checklist(BaseModel):
    """Transaction compliance checklist."""

    id: UUID
    transaction_id: UUID
    template_id: str  # e.g., "FL_RESIDENTIAL_PURCHASE"
    items: list[ChecklistItem]

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.items:
            return 0.0
        completed = sum(
            1
            for item in self.items
            if item.status in (ChecklistItemStatus.COMPLETED, ChecklistItemStatus.NOT_APPLICABLE)
        )
        return (completed / len(self.items)) * 100


class Transaction(BaseModel):
    """Core transaction entity."""

    id: UUID
    organization_id: UUID
    status: TransactionStatus = TransactionStatus.DRAFT
    transaction_type: TransactionType

    # Property
    property_address: Address
    purchase_price: Decimal | None = None
    year_built: int | None = None

    # Key Dates
    effective_date: date | None = None
    closing_date: date | None = None

    # Parties
    parties: list[Party] = Field(default_factory=list)

    # Related entities (loaded separately)
    # documents: list[Document]
    # deadlines: list[Deadline]
    # checklist: Checklist

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    notes: str | None = None

    def get_party_by_role(self, role: PartyRole) -> Party | None:
        """Find a party by their role."""
        for party in self.parties:
            if party.role == role:
                return party
        return None


# === Event Models (for agent communication) ===


class TransactionEvent(BaseModel):
    """Base class for transaction events."""

    event_type: str
    transaction_id: UUID
    timestamp: datetime
    triggered_by: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentUploadedEvent(TransactionEvent):
    """Fired when a document is uploaded."""

    event_type: str = "document.uploaded"
    document_id: UUID
    document_type: DocumentType
    filename: str


class ExtractionCompleteEvent(TransactionEvent):
    """Fired when document extraction completes."""

    event_type: str = "extraction.complete"
    document_id: UUID
    extracted_data: dict[str, Any]
    confidence: float
    needs_review: bool


class DeadlineApproachingEvent(TransactionEvent):
    """Fired when a deadline is approaching."""

    event_type: str = "deadline.approaching"
    deadline_id: UUID
    deadline_type: DeadlineType
    due_date: date
    days_remaining: int


class ReviewRequiredEvent(TransactionEvent):
    """Fired when human review is required."""

    event_type: str = "review.required"
    review_type: str
    reason: str
    context: dict[str, Any]
