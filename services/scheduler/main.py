"""Deadline reminder scheduler.

This service runs periodically to:
1. Update deadline statuses based on current date
2. Enqueue reminder jobs for deadlines that need notifications
3. Check for overdue deadlines and send alerts

Can be run as a separate process or integrated into the worker with asyncio.
"""

import asyncio
import signal
from datetime import date, datetime, timedelta
from typing import Any

import structlog

from packages.core.config import settings
from packages.core.services.deadline import DeadlineService
from packages.core.services.audit import AuditService, AuditAction
from packages.db.session import AsyncSessionLocal
from packages.db.repositories.job_queue import JobQueueRepository
from packages.db.repositories.deadline import DeadlineRepository


logger = structlog.get_logger()


class DeadlineScheduler:
    """
    Scheduler for deadline-related background tasks.

    Features:
    - Runs at configurable intervals (default: every hour)
    - Updates deadline statuses
    - Enqueues reminder notifications
    - Detects overdue deadlines
    - Graceful shutdown support
    """

    def __init__(
        self,
        check_interval_seconds: int = 3600,  # 1 hour default
        reminder_check_interval_seconds: int = 300,  # 5 minutes for reminders
    ) -> None:
        self.check_interval = check_interval_seconds
        self.reminder_interval = reminder_check_interval_seconds
        self.running = False
        self._last_status_update = datetime.min
        self._last_reminder_check = datetime.min

    async def start(self) -> None:
        """Start the scheduler loop."""
        self.running = True
        logger.info(
            "scheduler_started",
            check_interval=self.check_interval,
            reminder_interval=self.reminder_interval,
        )

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        # Run initial check immediately
        await self._run_checks()

        while self.running:
            try:
                await asyncio.sleep(min(self.reminder_interval, 60))

                now = datetime.utcnow()

                # Check if it's time for status updates (hourly)
                if (now - self._last_status_update).total_seconds() >= self.check_interval:
                    await self._update_deadline_statuses()
                    self._last_status_update = now

                # Check for reminders more frequently
                if (now - self._last_reminder_check).total_seconds() >= self.reminder_interval:
                    await self._enqueue_reminders()
                    self._last_reminder_check = now

            except Exception as e:
                logger.error("scheduler_error", error=str(e), exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying

        logger.info("scheduler_stopped")

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("scheduler_shutdown_requested")
        self.running = False

    async def _run_checks(self) -> None:
        """Run all checks immediately."""
        await self._update_deadline_statuses()
        await self._enqueue_reminders()
        self._last_status_update = datetime.utcnow()
        self._last_reminder_check = datetime.utcnow()

    async def _update_deadline_statuses(self) -> None:
        """Update status of all deadlines based on current date."""
        logger.info("updating_deadline_statuses")

        try:
            async with AsyncSessionLocal() as session:
                deadline_service = DeadlineService(session)
                updated_count = await deadline_service.update_all_statuses()
                await session.commit()

                logger.info(
                    "deadline_statuses_updated",
                    updated_count=updated_count,
                )
        except Exception as e:
            logger.error("status_update_error", error=str(e), exc_info=True)

    async def _enqueue_reminders(self) -> None:
        """Enqueue reminder jobs for deadlines that need notifications."""
        logger.debug("checking_for_reminder_deadlines")

        try:
            async with AsyncSessionLocal() as session:
                deadline_service = DeadlineService(session)
                job_repo = JobQueueRepository(session)

                # Get deadlines needing reminders
                reminders = await deadline_service.get_reminders_due()

                enqueued_count = 0
                for reminder in reminders:
                    # Check if we already have a pending reminder job for this deadline
                    existing = await job_repo.get_pending_by_payload_key(
                        job_type="deadline_reminder",
                        key="deadline_id",
                        value=reminder["deadline_id"],
                    )

                    if not existing:
                        await job_repo.enqueue(
                            job_type="deadline_reminder",
                            payload={
                                "deadline_id": reminder["deadline_id"],
                                "deadline_name": reminder["deadline_name"],
                                "due_date": reminder["due_date"],
                                "days_remaining": reminder["days_remaining"],
                                "transaction_id": reminder["transaction_id"],
                                "organization_id": reminder["organization_id"],
                                "property_address": reminder["property_address"],
                            },
                            priority=1 if reminder["days_remaining"] <= 1 else 0,
                        )
                        enqueued_count += 1

                await session.commit()

                if enqueued_count > 0:
                    logger.info(
                        "reminders_enqueued",
                        count=enqueued_count,
                    )

        except Exception as e:
            logger.error("reminder_enqueue_error", error=str(e), exc_info=True)

    async def check_overdue_deadlines(self) -> list[dict[str, Any]]:
        """
        Check for overdue deadlines and return details.

        Called daily to generate overdue deadline reports.
        """
        overdue = []

        async with AsyncSessionLocal() as session:
            deadline_repo = DeadlineRepository(session)

            # Get all overdue deadlines
            deadlines = await deadline_repo.get_all_overdue()

            for deadline in deadlines:
                days_overdue = (date.today() - deadline.due_date).days
                overdue.append({
                    "deadline_id": str(deadline.id),
                    "name": deadline.name,
                    "due_date": str(deadline.due_date),
                    "days_overdue": days_overdue,
                    "transaction_id": str(deadline.transaction_id),
                    "deadline_type": deadline.deadline_type,
                })

        return overdue


class DailyDigestScheduler:
    """
    Scheduler for daily digest emails.

    Runs once per day at a configurable time to send
    summary emails to users.
    """

    def __init__(self, run_hour: int = 8) -> None:
        """
        Initialize the daily digest scheduler.

        Args:
            run_hour: Hour of day (0-23) to run the digest (default 8 AM)
        """
        self.run_hour = run_hour
        self.running = False
        self._last_run_date: date | None = None

    async def start(self) -> None:
        """Start the daily digest scheduler."""
        self.running = True
        logger.info("daily_digest_scheduler_started", run_hour=self.run_hour)

        while self.running:
            try:
                now = datetime.utcnow()
                today = now.date()

                # Check if we should run today
                if (
                    now.hour >= self.run_hour
                    and self._last_run_date != today
                ):
                    await self._send_daily_digests()
                    self._last_run_date = today

                # Sleep until next check (every 15 minutes)
                await asyncio.sleep(900)

            except Exception as e:
                logger.error("daily_digest_error", error=str(e), exc_info=True)
                await asyncio.sleep(300)

        logger.info("daily_digest_scheduler_stopped")

    async def _send_daily_digests(self) -> None:
        """Generate and enqueue daily digest emails for all organizations."""
        logger.info("generating_daily_digests")

        try:
            async with AsyncSessionLocal() as session:
                job_repo = JobQueueRepository(session)

                # Enqueue a digest job (the worker will handle getting orgs and users)
                await job_repo.enqueue(
                    job_type="daily_digest",
                    payload={
                        "date": str(date.today()),
                        "triggered_at": datetime.utcnow().isoformat(),
                    },
                )
                await session.commit()

                logger.info("daily_digest_enqueued")

        except Exception as e:
            logger.error("daily_digest_enqueue_error", error=str(e), exc_info=True)


async def run_all_schedulers() -> None:
    """Run all schedulers concurrently."""
    deadline_scheduler = DeadlineScheduler(
        check_interval_seconds=3600,  # Update statuses hourly
        reminder_check_interval_seconds=300,  # Check reminders every 5 min
    )
    daily_digest_scheduler = DailyDigestScheduler(run_hour=8)

    # Run both schedulers concurrently
    await asyncio.gather(
        deadline_scheduler.start(),
        daily_digest_scheduler.start(),
    )


async def main() -> None:
    """Main entry point for the scheduler service."""
    await run_all_schedulers()


if __name__ == "__main__":
    asyncio.run(main())
