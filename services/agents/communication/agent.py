"""Communication agent for drafting transaction status updates."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from services.agents.base import AgentContext, AgentEvent, BaseAgent, emit_event
from .templates import (
    CommunicationTemplate,
    CommunicationType,
    FL_COMMUNICATION_TEMPLATES,
    get_template,
    render_template,
)


# === Input/Output Models ===


class Recipient(BaseModel):
    """A communication recipient."""

    role: str
    name: str
    email: str


class CommunicationInput(BaseModel):
    """Input for communication drafting."""

    transaction_id: UUID
    communication_type: str
    template_id: str | None = None
    recipients: list[Recipient] = []
    context: dict[str, Any] = {}
    custom_message: str | None = None


class DraftedCommunication(BaseModel):
    """A drafted communication."""

    id: UUID
    template_id: str
    communication_type: str
    recipient: Recipient
    subject: str
    body: str
    created_at: datetime
    requires_review: bool = True


class CommunicationOutput(BaseModel):
    """Output from communication drafting."""

    transaction_id: UUID
    drafts: list[DraftedCommunication]
    warnings: list[str] = []


class CommunicationAgent(BaseAgent[CommunicationInput, CommunicationOutput]):
    """
    Agent for drafting transaction communications.

    Handles:
    - Generating status update drafts from templates
    - Personalizing communications for each recipient
    - Queuing drafts for human review and approval
    - Tracking communication history

    Compliance Notes:
    - All communications require human review before sending
    - Does NOT send communications automatically
    - Templates are pre-approved for FL real estate transactions
    """

    name = "communication"
    version = "0.1.0"

    async def process(
        self,
        context: AgentContext,
        input_data: CommunicationInput,
    ) -> tuple[CommunicationOutput, float | None, bool, str | None]:
        """
        Draft communications for a transaction.

        Returns:
            tuple: (output, confidence, needs_review, review_reason)
        """
        self.logger.info(
            "communication_drafting",
            transaction_id=str(input_data.transaction_id),
            communication_type=input_data.communication_type,
        )

        drafts: list[DraftedCommunication] = []
        warnings: list[str] = []

        # Get template
        template_id = input_data.template_id or input_data.communication_type
        template = get_template(template_id)

        if not template:
            # Use custom message or return error
            if input_data.custom_message:
                for recipient in input_data.recipients:
                    drafts.append(
                        DraftedCommunication(
                            id=uuid4(),
                            template_id="custom",
                            communication_type=CommunicationType.CUSTOM.value,
                            recipient=recipient,
                            subject=input_data.context.get("subject", "Transaction Update"),
                            body=input_data.custom_message,
                            created_at=datetime.now(),
                            requires_review=True,
                        )
                    )
            else:
                return (
                    CommunicationOutput(
                        transaction_id=input_data.transaction_id,
                        drafts=[],
                        warnings=[f"Template not found: {template_id}"],
                    ),
                    0.5,
                    True,
                    f"Template not found: {template_id}",
                )
        else:
            # Check for missing required fields
            missing_fields = []
            for field in template.required_fields:
                if field not in input_data.context or input_data.context[field] is None:
                    missing_fields.append(field)

            if missing_fields:
                warnings.append(f"Missing fields: {', '.join(missing_fields)}")

            # Generate drafts for each recipient
            for recipient in input_data.recipients:
                # Build recipient-specific context
                recipient_context = {
                    **input_data.context,
                    "recipient_name": recipient.name,
                    "recipient_email": recipient.email,
                    "recipient_role": recipient.role,
                }

                # Render template
                subject, body = render_template(template, recipient_context)

                drafts.append(
                    DraftedCommunication(
                        id=uuid4(),
                        template_id=template.id,
                        communication_type=template.type.value,
                        recipient=recipient,
                        subject=subject,
                        body=body,
                        created_at=datetime.now(),
                        requires_review=True,
                    )
                )

        # All communications require human review
        output = CommunicationOutput(
            transaction_id=input_data.transaction_id,
            drafts=drafts,
            warnings=warnings,
        )

        # Emit event for each draft
        for draft in drafts:
            await emit_event(
                AgentEvent(
                    event_type="communication.drafted",
                    agent_name=self.name,
                    execution_id=context.execution_id,
                    transaction_id=input_data.transaction_id,
                    timestamp=datetime.now(),
                    payload={
                        "draft_id": str(draft.id),
                        "template_id": draft.template_id,
                        "recipient_email": draft.recipient.email,
                        "requires_review": draft.requires_review,
                    },
                )
            )

        # Always needs review for communications
        return (
            output,
            0.95 if not warnings else 0.75,
            True,
            "Communications require approval before sending",
        )

    async def draft_deadline_reminder(
        self,
        context: AgentContext,
        transaction_id: UUID,
        deadline_name: str,
        due_date: str,
        days_remaining: int,
        property_address: str,
        recipients: list[Recipient],
        sender_name: str,
    ) -> CommunicationOutput:
        """Convenience method for drafting deadline reminders."""
        template_id = "deadline_urgent" if days_remaining <= 1 else "deadline_reminder"

        input_data = CommunicationInput(
            transaction_id=transaction_id,
            communication_type=template_id,
            template_id=template_id,
            recipients=recipients,
            context={
                "deadline_name": deadline_name,
                "due_date": due_date,
                "days_remaining": days_remaining,
                "property_address": property_address,
                "sender_name": sender_name,
                "deadline_description": "",
            },
        )

        result = await self.execute(context, input_data)
        return result.output

    async def draft_status_update(
        self,
        context: AgentContext,
        transaction_id: UUID,
        property_address: str,
        transaction_status: str,
        status_details: str,
        deadline_summary: str,
        checklist_progress: int,
        recipients: list[Recipient],
        sender_name: str,
    ) -> CommunicationOutput:
        """Convenience method for drafting status updates."""
        input_data = CommunicationInput(
            transaction_id=transaction_id,
            communication_type="status_update",
            template_id="status_update",
            recipients=recipients,
            context={
                "property_address": property_address,
                "transaction_status": transaction_status,
                "status_details": status_details,
                "deadline_summary": deadline_summary,
                "checklist_progress": checklist_progress,
                "sender_name": sender_name,
            },
        )

        result = await self.execute(context, input_data)
        return result.output
