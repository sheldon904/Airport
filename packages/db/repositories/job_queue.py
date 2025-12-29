"""Job queue repository for background processing."""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import and_, select, update

from packages.db.models import Base
from packages.db.repositories.base import BaseRepository


# Define JobQueueModel here since it wasn't in the original models
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class JobQueueModel(Base):
    """Background job queue entry."""

    __tablename__ = "job_queue"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JobQueueRepository(BaseRepository[JobQueueModel]):
    """Repository for job queue operations."""

    model = JobQueueModel

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        priority: int = 0,
        scheduled_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> JobQueueModel:
        """Add a new job to the queue."""
        return await self.create(
            id=uuid4(),
            job_type=job_type,
            payload=payload,
            priority=priority,
            scheduled_at=scheduled_at or datetime.utcnow(),
            max_attempts=max_attempts,
        )

    async def dequeue(
        self,
        job_types: list[str] | None = None,
    ) -> JobQueueModel | None:
        """
        Get the next available job and mark it as processing.

        Uses SELECT FOR UPDATE SKIP LOCKED for safe concurrent access.
        """
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.status == "pending",
                    self.model.scheduled_at <= datetime.utcnow(),
                    self.model.attempts < self.model.max_attempts,
                )
            )
        )

        if job_types:
            query = query.where(self.model.job_type.in_(job_types))

        query = query.order_by(
            self.model.priority.desc(),
            self.model.scheduled_at,
        ).limit(1).with_for_update(skip_locked=True)

        result = await self.session.execute(query)
        job = result.scalar_one_or_none()

        if job:
            await self.session.execute(
                update(self.model)
                .where(self.model.id == job.id)
                .values(
                    status="processing",
                    started_at=datetime.utcnow(),
                    attempts=job.attempts + 1,
                )
            )
            await self.session.flush()
            await self.session.refresh(job)

        return job

    async def complete(
        self,
        job_id: UUID,
        result: dict[str, Any] | None = None,
    ) -> JobQueueModel | None:
        """Mark a job as completed."""
        return await self.update(
            job_id,
            status="completed",
            completed_at=datetime.utcnow(),
            result=result,
        )

    async def fail(
        self,
        job_id: UUID,
        error: str,
    ) -> JobQueueModel | None:
        """Mark a job as failed."""
        job = await self.get_by_id(job_id)
        if not job:
            return None

        # Check if we should retry
        if job.attempts < job.max_attempts:
            status = "pending"  # Will be retried
        else:
            status = "failed"  # Max attempts reached

        return await self.update(
            job_id,
            status=status,
            error=error,
            completed_at=datetime.utcnow() if status == "failed" else None,
        )

    async def get_pending_count(self, job_type: str | None = None) -> int:
        """Get count of pending jobs."""
        filters = {"status": "pending"}
        if job_type:
            filters["job_type"] = job_type
        return await self.count(**filters)

    async def get_pending_by_payload_key(
        self,
        job_type: str,
        key: str,
        value: str,
    ) -> JobQueueModel | None:
        """Get a pending job with a specific payload value."""
        from sqlalchemy.dialects.postgresql import JSONB

        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.job_type == job_type,
                    self.model.status == "pending",
                    self.model.payload[key].astext == value,
                )
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_failed_jobs(
        self,
        job_type: str | None = None,
        limit: int = 100,
    ) -> Sequence[JobQueueModel]:
        """Get failed jobs for inspection."""
        query = select(self.model).where(self.model.status == "failed")

        if job_type:
            query = query.where(self.model.job_type == job_type)

        query = query.order_by(self.model.completed_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def retry_failed(self, job_id: UUID) -> JobQueueModel | None:
        """Reset a failed job for retry."""
        return await self.update(
            job_id,
            status="pending",
            error=None,
            attempts=0,
            scheduled_at=datetime.utcnow(),
        )

    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """Delete completed/failed jobs older than N days."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.status.in_(["completed", "failed"]),
                    self.model.completed_at < cutoff,
                )
            )
        )

        jobs = result.scalars().all()
        count = len(jobs)

        for job in jobs:
            await self.delete(job.id)

        return count
