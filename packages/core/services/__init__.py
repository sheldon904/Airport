"""Service layer - business logic and orchestration."""

from packages.core.services.transaction import TransactionService
from packages.core.services.document import DocumentService
from packages.core.services.deadline import DeadlineService
from packages.core.services.auth import AuthService
from packages.core.services.audit import AuditService
from packages.core.services.report import ReportService
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
from packages.core.services.privacy import (
    PrivacyService,
    PIIType,
    AccessLevel,
    get_privacy_service,
    is_confidential_document_type,
)
from packages.core.services.communication_log import (
    CommunicationLogService,
    CommunicationDirection,
    CommunicationChannel,
    CommunicationStatus,
    get_communication_log_service,
)
from packages.core.services.priority import (
    PriorityService,
    HealthStatus,
    PriorityLevel,
    get_priority_service,
)
from packages.core.services.portal import (
    PortalService,
    get_portal_service,
)
from packages.core.services.contacts import (
    ContactsService,
    ContactType,
    ContactSource,
    get_contacts_service,
)

__all__ = [
    # Existing services
    "TransactionService",
    "DocumentService",
    "DeadlineService",
    "AuthService",
    "AuditService",
    "ReportService",
    "EmailService",
    "SMTPEmailService",
    "ConsoleEmailService",
    "QueuedEmailService",
    "get_email_service",
    "EventBus",
    "EventTypes",
    "get_event_bus",
    # New services - Privacy
    "PrivacyService",
    "PIIType",
    "AccessLevel",
    "get_privacy_service",
    "is_confidential_document_type",
    # New services - Communication
    "CommunicationLogService",
    "CommunicationDirection",
    "CommunicationChannel",
    "CommunicationStatus",
    "get_communication_log_service",
    # New services - Priority
    "PriorityService",
    "HealthStatus",
    "PriorityLevel",
    "get_priority_service",
    # New services - Portal
    "PortalService",
    "get_portal_service",
    # New services - Contacts/CRM
    "ContactsService",
    "ContactType",
    "ContactSource",
    "get_contacts_service",
]
