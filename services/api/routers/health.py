"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check - verifies dependencies are available."""
    # TODO: Check database, redis, etc.
    return {"status": "ready"}
