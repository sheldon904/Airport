"""Background worker main entry point."""

import asyncio
import signal
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from packages.core.config import settings
from packages.db.session import AsyncSessionLocal
from packages.db.repositories.job_queue import JobQueueRepository
from packages.db.repositories.document import DocumentRepository
from packages.db.repositories.deadline import DeadlineRepository
from services.agents.document_extract.agent import (
    DocumentExtractAgent,
    DocumentExtractInput,
)
from services.agents.deadline.agent import DeadlineAgent, DeadlineInput
from services.agents.base import AgentContext

logger = structlog.get_logger()


class Worker:
    """
    Background worker for processing agent jobs.

    Polls the job queue and executes agents based on job type.
    Supports graceful shutdown and job retry logic.
    """

    def __init__(self) -> None:
        self.running = False
        self.current_job_id: UUID | None = None

        # Initialize agents
        self.document_extract_agent = DocumentExtractAgent()
        self.deadline_agent = DeadlineAgent()

    async def start(self) -> None:
        """Start the worker loop."""
        self.running = True
        logger.info("worker_started")

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        while self.running:
            try:
                await self._process_next_job()
            except Exception as e:
                logger.error("worker_error", error=str(e))
                await asyncio.sleep(5)  # Back off on errors

        logger.info("worker_stopped")

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("shutdown_requested")
        self.running = False

    async def _process_next_job(self) -> None:
        """Process the next available job from the queue."""
        async with AsyncSessionLocal() as session:
            job_repo = JobQueueRepository(session)

            # Dequeue next job
            job = await job_repo.dequeue(
                job_types=[
                    "document_extraction",
                    "deadline_calculation",
                    "deadline_reminder",
                ]
            )

            if not job:
                # No jobs available, wait before polling again
                await asyncio.sleep(1)
                return

            self.current_job_id = job.id

            logger.info(
                "job_started",
                job_id=str(job.id),
                job_type=job.job_type,
            )

            try:
                result = await self._execute_job(session, job.job_type, job.payload)

                await job_repo.complete(job.id, result)
                await session.commit()

                logger.info(
                    "job_completed",
                    job_id=str(job.id),
                    job_type=job.job_type,
                )

            except Exception as e:
                logger.error(
                    "job_failed",
                    job_id=str(job.id),
                    job_type=job.job_type,
                    error=str(e),
                )

                await session.rollback()

                async with AsyncSessionLocal() as error_session:
                    error_repo = JobQueueRepository(error_session)
                    await error_repo.fail(job.id, str(e))
                    await error_session.commit()

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
            triggered_at=datetime.utcnow(),
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
            triggered_at=datetime.utcnow(),
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
        # TODO: Implement email/notification sending
        logger.info(
            "deadline_reminder",
            deadline_id=payload.get("deadline_id"),
            days_remaining=payload.get("days_remaining"),
        )

        return {"success": True, "notification_sent": False}


async def main() -> None:
    """Main entry point."""
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
