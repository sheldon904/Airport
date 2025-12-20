"""Notification models and enums."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NotificationType(str, Enum):
    """Types of notifications."""

    # Deadline notifications
    DEADLINE_REMINDER = "deadline_reminder"
    DEADLINE_URGENT = "deadline_urgent"
    DEADLINE_OVERDUE = "deadline_overdue"

    # Document notifications
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_NEEDS_REVIEW = "document_needs_review"
    DOCUMENT_VERIFIED = "document_verified"
    DOCUMENT_REJECTED = "document_rejected"

    # Transaction notifications
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_STATUS_CHANGE = "transaction_status_change"
    TRANSACTION_CLOSING_SOON = "transaction_closing_soon"

    # Communication notifications
    COMMUNICATION_PENDING_APPROVAL = "communication_pending_approval"
    COMMUNICATION_SENT = "communication_sent"

    # System notifications
    SYSTEM_ALERT = "system_alert"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True

    # Specific notification type preferences
    deadline_reminders: bool = True
    deadline_reminder_days: list[int] = [7, 3, 1]
    document_updates: bool = True
    transaction_updates: bool = True
    marketing_emails: bool = False

    # Quiet hours (no notifications during these hours)
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8  # 8 AM


class NotificationRecord(BaseModel):
    """A notification record for tracking."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    transaction_id: UUID | None = None

    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    status: NotificationStatus

    recipient_email: str | None = None
    recipient_phone: str | None = None

    subject: str | None = None
    body: str
    metadata: dict[str, Any] = {}

    created_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None

    # Retry tracking
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
