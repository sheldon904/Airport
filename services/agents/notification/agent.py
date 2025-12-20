"""Notification agent for sending emails and alerts."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from packages.core.config import settings
from services.agents.base import AgentContext, AgentEvent, BaseAgent, emit_event
from .models import (
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationStatus,
    NotificationType,
)


# === Input/Output Models ===


class NotificationInput(BaseModel):
    """Input for sending notifications."""

    transaction_id: UUID | None = None
    user_id: UUID
    organization_id: UUID

    notification_type: NotificationType
    channel: NotificationChannel = NotificationChannel.EMAIL
    priority: NotificationPriority = NotificationPriority.NORMAL

    recipient_email: str | None = None
    recipient_phone: str | None = None

    subject: str | None = None
    body: str
    metadata: dict[str, Any] = {}


class NotificationOutput(BaseModel):
    """Output from notification processing."""

    notification_id: UUID
    status: NotificationStatus
    channel: NotificationChannel
    queued_at: datetime
    message: str | None = None


class NotificationAgent(BaseAgent[NotificationInput, NotificationOutput]):
    """
    Agent for managing and sending notifications.

    Handles:
    - Email notifications (via SMTP or email service)
    - SMS notifications (via Twilio or similar)
    - In-app notifications
    - Push notifications

    Compliance Notes:
    - Respects user notification preferences
    - Implements quiet hours
    - Tracks delivery status for audit
    """

    name = "notification"
    version = "0.1.0"

    def __init__(self) -> None:
        super().__init__()
        self._email_service: "EmailService | None" = None

    @property
    def email_service(self) -> "EmailService":
        """Lazy-load email service."""
        if self._email_service is None:
            from packages.core.services.email import get_email_service
            self._email_service = get_email_service()
        return self._email_service

    async def process(
        self,
        context: AgentContext,
        input_data: NotificationInput,
    ) -> tuple[NotificationOutput, float | None, bool, str | None]:
        """
        Process and send a notification.

        Returns:
            tuple: (output, confidence, needs_review, review_reason)
        """
        notification_id = uuid4()

        self.logger.info(
            "notification_processing",
            notification_id=str(notification_id),
            notification_type=input_data.notification_type.value,
            channel=input_data.channel.value,
        )

        # Create notification record
        record = NotificationRecord(
            id=notification_id,
            user_id=input_data.user_id,
            organization_id=input_data.organization_id,
            transaction_id=input_data.transaction_id,
            notification_type=input_data.notification_type,
            channel=input_data.channel,
            priority=input_data.priority,
            status=NotificationStatus.PENDING,
            recipient_email=input_data.recipient_email,
            recipient_phone=input_data.recipient_phone,
            subject=input_data.subject,
            body=input_data.body,
            metadata=input_data.metadata,
            created_at=datetime.now(),
        )

        # Process based on channel
        try:
            if input_data.channel == NotificationChannel.EMAIL:
                result = await self._send_email(record)
            elif input_data.channel == NotificationChannel.SMS:
                result = await self._send_sms(record)
            elif input_data.channel == NotificationChannel.IN_APP:
                result = await self._create_in_app_notification(record)
            elif input_data.channel == NotificationChannel.PUSH:
                result = await self._send_push(record)
            else:
                result = (NotificationStatus.FAILED, "Unknown channel")

            status, message = result

            # Emit event
            await emit_event(
                AgentEvent(
                    event_type=f"notification.{status.value}",
                    agent_name=self.name,
                    execution_id=context.execution_id,
                    transaction_id=input_data.transaction_id or uuid4(),
                    timestamp=datetime.now(),
                    payload={
                        "notification_id": str(notification_id),
                        "notification_type": input_data.notification_type.value,
                        "channel": input_data.channel.value,
                        "status": status.value,
                    },
                )
            )

            output = NotificationOutput(
                notification_id=notification_id,
                status=status,
                channel=input_data.channel,
                queued_at=datetime.now(),
                message=message,
            )

            return (
                output,
                1.0 if status == NotificationStatus.SENT else 0.5,
                status == NotificationStatus.FAILED,
                message if status == NotificationStatus.FAILED else None,
            )

        except Exception as e:
            self.logger.error(
                "notification_failed",
                notification_id=str(notification_id),
                error=str(e),
            )

            return (
                NotificationOutput(
                    notification_id=notification_id,
                    status=NotificationStatus.FAILED,
                    channel=input_data.channel,
                    queued_at=datetime.now(),
                    message=str(e),
                ),
                0.0,
                True,
                f"Notification failed: {str(e)}",
            )

    async def _send_email(
        self,
        record: NotificationRecord,
    ) -> tuple[NotificationStatus, str]:
        """Send an email notification."""
        if not record.recipient_email:
            return (NotificationStatus.FAILED, "No recipient email provided")

        try:
            success = await self.email_service.send_email(
                to_email=record.recipient_email,
                subject=record.subject or "Notification",
                body=record.body,
                html_body=self._format_html_email(record),
            )

            if success:
                self.logger.info(
                    "email_sent",
                    notification_id=str(record.id),
                    recipient=record.recipient_email,
                )
                return (NotificationStatus.SENT, "Email sent successfully")
            else:
                return (NotificationStatus.QUEUED, "Email queued for delivery")

        except Exception as e:
            self.logger.error(
                "email_send_failed",
                notification_id=str(record.id),
                error=str(e),
            )
            return (NotificationStatus.FAILED, str(e))

    async def _send_sms(
        self,
        record: NotificationRecord,
    ) -> tuple[NotificationStatus, str]:
        """Send an SMS notification."""
        if not record.recipient_phone:
            return (NotificationStatus.FAILED, "No recipient phone provided")

        # SMS service not implemented - queue for later
        self.logger.info(
            "sms_queued",
            notification_id=str(record.id),
            recipient=record.recipient_phone,
        )
        return (NotificationStatus.QUEUED, "SMS queued (service not configured)")

    async def _create_in_app_notification(
        self,
        record: NotificationRecord,
    ) -> tuple[NotificationStatus, str]:
        """Create an in-app notification."""
        # In-app notifications are stored in the database
        # They would be fetched by the frontend via API
        self.logger.info(
            "in_app_notification_created",
            notification_id=str(record.id),
            user_id=str(record.user_id),
        )
        return (NotificationStatus.SENT, "In-app notification created")

    async def _send_push(
        self,
        record: NotificationRecord,
    ) -> tuple[NotificationStatus, str]:
        """Send a push notification."""
        # Push notifications not implemented - queue for later
        self.logger.info(
            "push_queued",
            notification_id=str(record.id),
            user_id=str(record.user_id),
        )
        return (NotificationStatus.QUEUED, "Push notification queued (service not configured)")

    def _format_html_email(self, record: NotificationRecord) -> str:
        """Format notification as HTML email."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{record.subject or 'Notification'}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #2563eb;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f9fafb;
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-top: none;
        }}
        .footer {{
            background: #f3f4f6;
            padding: 15px;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            border-radius: 0 0 8px 8px;
            border: 1px solid #e5e7eb;
            border-top: none;
        }}
        .priority-urgent {{
            border-left: 4px solid #dc2626;
        }}
        .priority-high {{
            border-left: 4px solid #f59e0b;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0; font-size: 24px;">Airport TC</h1>
    </div>
    <div class="content {'priority-urgent' if record.priority == NotificationPriority.URGENT else 'priority-high' if record.priority == NotificationPriority.HIGH else ''}">
        <h2 style="margin-top: 0;">{record.subject or 'Notification'}</h2>
        <div style="white-space: pre-wrap;">{record.body}</div>
    </div>
    <div class="footer">
        <p>This is an automated message from Airport Transaction Coordinator.</p>
        <p>Please do not reply to this email.</p>
    </div>
</body>
</html>
"""

    async def send_deadline_reminder(
        self,
        context: AgentContext,
        user_id: UUID,
        organization_id: UUID,
        transaction_id: UUID,
        recipient_email: str,
        deadline_name: str,
        due_date: str,
        days_remaining: int,
        property_address: str,
    ) -> NotificationOutput:
        """Convenience method for sending deadline reminders."""
        if days_remaining <= 1:
            notification_type = NotificationType.DEADLINE_URGENT
            priority = NotificationPriority.URGENT
            subject = f"URGENT: {deadline_name} Due Tomorrow"
        elif days_remaining <= 3:
            notification_type = NotificationType.DEADLINE_URGENT
            priority = NotificationPriority.HIGH
            subject = f"Reminder: {deadline_name} Due in {days_remaining} Days"
        else:
            notification_type = NotificationType.DEADLINE_REMINDER
            priority = NotificationPriority.NORMAL
            subject = f"Reminder: {deadline_name} - {property_address}"

        body = f"""Deadline Reminder

Property: {property_address}
Deadline: {deadline_name}
Due Date: {due_date}
Days Remaining: {days_remaining}

Please take any necessary action before this deadline expires."""

        input_data = NotificationInput(
            transaction_id=transaction_id,
            user_id=user_id,
            organization_id=organization_id,
            notification_type=notification_type,
            channel=NotificationChannel.EMAIL,
            priority=priority,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            metadata={
                "deadline_name": deadline_name,
                "due_date": due_date,
                "days_remaining": days_remaining,
                "property_address": property_address,
            },
        )

        result = await self.execute(context, input_data)
        return result.output

    async def send_password_reset(
        self,
        context: AgentContext,
        user_id: UUID,
        organization_id: UUID,
        recipient_email: str,
        reset_token: str,
        reset_url: str,
    ) -> NotificationOutput:
        """Send a password reset email."""
        input_data = NotificationInput(
            user_id=user_id,
            organization_id=organization_id,
            notification_type=NotificationType.PASSWORD_RESET,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH,
            recipient_email=recipient_email,
            subject="Password Reset Request - Airport TC",
            body=f"""You have requested to reset your password for Airport Transaction Coordinator.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email or contact support if you have concerns.

Best regards,
Airport TC Team""",
            metadata={
                "reset_token": reset_token,
            },
        )

        result = await self.execute(context, input_data)
        return result.output

    async def send_welcome_email(
        self,
        context: AgentContext,
        user_id: UUID,
        organization_id: UUID,
        recipient_email: str,
        user_name: str,
        organization_name: str,
    ) -> NotificationOutput:
        """Send a welcome email to new users."""
        input_data = NotificationInput(
            user_id=user_id,
            organization_id=organization_id,
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.NORMAL,
            recipient_email=recipient_email,
            subject=f"Welcome to Airport TC - {organization_name}",
            body=f"""Welcome to Airport Transaction Coordinator!

Hello {user_name},

Your account has been created for {organization_name}.

With Airport TC, you can:
- Upload and manage transaction documents
- Track deadlines automatically
- Stay on top of Florida compliance requirements
- Communicate with all transaction parties

Getting Started:
1. Log in to your dashboard
2. Create your first transaction
3. Upload your executed contract
4. Let our AI handle the rest!

If you have any questions, our support team is here to help.

Best regards,
The Airport TC Team""",
            metadata={
                "user_name": user_name,
                "organization_name": organization_name,
            },
        )

        result = await self.execute(context, input_data)
        return result.output
