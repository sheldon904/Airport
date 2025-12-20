"""Agent orchestrator for coordinating multi-agent workflows."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel

from services.agents.base import AgentContext, AgentEvent, emit_event
from services.agents.document_extract.agent import (
    DocumentExtractAgent,
    DocumentExtractInput,
    DocumentExtractOutput,
)
from services.agents.deadline.agent import DeadlineAgent, DeadlineInput

logger = structlog.get_logger()


class WorkflowStep(BaseModel):
    """A step in an agent workflow."""

    step_id: str
    agent_name: str
    status: str = "pending"  # pending, running, completed, failed, needs_review
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: dict[str, Any] | None = None
    error: str | None = None


class Workflow(BaseModel):
    """A multi-step agent workflow."""

    id: UUID
    workflow_type: str
    transaction_id: UUID
    status: str = "running"
    steps: list[WorkflowStep]
    created_at: datetime
    completed_at: datetime | None = None


class AgentOrchestrator:
    """
    Coordinates multi-agent workflows for transaction processing.

    Handles:
    - Spinning up appropriate agents based on events
    - Chaining agent outputs to downstream agents
    - Managing human review checkpoints
    - Error handling and retry logic
    """

    def __init__(self) -> None:
        self.logger = logger.bind(component="orchestrator")

        # Initialize agents
        self.document_extract_agent = DocumentExtractAgent()
        self.deadline_agent = DeadlineAgent()

    async def handle_document_uploaded(
        self,
        transaction_id: UUID,
        organization_id: UUID,
        document_id: UUID,
        document_type: str,
        storage_path: str,
        filename: str,
        user_id: UUID | None = None,
    ) -> Workflow:
        """
        Handle a document upload event.

        Workflow:
        1. DocumentExtractAgent extracts data from document
        2. If purchase contract, DeadlineAgent calculates timeline
        3. ChecklistAgent updates document status
        4. Queue human review if needed
        """
        workflow_id = uuid4()

        self.logger.info(
            "document_upload_workflow_started",
            workflow_id=str(workflow_id),
            transaction_id=str(transaction_id),
            document_id=str(document_id),
        )

        # Create workflow
        workflow = Workflow(
            id=workflow_id,
            workflow_type="document_upload",
            transaction_id=transaction_id,
            steps=[
                WorkflowStep(step_id="extract", agent_name="document_extract"),
                WorkflowStep(step_id="deadlines", agent_name="deadline"),
                WorkflowStep(step_id="checklist", agent_name="checklist"),
            ],
            created_at=datetime.now(),
        )

        # Step 1: Extract document data
        context = AgentContext(
            execution_id=uuid4(),
            transaction_id=transaction_id,
            organization_id=organization_id,
            user_id=user_id,
            triggered_by="system",
            triggered_at=datetime.now(),
        )

        extract_input = DocumentExtractInput(
            document_id=document_id,
            document_type=document_type,
            storage_path=storage_path,
            filename=filename,
        )

        workflow.steps[0].status = "running"
        workflow.steps[0].started_at = datetime.now()

        result = await self.document_extract_agent.execute(context, extract_input)

        if result.success and result.output:
            workflow.steps[0].status = (
                "needs_review" if result.needs_human_review else "completed"
            )
            workflow.steps[0].completed_at = datetime.now()
            workflow.steps[0].output = result.output.model_dump()

            # Emit extraction complete event
            await emit_event(
                AgentEvent(
                    event_type="extraction.complete",
                    agent_name="document_extract",
                    execution_id=result.execution_id,
                    transaction_id=transaction_id,
                    timestamp=datetime.now(),
                    payload={
                        "document_id": str(document_id),
                        "confidence": result.confidence,
                        "needs_review": result.needs_human_review,
                    },
                )
            )

            # Step 2: Calculate deadlines if this is a contract
            if document_type == "purchase_contract" and result.output.effective_date:
                await self._run_deadline_calculation(
                    workflow, context, result.output
                )
        else:
            workflow.steps[0].status = "failed"
            workflow.steps[0].error = result.error
            workflow.status = "failed"

        return workflow

    async def _run_deadline_calculation(
        self,
        workflow: Workflow,
        context: AgentContext,
        extract_output: DocumentExtractOutput,
    ) -> None:
        """Run deadline calculation as part of workflow."""
        if not extract_output.effective_date or not extract_output.closing_date:
            self.logger.warning(
                "skipping_deadline_calculation",
                reason="missing effective or closing date",
            )
            workflow.steps[1].status = "skipped"
            return

        workflow.steps[1].status = "running"
        workflow.steps[1].started_at = datetime.now()

        deadline_input = DeadlineInput(
            transaction_id=context.transaction_id,
            effective_date=extract_output.effective_date,
            closing_date=extract_output.closing_date,
            contingencies=[c.model_dump() for c in extract_output.contingencies],
            state="FL",
        )

        result = await self.deadline_agent.execute(context, deadline_input)

        if result.success:
            workflow.steps[1].status = (
                "needs_review" if result.needs_human_review else "completed"
            )
            workflow.steps[1].completed_at = datetime.now()
            workflow.steps[1].output = result.output.model_dump() if result.output else None

            # Emit deadlines calculated event
            await emit_event(
                AgentEvent(
                    event_type="deadlines.calculated",
                    agent_name="deadline",
                    execution_id=result.execution_id,
                    transaction_id=context.transaction_id,
                    timestamp=datetime.now(),
                    payload={
                        "deadline_count": len(result.output.deadlines) if result.output else 0,
                        "warnings": result.output.warnings if result.output else [],
                    },
                )
            )
        else:
            workflow.steps[1].status = "failed"
            workflow.steps[1].error = result.error

    async def handle_deadline_approaching(
        self,
        transaction_id: UUID,
        deadline_id: UUID,
        days_remaining: int,
    ) -> None:
        """
        Handle a deadline approaching event.

        Triggers:
        - NotificationAgent to send reminders
        - CommunicationAgent to draft status update if needed
        """
        self.logger.info(
            "deadline_approaching",
            transaction_id=str(transaction_id),
            deadline_id=str(deadline_id),
            days_remaining=days_remaining,
        )

        # TODO: Implement notification workflow
        pass

    async def handle_review_completed(
        self,
        transaction_id: UUID,
        review_type: str,
        approved: bool,
        corrections: dict[str, Any] | None = None,
    ) -> None:
        """
        Handle human review completion.

        Continues paused workflows or triggers corrective actions.
        """
        self.logger.info(
            "review_completed",
            transaction_id=str(transaction_id),
            review_type=review_type,
            approved=approved,
        )

        # TODO: Implement review continuation workflow
        pass
