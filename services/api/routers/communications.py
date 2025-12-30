"""Communication management and email sending endpoints."""

import html
import logging
import re
from datetime import datetime, timezone
from string import Template
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
from packages.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# === Email Templates ===
# REM-004: Templates use $variable syntax for safe string.Template substitution
# This prevents format string injection attacks

EMAIL_TEMPLATES = {
    "earnest_money_receipt": {
        "subject": "Earnest Money Deposit Received - $property_address",
        "body": """Dear $recipient_name,

This email confirms receipt of the earnest money deposit for the property at $property_address.

Deposit Details:
- Amount: $amount
- Date Received: $date_received
- Transaction ID: $transaction_id

The deposit is being held in escrow per the terms of the purchase agreement.

Please retain this email for your records.

Best regards,
$sender_name
$company_name""",
        "required_vars": ["recipient_name", "property_address", "amount", "date_received", "transaction_id", "sender_name", "company_name"],
    },
    "deadline_reminder": {
        "subject": "Deadline Reminder: $deadline_name - $property_address",
        "body": """Dear $recipient_name,

This is a reminder that the following deadline is approaching:

Deadline: $deadline_name
Due Date: $due_date
Property: $property_address

Please ensure all required actions are completed before this date.

If you have any questions, please don't hesitate to reach out.

Best regards,
$sender_name
$company_name""",
        "required_vars": ["recipient_name", "deadline_name", "due_date", "property_address", "sender_name", "company_name"],
    },
    "document_request": {
        "subject": "Document Request - $property_address",
        "body": """Dear $recipient_name,

We are missing the following document(s) for the transaction at $property_address:

$document_list

Please submit these documents at your earliest convenience to avoid delays in the closing process.

You can upload documents directly through our secure portal:
$portal_link

Best regards,
$sender_name
$company_name""",
        "required_vars": ["recipient_name", "property_address", "document_list", "portal_link", "sender_name", "company_name"],
    },
    "closing_confirmation": {
        "subject": "Closing Scheduled - $property_address",
        "body": """Dear $recipient_name,

Your closing has been scheduled for the property at $property_address.

Closing Details:
- Date: $closing_date
- Time: $closing_time
- Location: $closing_location

Please bring the following to closing:
- Valid government-issued photo ID
- Certified funds as specified in closing disclosure
- Any additional documents requested

If you need to reschedule or have questions, please contact us immediately.

Best regards,
$sender_name
$company_name""",
        "required_vars": ["recipient_name", "property_address", "closing_date", "closing_time", "closing_location", "sender_name", "company_name"],
    },
    "general": {
        "subject": "$subject",
        "body": """$body

Best regards,
$sender_name
$company_name""",
        "required_vars": ["subject", "body", "sender_name", "company_name"],
    },
}


# === HTML Template Wrapper ===
# REM-009: Generate HTML version from plain text

HTML_WRAPPER = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            border-bottom: 2px solid #0066cc;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }
        p { margin: 10px 0; }
        ul { margin: 10px 0; padding-left: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <strong>$company_name</strong>
    </div>
    <div class="content">
        $html_content
    </div>
    <div class="footer">
        <p>This email was sent by $company_name.</p>
        <p>If you have questions, please contact your transaction coordinator.</p>
    </div>
</body>
</html>"""


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


class TemplateError(Exception):
    """Custom exception for template rendering errors."""
    pass


def _sanitize_variable(value: Any) -> str:
    """
    Sanitize a variable value for safe inclusion in templates.

    REM-004: Prevent injection attacks by escaping special characters.
    """
    if value is None:
        return ""
    str_value = str(value)
    # Remove any dollar signs to prevent Template injection
    str_value = str_value.replace("$", "")
    return str_value


def _get_company_name(organization_id: UUID | None = None) -> str:
    """
    Get company name from organization settings.

    REM-008, REM-013: Use configurable company name instead of hardcoded value.
    """
    # For now, use app_name from settings
    # In future, this could look up organization-specific branding
    return getattr(settings, "app_name", "Airport TC")


def _validate_template_variables(
    template_name: str,
    variables: dict[str, Any],
) -> list[str]:
    """
    Validate that all required variables are present.

    REM-010: Proper error handling for missing template variables.

    Returns list of missing variable names.
    """
    template_def = EMAIL_TEMPLATES.get(template_name)
    if not template_def:
        return []

    required = template_def.get("required_vars", [])
    missing = [var for var in required if var not in variables or variables[var] is None]
    return missing


def _text_to_html(text: str) -> str:
    """
    Convert plain text to HTML with proper escaping.

    REM-009: Generate HTML version from plain text.
    """
    # Escape HTML special characters
    escaped = html.escape(text)
    # Convert newlines to <br> tags
    with_breaks = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
    # Wrap in paragraph tags
    return f"<p>{with_breaks}</p>"


def render_template(
    template_name: str,
    variables: dict[str, Any],
    generate_html: bool = True,
) -> tuple[str, str, str | None]:
    """
    Render an email template with variables safely.

    REM-004: Uses string.Template instead of str.format() to prevent injection.
    REM-010: Validates variables and provides clear error messages.
    REM-009: Optionally generates HTML version.

    Returns (subject, body, html_body).

    Raises TemplateError if template not found or variables missing.
    """
    template_def = EMAIL_TEMPLATES.get(template_name)
    if not template_def:
        raise TemplateError(f"Template not found: {template_name}")

    # Validate required variables
    missing = _validate_template_variables(template_name, variables)
    if missing:
        raise TemplateError(
            f"Missing required variables for template '{template_name}': {', '.join(missing)}"
        )

    # Sanitize all variable values
    safe_vars = {key: _sanitize_variable(value) for key, value in variables.items()}

    try:
        # Use string.Template for safe substitution
        subject_template = Template(template_def["subject"])
        body_template = Template(template_def["body"])

        subject = subject_template.safe_substitute(safe_vars)
        body = body_template.safe_substitute(safe_vars)

        # Check for unsubstituted variables (indicates missing optional vars)
        if "$" in subject or "$" in body:
            # Find which variables are still present
            remaining = re.findall(r'\$(\w+)', subject + body)
            logger.warning(
                "template_unsubstituted_variables",
                extra={
                    "template": template_name,
                    "remaining_vars": remaining,
                }
            )

        # Generate HTML version if requested
        html_body = None
        if generate_html:
            html_content = _text_to_html(body)
            html_template = Template(HTML_WRAPPER)
            html_body = html_template.safe_substitute(
                html_content=html_content,
                company_name=safe_vars.get("company_name", _get_company_name()),
            )

        return subject, body, html_body

    except Exception as e:
        logger.error(
            "template_render_error",
            extra={
                "template": template_name,
                "error_type": type(e).__name__,
                "error": str(e),
            }
        )
        raise TemplateError(f"Failed to render template: {str(e)}")


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
                "variables": template_def.get("required_vars", []),
            }
            for name, template_def in EMAIL_TEMPLATES.items()
        ]
    }


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

    # REM-008, REM-013: Use configurable company name
    company_name = _get_company_name(current_user.organization_id)

    base_variables = {
        "property_address": f"{street}, {city}",
        "transaction_id": str(transaction.id),
        "recipient_name": request.recipient_name,
        "sender_name": current_user.name or "Transaction Coordinator",
        "company_name": company_name,
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
        # REM-004, REM-010: Safe template rendering with validation
        subject, body, html_body = render_template(request.template, variables)
    except TemplateError as e:
        # REM-010: Clear error message without exposing internals
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Generate draft ID
    draft_id = f"draft-{transaction.id}-{datetime.now(timezone.utc).timestamp()}"

    return DraftEmailResponse(
        draft_id=draft_id,
        subject=subject,
        body=body,
        html_body=html_body,  # REM-009: Now includes HTML version
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
            message_id=f"msg-{datetime.now(timezone.utc).timestamp()}",
            communication_id=communication_id,
        )

    except Exception as e:
        # REM-014: Consistent error response - don't expose internal details
        logger.error(
            "email_send_failed",
            extra={
                "transaction_id": str(request.transaction_id),
                "to_email": request.to_email,
                "error_type": type(e).__name__,
                "error": str(e),
            }
        )
        return SendEmailResponse(
            success=False,
            error="Failed to send email. Please try again later.",
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
    # REM-008, REM-013: Use configurable company name
    company_name = _get_company_name(current_user.organization_id)

    base_variables = {
        "property_address": f"{property_address.get('street', '')}, {property_address.get('city', '')}",
        "transaction_id": str(transaction.id),
        "sender_name": current_user.name or "Transaction Coordinator",
        "company_name": company_name,
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
            # REM-004: Safe template rendering
            subject, body, html_body = render_template(request.template, variables)
            success = await email_service.send_email(
                to_email=email,
                subject=subject,
                body=body,
                html_body=html_body,
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

        except TemplateError as e:
            logger.warning(
                "bulk_email_template_error",
                extra={
                    "email": email,
                    "error": str(e),
                }
            )
            results[email] = False
            failed += 1
        except Exception as e:
            logger.error(
                "bulk_email_send_error",
                extra={
                    "email": email,
                    "error_type": type(e).__name__,
                    "error": str(e),
                }
            )
            results[email] = False
            failed += 1

    return BulkEmailResponse(
        total=len(request.recipients),
        sent=sent,
        failed=failed,
        results=results,
    )
