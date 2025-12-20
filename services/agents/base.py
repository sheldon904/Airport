"""Base agent class and shared utilities."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel

from packages.core.config import settings

logger = structlog.get_logger()

# Type variables for input/output
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentContext(BaseModel):
    """Context passed to every agent execution."""

    execution_id: UUID
    transaction_id: UUID
    organization_id: UUID
    user_id: UUID | None = None
    triggered_by: str  # "user", "system", "agent:<agent_name>"
    triggered_at: datetime
    metadata: dict[str, Any] = {}


class AgentResult(BaseModel, Generic[OutputT]):
    """Standard result wrapper for agent outputs."""

    success: bool
    execution_id: UUID
    agent_name: str
    output: OutputT | None = None
    error: str | None = None
    needs_human_review: bool = False
    review_reason: str | None = None
    confidence: float | None = None
    duration_ms: int = 0
    events_emitted: list[str] = []


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Base class for all Airport agents.

    Agents are stateless workers that:
    1. Receive structured input
    2. Perform AI-assisted processing
    3. Return structured output
    4. Emit events for downstream processing
    5. Flag items requiring human review
    """

    name: str = "base_agent"
    version: str = "0.1.0"

    def __init__(self) -> None:
        self.logger = logger.bind(agent=self.name, version=self.version)

    async def execute(
        self,
        context: AgentContext,
        input_data: InputT,
    ) -> AgentResult[OutputT]:
        """
        Execute the agent with full lifecycle handling.

        This method handles:
        - Logging and telemetry
        - Error handling and recovery
        - Human review flagging
        - Event emission
        """
        start_time = datetime.now()
        execution_id = context.execution_id or uuid4()

        self.logger.info(
            "agent_execution_started",
            execution_id=str(execution_id),
            transaction_id=str(context.transaction_id),
        )

        try:
            # Run the agent's core logic
            output, confidence, review_needed, review_reason = await self.process(
                context, input_data
            )

            # Check confidence threshold
            if confidence is not None and confidence < settings.require_human_review_below:
                review_needed = True
                review_reason = review_reason or f"Low confidence: {confidence:.2%}"

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.info(
                "agent_execution_completed",
                execution_id=str(execution_id),
                confidence=confidence,
                needs_review=review_needed,
                duration_ms=duration_ms,
            )

            return AgentResult(
                success=True,
                execution_id=execution_id,
                agent_name=self.name,
                output=output,
                needs_human_review=review_needed,
                review_reason=review_reason,
                confidence=confidence,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.error(
                "agent_execution_failed",
                execution_id=str(execution_id),
                error=str(e),
                duration_ms=duration_ms,
            )

            return AgentResult(
                success=False,
                execution_id=execution_id,
                agent_name=self.name,
                error=str(e),
                needs_human_review=True,
                review_reason=f"Agent failed: {str(e)}",
                duration_ms=duration_ms,
            )

    @abstractmethod
    async def process(
        self,
        context: AgentContext,
        input_data: InputT,
    ) -> tuple[OutputT, float | None, bool, str | None]:
        """
        Core processing logic to be implemented by each agent.

        Returns:
            tuple: (output, confidence, needs_review, review_reason)
        """
        pass


class AgentEvent(BaseModel):
    """Event emitted by an agent for downstream processing."""

    event_type: str
    agent_name: str
    execution_id: UUID
    transaction_id: UUID
    timestamp: datetime
    payload: dict[str, Any]


async def emit_event(event: AgentEvent) -> None:
    """
    Emit an event to the event bus.

    Other agents and services can subscribe to these events.
    """
    from packages.core.services.events import get_event_bus

    event_bus = get_event_bus()

    await event_bus.publish(
        event_type=event.event_type,
        payload=event.payload,
        transaction_id=event.transaction_id,
        agent_name=event.agent_name,
    )

    logger.info(
        "event_emitted",
        event_type=event.event_type,
        transaction_id=str(event.transaction_id),
    )
