"""FastAPI dependencies for request handling."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.session import get_db
from packages.core.services.auth import AuthService
from packages.core.services.transaction import TransactionService
from packages.core.services.document import DocumentService
from packages.core.services.deadline import DeadlineService
from packages.core.services.storage import get_storage_service, StorageService
from packages.db.models import UserModel


# Security scheme
security = HTTPBearer()


class CurrentUser(BaseModel):
    """Current authenticated user context."""

    id: UUID
    organization_id: UUID
    email: str
    role: str
    full_name: str

    @classmethod
    def from_model(cls, user: UserModel) -> "CurrentUser":
        return cls(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role,
            full_name=user.full_name,
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser:
    """
    Extract and validate current user from JWT token.

    Raises 401 if token is invalid or user not found.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser.from_model(user)


async def get_current_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Require admin role for endpoint access."""
    if current_user.role not in ["admin", "broker"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Service dependencies
async def get_transaction_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionService:
    """Get transaction service instance."""
    return TransactionService(db)


async def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentService:
    """Get document service instance."""
    return DocumentService(db)


async def get_deadline_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeadlineService:
    """Get deadline service instance."""
    return DeadlineService(db)


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


def get_storage() -> StorageService:
    """Get storage service instance."""
    return get_storage_service()


# Type aliases for cleaner endpoint signatures
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
AdminUserDep = Annotated[CurrentUser, Depends(get_current_admin)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
DeadlineServiceDep = Annotated[DeadlineService, Depends(get_deadline_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
StorageDep = Annotated[StorageService, Depends(get_storage)]
