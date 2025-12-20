"""Service layer - business logic and orchestration."""

from packages.core.services.transaction import TransactionService
from packages.core.services.document import DocumentService
from packages.core.services.deadline import DeadlineService
from packages.core.services.auth import AuthService
from packages.core.services.email import (
    EmailService,
    SMTPEmailService,
    ConsoleEmailService,
    QueuedEmailService,
    get_email_service,
)
from packages.core.services.events import (
    EventBus,
    EventTypes,
    get_event_bus,
)

__all__ = [
    "TransactionService",
    "DocumentService",
    "DeadlineService",
    "AuthService",
    "EmailService",
    "SMTPEmailService",
    "ConsoleEmailService",
    "QueuedEmailService",
    "get_email_service",
    "EventBus",
    "EventTypes",
    "get_event_bus",
]
