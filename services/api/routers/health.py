"""Health check endpoints."""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from packages.core.config import settings
from packages.db.session import AsyncSessionLocal

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response."""

    status: str
    timestamp: str
    version: str = "0.1.0"
    environment: str


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    message: str | None = None


class ReadinessStatus(BaseModel):
    """Readiness status with dependency details."""

    status: str
    timestamp: str
    dependencies: list[DependencyStatus]


async def check_database() -> DependencyStatus:
    """Check database connectivity."""
    start = datetime.now()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="database",
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="database",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=str(e)[:200],
        )


async def check_redis() -> DependencyStatus:
    """Check Redis connectivity."""
    start = datetime.now()
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="redis",
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="redis",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=str(e)[:200],
        )


async def check_storage() -> DependencyStatus:
    """Check S3/storage connectivity."""
    start = datetime.now()
    try:
        from packages.core.services.storage import get_storage_service

        storage = get_storage_service()
        # Just verify the service can be instantiated
        # A full check would list buckets or check permissions
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="storage",
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="storage",
            status="degraded",
            latency_ms=round(latency, 2),
            message=str(e)[:200],
        )


async def check_anthropic() -> DependencyStatus:
    """Check Anthropic API key is configured."""
    start = datetime.now()
    try:
        if not settings.anthropic_api_key:
            return DependencyStatus(
                name="anthropic",
                status="unhealthy",
                message="API key not configured",
            )

        # Just verify key format (starts with sk-)
        if not settings.anthropic_api_key.startswith("sk-"):
            return DependencyStatus(
                name="anthropic",
                status="degraded",
                message="API key format may be invalid",
            )

        latency = (datetime.now() - start).total_seconds() * 1000
        return DependencyStatus(
            name="anthropic",
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyStatus(
            name="anthropic",
            status="unhealthy",
            message=str(e)[:200],
        )


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint.

    Returns 200 if the service is running.
    Does not check dependencies - use /ready for that.
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        environment=settings.environment,
    )


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness check - verifies all dependencies are available.

    Returns 200 if all dependencies are healthy.
    Returns 503 if any critical dependency is unhealthy.
    """
    # Check all dependencies in parallel
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_storage(),
        check_anthropic(),
        return_exceptions=True,
    )

    dependencies = []
    for result in results:
        if isinstance(result, Exception):
            dependencies.append(
                DependencyStatus(
                    name="unknown",
                    status="unhealthy",
                    message=str(result)[:200],
                )
            )
        else:
            dependencies.append(result)

    # Determine overall status
    # Critical dependencies: database
    # Non-critical: redis, storage, anthropic (can operate in degraded mode)
    critical_unhealthy = any(
        d.status == "unhealthy" and d.name in ("database",)
        for d in dependencies
    )

    any_unhealthy = any(d.status == "unhealthy" for d in dependencies)
    any_degraded = any(d.status == "degraded" for d in dependencies)

    if critical_unhealthy:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any_unhealthy or any_degraded:
        overall_status = "degraded"
        http_status = status.HTTP_200_OK
    else:
        overall_status = "ready"
        http_status = status.HTTP_200_OK

    response = ReadinessStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
    )

    return JSONResponse(
        status_code=http_status,
        content=response.model_dump(),
    )


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """
    Liveness check for Kubernetes.

    Returns 200 if the process is alive.
    This should always succeed unless the process is hung.
    """
    return {"status": "alive"}


@router.get("/info")
async def info() -> dict[str, Any]:
    """
    Service information endpoint.

    Returns version, environment, and configuration info.
    """
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "document_extraction": True,
            "deadline_calculation": True,
            "checklist_management": True,
            "communication_drafting": True,
            "notifications": True,
        },
        "compliance": {
            "state": "FL",
            "human_review_threshold": settings.require_human_review_below,
            "extraction_confidence_threshold": settings.extraction_confidence_threshold,
        },
    }
