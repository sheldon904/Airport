"""Base repository with generic CRUD operations."""

import logging
from functools import lru_cache
from typing import Any, Generic, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import func, select, update, delete, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from packages.db.models import Base

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)


# Disallowed attribute prefixes for security (REM-002)
_DISALLOWED_PREFIXES = ("__", "_sa_")
_DISALLOWED_ATTRS = frozenset({
    "metadata", "registry", "query", "session", "c", "columns",
})


class BaseRepository(Generic[ModelT]):
    """
    Base repository providing generic CRUD operations.

    All repositories inherit from this class and can add
    entity-specific query methods.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        # Cache allowed columns for this model
        self._allowed_columns: frozenset[str] | None = None

    def _get_allowed_columns(self) -> frozenset[str]:
        """
        Get set of allowed column names for this model.

        Cached for performance. Only includes actual SQLAlchemy columns,
        not internal attributes or methods.

        REM-002: Prevents attribute traversal attacks via user input.
        """
        if self._allowed_columns is None:
            try:
                mapper = inspect(self.model)
                # Only allow actual mapped column attributes
                columns = {col.key for col in mapper.columns}
                # Also allow relationship names for potential joins
                relationships = {rel.key for rel in mapper.relationships}
                self._allowed_columns = frozenset(columns | relationships)
            except Exception:
                # Fallback: use empty set if inspection fails
                self._allowed_columns = frozenset()
        return self._allowed_columns

    def _is_safe_column(self, name: str) -> bool:
        """
        Check if a column name is safe to use with getattr.

        REM-002: Validates that name is an actual column, not an internal
        attribute that could be exploited.
        """
        # Check for disallowed prefixes
        if any(name.startswith(prefix) for prefix in _DISALLOWED_PREFIXES):
            logger.warning(
                "repository_disallowed_column_prefix",
                extra={"column": name, "model": self.model.__name__}
            )
            return False

        # Check for explicitly disallowed attributes
        if name in _DISALLOWED_ATTRS:
            logger.warning(
                "repository_disallowed_column_name",
                extra={"column": name, "model": self.model.__name__}
            )
            return False

        # Check if it's in the allowed columns list
        allowed = self._get_allowed_columns()
        if name not in allowed:
            logger.warning(
                "repository_unknown_column",
                extra={
                    "column": name,
                    "model": self.model.__name__,
                    "allowed_count": len(allowed),
                }
            )
            return False

        return True

    def _get_column(self, name: str) -> InstrumentedAttribute | None:
        """
        Safely get a column attribute by name.

        Returns None if the column is not allowed or doesn't exist.
        """
        if not self._is_safe_column(name):
            return None
        return getattr(self.model, name, None)

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Get a single entity by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        descending: bool = False,
    ) -> Sequence[ModelT]:
        """Get all entities with pagination."""
        query = select(self.model)

        # REM-002: Use safe column getter to prevent attribute traversal
        if order_by:
            order_col = self._get_column(order_by)
            if order_col is not None:
                query = query.order_by(order_col.desc() if descending else order_col)

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        """Count entities matching filters."""
        query = select(func.count(self.model.id))

        # REM-002: Use safe column getter to prevent attribute traversal
        for key, value in filters.items():
            col = self._get_column(key)
            if col is not None:
                query = query.where(col == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: UUID, **kwargs: Any) -> ModelT | None:
        """Update an entity by ID."""
        # Remove None values to avoid overwriting with null
        update_data = {k: v for k, v in kwargs.items() if v is not None}

        if not update_data:
            return await self.get_by_id(id)

        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """Check if an entity exists."""
        result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0

    async def find_by(self, **filters: Any) -> Sequence[ModelT]:
        """Find entities matching filters."""
        query = select(self.model)

        # REM-002: Use safe column getter to prevent attribute traversal
        for key, value in filters.items():
            col = self._get_column(key)
            if col is not None:
                query = query.where(col == value)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_by(self, **filters: Any) -> ModelT | None:
        """Find a single entity matching filters."""
        query = select(self.model)

        # REM-002: Use safe column getter to prevent attribute traversal
        for key, value in filters.items():
            col = self._get_column(key)
            if col is not None:
                query = query.where(col == value)

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()
