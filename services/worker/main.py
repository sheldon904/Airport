"""Background worker main entry point."""

import asyncio
import signal
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog

from packages.core.config import settings
from packages.core.services.audit import AuditAction, AuditService
from packages.db.session import AsyncSessionLocal
from packages.db.repositories.job_queue import JobQueueRepository
from packages.db.repositories.document import DocumentRepository
from packages.db.repositories.deadline import DeadlineRepository
from packages.db.repositories.transaction import TransactionRepository
from packages.db.repositories.user import UserRepository
from services.agents.document_extract.agent import (
    DocumentExtractAgent,
    DocumentExtractInput,
)
from services.agents.deadline.agent import DeadlineAgent, DeadlineInput
from services.agents.notification.agent import NotificationAgent
from services.agents.base import AgentContext

logger = structlog.get_logger()


class ExponentialBackoff:
    """
    Exponential backoff with jitter for polling.

    Starts at min_delay, doubles on each empty poll (up to max_delay),
    and resets to min_delay when a job is processed.
    """

    def __init__(
        self,
        min_delay: float = 0.5,
        max_delay: float = 30.0,
        multiplier: float = 2.0,
        jitter: float = 0.1,
    ) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self._current_delay = min_delay

    def reset(self) -> None:
        """Reset delay to minimum after processing a job."""
        self._current_delay = self.min_delay

    def increase(self) -> None:
        """Increase delay after an empty poll."""
        self._current_delay = min(
            self._current_delay * self.multiplier,
            self.max_delay,
        )

    async def wait(self) -> None:
        """Wait for the current delay with jitter."""
        import random

        jitter_amount = self._current_delay * self.jitter * random.random()
        await asyncio.sleep(self._current_delay + jitter_amount)

    @property
    def current_delay(self) -> float:
        """Current delay in seconds."""
        return self._current_delay


class Worker:
    """
    Background worker for processing agent jobs.

    Features:
    - Polls the job queue with exponential backoff
    - Graceful shutdown on SIGTERM/SIGINT
    - Automatic retry with exponential backoff on failures
    - Audit logging for job execution
    """

    def __init__(self) -> None:
        self.running = False
        self.current_job_id: UUID | None = None
        self.backoff = ExponentialBackoff()
        self.jobs_processed = 0
        self.jobs_failed = 0

        # Initialize agents
        self.document_extract_agent = DocumentExtractAgent()
        self.deadline_agent = DeadlineAgent()
        self.notification_agent = NotificationAgent()

    async def start(self) -> None:
        """Start the worker loop."""
        self.running = True
        logger.info("worker_started", pid=asyncio.current_task().get_name())

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        while self.running:
            try:
                job_found = await self._process_next_job()

                if job_found:
                    self.backoff.reset()
                else:
                    self.backoff.increase()
                    await self.backoff.wait()

            except Exception as e:
                logger.error("worker_error", error=str(e), exc_info=True)
                self.backoff.increase()
                await self.backoff.wait()

        logger.info(
            "worker_stopped",
            jobs_processed=self.jobs_processed,
            jobs_failed=self.jobs_failed,
        )

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("shutdown_requested", current_job=str(self.current_job_id))
        self.running = False

    async def _process_next_job(self) -> bool:
        """
        Process the next available job from the queue.

        Returns:
            True if a job was processed, False if queue was empty.
        """
        async with AsyncSessionLocal() as session:
            job_repo = JobQueueRepository(session)

            # Dequeue next job
            job = await job_repo.dequeue(
                job_types=[
                    "document_extraction",
                    "deadline_calculation",
                    "deadline_reminder",
                    "report_generation",
                ]
            )

            if not job:
                return False

            self.current_job_id = job.id

            logger.info(
                "job_started",
                job_id=str(job.id),
                job_type=job.job_type,
                attempt=getattr(job, 'attempt', 1),
            )

            try:
                result = await self._execute_job(session, job.job_type, job.payload)

                await job_repo.complete(job.id, result)
                await session.commit()

                self.jobs_processed += 1

                logger.info(
                    "job_completed",
                    job_id=str(job.id),
                    job_type=job.job_type,
                    success=result.get("success", True),
                )

                return True

            except Exception as e:
                logger.error(
                    "job_failed",
                    job_id=str(job.id),
                    job_type=job.job_type,
                    error=str(e),
                    exc_info=True,
                )

                self.jobs_failed += 1
                await session.rollback()

                async with AsyncSessionLocal() as error_session:
                    error_repo = JobQueueRepository(error_session)
                    await error_repo.fail(job.id, str(e))
                    await error_session.commit()

                return True  # A job was attempted

            finally:
                self.current_job_id = None

    async def _execute_job(
        self,
        session,
        job_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a job based on its type."""
        if job_type == "document_extraction":
            return await self._handle_document_extraction(session, payload)
        elif job_type == "deadline_calculation":
            return await self._handle_deadline_calculation(session, payload)
        elif job_type == "deadline_reminder":
            return await self._handle_deadline_reminder(session, payload)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

    async def _handle_document_extraction(
        self,
        session,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle document extraction job."""
        document_id = UUID(payload["document_id"])
        transaction_id = UUID(payload["transaction_id"])
        organization_id = UUID(payload["organization_id"])

        # Create agent context
        context = AgentContext(
            execution_id=document_id,  # Use document ID as execution ID
            transaction_id=transaction_id,
            organization_id=organization_id,
            triggered_by="worker",
            triggered_at=datetime.now(timezone.utc),
        )

        # Create input
        input_data = DocumentExtractInput(
            document_id=document_id,
            document_type=payload["document_type"],
            storage_path=payload["storage_path"],
            filename=payload["filename"],
        )

        # Mark document as processing
        doc_repo = DocumentRepository(session)
        await doc_repo.mark_processing(document_id)
        await session.commit()

        # Execute extraction
        result = await self.document_extract_agent.execute(context, input_data)

        if result.success and result.output:
            # Update document with extraction results
            await doc_repo.update_extraction(
                document_id,
                extracted_data=result.output.model_dump(),
                confidence=result.confidence or 0.0,
                needs_review=result.needs_human_review,
                needs_review_reason=result.review_reason,
            )
            await session.commit()

            # If this is a purchase contract with dates, trigger deadline calculation
            if (
                payload["document_type"] == "purchase_contract"
                and result.output.effective_date
                and result.output.closing_date
            ):
                job_repo = JobQueueRepository(session)
                await job_repo.enqueue(
                    job_type="deadline_calculation",
                    payload={
                        "transaction_id": str(transaction_id),
                        "organization_id": str(organization_id),
                        "document_id": str(document_id),
                        "effective_date": str(result.output.effective_date),
                        "closing_date": str(result.output.closing_date),
                        "contingencies": [
                            c.model_dump() for c in result.output.contingencies
                        ],
                    },
                )
                await session.commit()

            return {
                "success": True,
                "confidence": result.confidence,
                "needs_review": result.needs_human_review,
            }
        else:
            # Mark as needing review due to failure
            await doc_repo.mark_failed(document_id, result.error or "Unknown error")
            await session.commit()

            return {
                "success": False,
                "error": result.error,
            }

    async def _handle_deadline_calculation(
        self,
        session,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle deadline calculation job."""
        from datetime import date

        transaction_id = UUID(payload["transaction_id"])
        organization_id = UUID(payload["organization_id"])

        context = AgentContext(
            execution_id=transaction_id,
            transaction_id=transaction_id,
            organization_id=organization_id,
            triggered_by="worker",
            triggered_at=datetime.now(timezone.utc),
        )

        input_data = DeadlineInput(
            transaction_id=transaction_id,
            effective_date=date.fromisoformat(payload["effective_date"]),
            closing_date=date.fromisoformat(payload["closing_date"]),
            contingencies=payload.get("contingencies", []),
            state="FL",
        )

        result = await self.deadline_agent.execute(context, input_data)

        if result.success and result.output:
            # Create deadline records
            deadline_repo = DeadlineRepository(session)

            for deadline in result.output.deadlines:
                await deadline_repo.create(
                    transaction_id=transaction_id,
                    deadline_type=deadline.deadline_type,
                    name=deadline.name,
                    due_date=deadline.due_date,
                    description=deadline.description,
                    source_document_id=UUID(payload["document_id"])
                    if payload.get("document_id")
                    else None,
                    reminder_days=deadline.reminder_days,
                )

            await session.commit()

            return {
                "success": True,
                "deadlines_created": len(result.output.deadlines),
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    async def _handle_deadline_reminder(
        self,
        session,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle deadline reminder job."""
        deadline_id = payload.get("deadline_id")
        days_remaining = payload.get("days_remaining")
        organization_id = payload.get("organization_id")
        transaction_id = payload.get("transaction_id")

        logger.info(
            "deadline_reminder",
            deadline_id=deadline_id,
            days_remaining=days_remaining,
        )

        try:
            # Get deadline details
            deadline_repo = DeadlineRepository(session)
            transaction_repo = TransactionRepository(session)
            user_repo = UserRepository(session)

            deadline = await deadline_repo.get_by_id(UUID(deadline_id))
            if not deadline:
                return {"success": False, "error": "Deadline not found"}

            transaction = await transaction_repo.get_by_id(UUID(transaction_id))
            if not transaction:
                return {"success": False, "error": "Transaction not found"}

            # Get users in the organization to notify
            users = await user_repo.get_by_organization(UUID(organization_id))

            # Build property address string
            property_addr = transaction.property_address
            address_str = property_addr.get("street", "Unknown property")
            if property_addr.get("city"):
                address_str += f", {property_addr['city']}"

            # Send notifications to relevant users
            notifications_sent = 0
            for user in users:
                if user.role in ["admin", "broker", "agent"]:
                    # Create context for the notification agent
                    context = AgentContext(
                        execution_id=UUID(deadline_id),
                        transaction_id=UUID(transaction_id),
                        organization_id=UUID(organization_id),
                        triggered_by="worker",
                        triggered_at=datetime.now(timezone.utc),
                    )

                    await self.notification_agent.send_deadline_reminder(
                        context=context,
                        user_id=user.id,
                        organization_id=UUID(organization_id),
                        transaction_id=UUID(transaction_id),
                        recipient_email=user.email,
                        deadline_name=deadline.name,
                        due_date=str(deadline.due_date),
                        days_remaining=days_remaining,
                        property_address=address_str,
                    )
                    notifications_sent += 1

            # Update last_reminder_sent on deadline
            await deadline_repo.update(
                deadline.id,
                last_reminder_sent=datetime.now(timezone.utc),
            )

            return {
                "success": True,
                "notification_sent": True,
                "notifications_count": notifications_sent,
            }

        except Exception as e:
            logger.error(
                "deadline_reminder_error",
                deadline_id=deadline_id,
                error=str(e),
            )
            return {"success": False, "error": str(e)}


async def main() -> None:
    """Main entry point."""
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
