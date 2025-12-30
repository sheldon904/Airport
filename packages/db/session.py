"""Database session management with proper error handling and logging."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import structlog

from packages.core.config import settings

logger = structlog.get_logger()

# Create async engine with appropriate options
engine_kwargs = {
    "echo": settings.debug,
}

# Only add connection pool options for PostgreSQL (not SQLite)
if "postgresql" in settings.database_url:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True  # Check connection health before use

engine = create_async_engine(settings.database_url, **engine_kwargs)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.

    Provides proper error handling and logging for database operations.
    Uses autocommit=False pattern - caller decides when to commit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Only commit if there are pending changes (not for read-only operations)
            if session.new or session.dirty or session.deleted:
                await session.commit()
        except IntegrityError as e:
            logger.warning(
                "database_integrity_error",
                error=str(e),
                constraint=getattr(e.orig, 'constraint_name', None) if hasattr(e, 'orig') else None,
            )
            await session.rollback()
            raise
        except OperationalError as e:
            logger.error(
                "database_operational_error",
                error=str(e),
                connection_invalidated=getattr(e, 'connection_invalidated', False),
            )
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(
                "database_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            await session.rollback()
            raise
        except Exception as e:
            # Non-SQLAlchemy exceptions - still need to rollback
            logger.error(
                "database_session_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting database sessions outside FastAPI dependencies.

    Use this for WebSocket handlers or background tasks where dependency
    injection is not available.

    Provides proper error handling and logging for database operations.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Only commit if there are pending changes
            if session.new or session.dirty or session.deleted:
                await session.commit()
        except IntegrityError as e:
            logger.warning(
                "database_integrity_error",
                error=str(e),
                constraint=getattr(e.orig, 'constraint_name', None) if hasattr(e, 'orig') else None,
            )
            await session.rollback()
            raise
        except OperationalError as e:
            logger.error(
                "database_operational_error",
                error=str(e),
                connection_invalidated=getattr(e, 'connection_invalidated', False),
            )
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(
                "database_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            await session.rollback()
            raise
        except Exception as e:
            logger.error(
                "database_session_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            await session.rollback()
            raise
        finally:
            await session.close()
