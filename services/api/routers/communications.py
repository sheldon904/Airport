"""Communication management and email sending endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from services.api.dependencies import (
    CurrentUserDep,
    TransactionServiceDep,
    DbSessionDep,
)
from packages.core.services.communication_log import get_communication_log_service
from packages.core.services.email import get_email_service

router = APIRouter()


# === Email Templates ===


EMAIL_TEMPLATES = {
    "earnest_money_receipt": {
        "subject": "Earnest Money Deposit Received - {property_address}",
        "body": """Dear {recipient_name},

This email confirms receipt of the earnest money deposit for the property at {property_address}.

Deposit Details:
- Amount: {amount}
- Date Received: {date_received}
- Transaction ID: {transaction_id}

The deposit is being held in escrow per the terms of the purchase agreement.

Please retain this email for your records.

Best regards,
{sender_name}
{company_name}""",
    },
    "deadline_reminder": {
        "subject": "Deadline Reminder: {deadline_name} - {property_address}",
        "body": """Dear {recipient_name},

This is a reminder that the following deadline is approaching:

Deadline: {deadline_name}
Due Date: {due_date}
Property: {property_address}

Please ensure all required actions are completed before this date.

If you have any questions, please don't hesitate to reach out.

Best regards,
{sender_name}
{company_name}""",
    },
    "document_request": {
        "subject": "Document Request - {property_address}",
        "body": """Dear {recipient_name},

We are missing the following document(s) for the transaction at {property_address}:

{document_list}

Please submit these documents at your earliest convenience to avoid delays in the closing process.

You can upload documents directly through our secure portal:
{portal_link}

Best regards,
{sender_name}
{company_name}""",
    },
    "closing_confirmation": {
        "subject": "Closing Scheduled - {property_address}",
        "body": """Dear {recipient_name},

Your closing has been scheduled for the property at {property_address}.

Closing Details:
- Date: {closing_date}
- Time: {closing_time}
- Location: {closing_location}

Please bring the following to closing:
- Valid government-issued photo ID
- Certified funds as specified in closing disclosure
- Any additional documents requested

If you need to reschedule or have questions, please contact us immediately.

Best regards,
{sender_name}
{company_name}""",
    },
    "general": {
        "subject": "{subject}",
        "body": """{body}

Best regards,
{sender_name}
{company_name}""",
    },
}


# === Request/Response Models ===


class CommunicationLogResponse(BaseModel):
    """Communication log entry."""

    id: UUID
    transaction_id: UUID
    direction: str
    channel: str
    subject: str | None
    body_preview: str | None
    topic: str | None
    from_party: str | None
    to_party: str | None
    timestamp: datetime
    status: str


class DraftEmailRequest(BaseModel):
    """Request to draft an email."""

    transaction_id: UUID
    template: str = Field(..., description="Template name or 'general' for custom")
    recipient_email: EmailStr
    recipient_name: str
    variables: dict[str, Any] = Field(default_factory=dict)
    # For general template
    subject: str | None = None
    body: str | None = None


class DraftEmailResponse(BaseModel):
    """Response with drafted email for preview."""

    draft_id: str
    subject: str
    body: str
    html_body: str | None = None
    to_email: str
    to_name: str
    template_used: str
    transaction_id: UUID


class SendEmailRequest(BaseModel):
    """Request to send an email."""

    transaction_id: UUID
    to_email: EmailStr
    to_name: str
    subject: str
    body: str
    html_body: str | None = None
    reply_to: str | None = None
    log_as_communication: bool = True
    topic: str | None = None


class SendEmailResponse(BaseModel):
    """Response after sending email."""

    success: bool
    message_id: str | None = None
    communication_id: UUID | None = None
    error: str | None = None


class BulkEmailRequest(BaseModel):
    """Request to send bulk emails."""

    transaction_id: UUID
    template: str
    recipients: list[dict[str, Any]]  # List of {email, name, variables}


class BulkEmailResponse(BaseModel):
    """Response after sending bulk emails."""

    total: int
    sent: int
    failed: int
    results: dict[str, bool]


# === Helper Functions ===


def render_template(
    template_name: str,
    variables: dict[str, Any],
) -> tuple[str, str]:
    """Render an email template with variables."""
    template = EMAIL_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template not found: {template_name}")

    subject = template["subject"].format(**variables)
    body = template["body"].format(**variables)

    return subject, body


# === Endpoints ===


@router.get("/transaction/{transaction_id}", response_model=list[CommunicationLogResponse])
async def list_communications(
    transaction_id: UUID,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    db: DbSessionDep,
    direction: str | None = Query(None, pattern="^(inbound|outbound)$"),
    channel: str | None = Query(None),
    topic: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[CommunicationLogResponse]:
    """Get communications for a transaction."""
    # Verify transaction access
    transaction = await tx_service.get_transaction(
        transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    service = get_communication_log_service(db)
    communications = await service.get_transaction_communications(
        transaction_id,
        direction=direction,
        channel=channel,
        topic=topic,
        limit=limit,
    )

    return [
        CommunicationLogResponse(
            id=c.id,
            transaction_id=c.transaction_id,
            direction=c.direction,
            channel=c.channel,
            subject=c.subject,
            body_preview=c.body_preview,
            topic=c.topic,
            from_party=c.from_party,
            to_party=c.to_party,
            timestamp=c.timestamp,
            status=c.status,
        )
        for c in communications
    ]


@router.get("/templates")
async def list_email_templates(
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """List available email templates."""
    return {
        "templates": [
            {
                "id": name,
                "name": name.replace("_", " ").title(),
                "variables": _extract_template_variables(template),
            }
            for name, template in EMAIL_TEMPLATES.items()
        ]
    }


def _extract_template_variables(template: dict[str, str]) -> list[str]:
    """Extract variable names from a template."""
    import re

    text = template["subject"] + template["body"]
    matches = re.findall(r"\{(\w+)\}", text)
    return list(set(matches))


@router.post("/draft", response_model=DraftEmailResponse)
async def draft_email(
    request: DraftEmailRequest,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
) -> DraftEmailResponse:
    """
    Draft an email for preview before sending.

    Use this to preview how an email will look before sending.
    Returns the rendered subject and body.
    """
    # Verify transaction access
    transaction = await tx_service.get_transaction(
        request.transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Build variables from transaction
    property_address = transaction.property_address or {}
    street = property_address.get("street", "")
    city = property_address.get("city", "")

    base_variables = {
        "property_address": f"{street}, {city}",
        "transaction_id": str(transaction.id),
        "recipient_name": request.recipient_name,
        "sender_name": current_user.name or "Transaction Coordinator",
        "company_name": "Airport TC",  # TODO: Get from org settings
    }

    # Merge with provided variables
    variables = {**base_variables, **request.variables}

    # Handle general template
    if request.template == "general":
        if not request.subject or not request.body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subject and body required for general template",
            )
        variables["subject"] = request.subject
        variables["body"] = request.body

    try:
        subject, body = render_template(request.template, variables)
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template error: {str(e)}",
        )

    # Generate draft ID
    draft_id = f"draft-{transaction.id}-{datetime.utcnow().timestamp()}"

    return DraftEmailResponse(
        draft_id=draft_id,
        subject=subject,
        body=body,
        html_body=None,  # TODO: Generate HTML version
        to_email=request.recipient_email,
        to_name=request.recipient_name,
        template_used=request.template,
        transaction_id=request.transaction_id,
    )


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    db: DbSessionDep,
    background_tasks: BackgroundTasks,
) -> SendEmailResponse:
    """
    Send an email and optionally log it as a communication.

    This endpoint actually sends the email using the configured
    email service (SMTP, SendGrid, etc.).
    """
    # Verify transaction access
    transaction = await tx_service.get_transaction(
        request.transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    email_service = get_email_service()

    try:
        # Send the email
        success = await email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            html_body=request.html_body,
            reply_to=request.reply_to,
        )

        communication_id = None

        # Log as communication if requested
        if request.log_as_communication and success:
            comm_service = get_communication_log_service(db)
            communication = await comm_service.log_communication(
                transaction_id=request.transaction_id,
                direction="outbound",
                channel="email",
                from_party=current_user.email,
                to_party=request.to_email,
                subject=request.subject,
                body=request.body,
                topic=request.topic,
            )
            communication_id = communication.id

        return SendEmailResponse(
            success=success,
            message_id=f"msg-{datetime.utcnow().timestamp()}",
            communication_id=communication_id,
        )

    except Exception as e:
        return SendEmailResponse(
            success=False,
            error=str(e),
        )


@router.post("/send-bulk", response_model=BulkEmailResponse)
async def send_bulk_email(
    request: BulkEmailRequest,
    current_user: CurrentUserDep,
    tx_service: TransactionServiceDep,
    db: DbSessionDep,
) -> BulkEmailResponse:
    """
    Send emails to multiple recipients using a template.

    Each recipient can have their own variable values.
    """
    # Verify transaction access
    transaction = await tx_service.get_transaction(
        request.transaction_id, current_user.organization_id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    email_service = get_email_service()
    comm_service = get_communication_log_service(db)

    results = {}
    sent = 0
    failed = 0

    # Build base variables
    property_address = transaction.property_address or {}
    base_variables = {
        "property_address": f"{property_address.get('street', '')}, {property_address.get('city', '')}",
        "transaction_id": str(transaction.id),
        "sender_name": current_user.name or "Transaction Coordinator",
        "company_name": "Airport TC",
    }

    for recipient in request.recipients:
        email = recipient.get("email")
        name = recipient.get("name", "")
        variables = {
            **base_variables,
            "recipient_name": name,
            **recipient.get("variables", {}),
        }

        try:
            subject, body = render_template(request.template, variables)
            success = await email_service.send_email(
                to_email=email,
                subject=subject,
                body=body,
            )

            if success:
                # Log communication
                await comm_service.log_communication(
                    transaction_id=request.transaction_id,
                    direction="outbound",
                    channel="email",
                    from_party=current_user.email,
                    to_party=email,
                    subject=subject,
                    body=body,
                )
                sent += 1
            else:
                failed += 1

            results[email] = success

        except Exception as e:
            results[email] = False
            failed += 1

    return BulkEmailResponse(
        total=len(request.recipients),
        sent=sent,
        failed=failed,
        results=results,
    )
