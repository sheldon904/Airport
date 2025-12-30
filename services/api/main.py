"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from packages.core.config import settings
from packages.core.exceptions import register_exception_handlers
from packages.core.rate_limit import RateLimitMiddleware
from services.api.routers import auth, transactions, documents, deadlines, health, reports, audit, forms, portal, contacts

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("api_starting", app_name=settings.app_name, environment=settings.environment)
    yield
    # Shutdown
    logger.info("api_shutting_down", app_name=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered transaction coordination platform for real estate",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register exception handlers
register_exception_handlers(app)

# Rate limiting middleware (must be before CORS)
app.add_middleware(RateLimitMiddleware)

# CORS middleware - configured via environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(deadlines.router, prefix="/api/v1/deadlines", tags=["Deadlines"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(forms.router, prefix="/api/v1/forms", tags=["Forms"])
app.include_router(portal.router, prefix="/api/v1/portal", tags=["Portal"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
