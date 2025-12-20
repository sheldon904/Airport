"""Communication templates for Florida real estate transactions."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class CommunicationType(str, Enum):
    """Types of communications."""

    # Status Updates
    CONTRACT_RECEIVED = "contract_received"
    UNDER_CONTRACT = "under_contract"
    INSPECTION_SCHEDULED = "inspection_scheduled"
    INSPECTION_COMPLETE = "inspection_complete"
    APPRAISAL_ORDERED = "appraisal_ordered"
    APPRAISAL_COMPLETE = "appraisal_complete"
    LOAN_APPROVED = "loan_approved"
    CLEAR_TO_CLOSE = "clear_to_close"
    CLOSING_SCHEDULED = "closing_scheduled"
    CLOSING_COMPLETE = "closing_complete"

    # Deadline Reminders
    DEADLINE_REMINDER = "deadline_reminder"
    DEADLINE_URGENT = "deadline_urgent"
    DEADLINE_MISSED = "deadline_missed"

    # Document Requests
    DOCUMENT_NEEDED = "document_needed"
    DOCUMENT_RECEIVED = "document_received"
    DOCUMENT_ISSUE = "document_issue"

    # General
    STATUS_UPDATE = "status_update"
    CUSTOM = "custom"


class CommunicationTemplate(BaseModel):
    """A communication template."""

    id: str
    type: CommunicationType
    name: str
    subject_template: str
    body_template: str
    recipients: list[str]  # Party roles to include
    required_fields: list[str]  # Fields needed for template


FL_COMMUNICATION_TEMPLATES: dict[str, CommunicationTemplate] = {
    # Contract Status
    "contract_received": CommunicationTemplate(
        id="contract_received",
        type=CommunicationType.CONTRACT_RECEIVED,
        name="Contract Received Confirmation",
        subject_template="Contract Received - {property_address}",
        body_template="""Hello {recipient_name},

This is to confirm that we have received the executed purchase contract for:

Property: {property_address}
Purchase Price: {purchase_price}
Effective Date: {effective_date}
Closing Date: {closing_date}

Key upcoming deadlines:
{deadline_summary}

Please review the attached contract and let us know if you have any questions.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "purchase_price", "effective_date", "closing_date"],
    ),
    "under_contract": CommunicationTemplate(
        id="under_contract",
        type=CommunicationType.UNDER_CONTRACT,
        name="Under Contract Notification",
        subject_template="Under Contract - {property_address}",
        body_template="""Hello {recipient_name},

Great news! The property at {property_address} is now officially under contract.

Contract Details:
- Purchase Price: {purchase_price}
- Effective Date: {effective_date}
- Closing Date: {closing_date}

Next Steps:
1. Earnest money deposit due by {earnest_money_deadline}
2. Inspection period ends {inspection_deadline}
3. Financing contingency expires {financing_deadline}

We will keep you updated on the progress of this transaction.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent", "lender", "title_company"],
        required_fields=["property_address", "purchase_price", "effective_date", "closing_date"],
    ),
    # Inspection Updates
    "inspection_scheduled": CommunicationTemplate(
        id="inspection_scheduled",
        type=CommunicationType.INSPECTION_SCHEDULED,
        name="Inspection Scheduled",
        subject_template="Inspection Scheduled - {property_address}",
        body_template="""Hello {recipient_name},

The home inspection has been scheduled for the property at {property_address}.

Inspection Details:
- Date: {inspection_date}
- Time: {inspection_time}
- Inspector: {inspector_name}
- Company: {inspector_company}

{access_instructions}

Please ensure the property is accessible at the scheduled time.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "inspection_date", "inspection_time"],
    ),
    "inspection_complete": CommunicationTemplate(
        id="inspection_complete",
        type=CommunicationType.INSPECTION_COMPLETE,
        name="Inspection Complete",
        subject_template="Inspection Complete - {property_address}",
        body_template="""Hello {recipient_name},

The home inspection for {property_address} has been completed.

{inspection_summary}

The inspection report is attached for your review. Please note that the inspection contingency period ends on {inspection_deadline}.

Next steps will depend on the buyer's review of the inspection report.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "inspection_deadline"],
    ),
    # Deadline Reminders
    "deadline_reminder": CommunicationTemplate(
        id="deadline_reminder",
        type=CommunicationType.DEADLINE_REMINDER,
        name="Deadline Reminder",
        subject_template="Reminder: {deadline_name} - {property_address}",
        body_template="""Hello {recipient_name},

This is a friendly reminder about an upcoming deadline for the transaction at {property_address}.

Deadline: {deadline_name}
Due Date: {due_date}
Days Remaining: {days_remaining}

{deadline_description}

Please take any necessary action before this deadline.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "deadline_name", "due_date", "days_remaining"],
    ),
    "deadline_urgent": CommunicationTemplate(
        id="deadline_urgent",
        type=CommunicationType.DEADLINE_URGENT,
        name="Urgent Deadline Notice",
        subject_template="URGENT: {deadline_name} Due Tomorrow - {property_address}",
        body_template="""Hello {recipient_name},

URGENT: An important deadline is due TOMORROW for the transaction at {property_address}.

Deadline: {deadline_name}
Due Date: {due_date}

{deadline_description}

Please take immediate action to meet this deadline.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "deadline_name", "due_date"],
    ),
    # Document Requests
    "document_needed": CommunicationTemplate(
        id="document_needed",
        type=CommunicationType.DOCUMENT_NEEDED,
        name="Document Needed",
        subject_template="Document Needed - {property_address}",
        body_template="""Hello {recipient_name},

We need the following document(s) for the transaction at {property_address}:

{document_list}

{additional_instructions}

Please submit the requested document(s) at your earliest convenience.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "document_list"],
    ),
    "document_received": CommunicationTemplate(
        id="document_received",
        type=CommunicationType.DOCUMENT_RECEIVED,
        name="Document Received Confirmation",
        subject_template="Document Received - {property_address}",
        body_template="""Hello {recipient_name},

This is to confirm that we have received the following document for the transaction at {property_address}:

Document: {document_name}
Received: {received_date}

{next_steps}

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "document_name", "received_date"],
    ),
    # Closing Updates
    "clear_to_close": CommunicationTemplate(
        id="clear_to_close",
        type=CommunicationType.CLEAR_TO_CLOSE,
        name="Clear to Close",
        subject_template="Clear to Close - {property_address}",
        body_template="""Hello {recipient_name},

Congratulations! We are clear to close on the transaction at {property_address}.

Closing Details:
- Closing Date: {closing_date}
- Closing Time: {closing_time}
- Location: {closing_location}

What to bring:
- Valid photo ID
- Cashier's check or wire transfer confirmation for closing funds
- Any required documents not yet submitted

Please review the attached Closing Disclosure carefully and contact us if you have any questions.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent", "lender", "title_company"],
        required_fields=["property_address", "closing_date"],
    ),
    "closing_complete": CommunicationTemplate(
        id="closing_complete",
        type=CommunicationType.CLOSING_COMPLETE,
        name="Closing Complete",
        subject_template="Congratulations! Closing Complete - {property_address}",
        body_template="""Hello {recipient_name},

Congratulations! The closing for {property_address} has been successfully completed.

Transaction Summary:
- Property: {property_address}
- Final Sale Price: {purchase_price}
- Closing Date: {closing_date}

{closing_summary}

Thank you for choosing to work with us. We wish you all the best in your new home!

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "purchase_price", "closing_date"],
    ),
    # Status Update
    "status_update": CommunicationTemplate(
        id="status_update",
        type=CommunicationType.STATUS_UPDATE,
        name="Transaction Status Update",
        subject_template="Status Update - {property_address}",
        body_template="""Hello {recipient_name},

Here is a status update for the transaction at {property_address}:

Current Status: {transaction_status}

{status_details}

Upcoming Deadlines:
{deadline_summary}

Checklist Progress: {checklist_progress}% complete

Please let us know if you have any questions.

Best regards,
{sender_name}""",
        recipients=["buyer", "seller", "buyer_agent", "seller_agent"],
        required_fields=["property_address", "transaction_status"],
    ),
}


def get_template(template_id: str) -> CommunicationTemplate | None:
    """Get a communication template by ID."""
    return FL_COMMUNICATION_TEMPLATES.get(template_id)


def render_template(template: CommunicationTemplate, context: dict[str, Any]) -> tuple[str, str]:
    """
    Render a template with the given context.

    Returns:
        tuple: (subject, body)
    """
    subject = template.subject_template
    body = template.body_template

    for key, value in context.items():
        placeholder = "{" + key + "}"
        if value is not None:
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        else:
            subject = subject.replace(placeholder, "")
            body = body.replace(placeholder, "")

    return (subject, body)
