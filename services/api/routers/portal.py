"""Portal router - external party portal access endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from packages.db.session import get_db
from packages.core.services import PortalService, get_portal_service
from packages.core.exceptions import AuthenticationError, NotFoundError
from services.api.routers.auth import get_current_user


router = APIRouter()


class GenerateTokenRequest(BaseModel):
    """Request to generate a portal access token."""

    transaction_id: UUID
    party_email: EmailStr
    party_role: str
    expires_hours: int = 72


class GenerateTokenResponse(BaseModel):
    """Response with portal access token."""

    token: str
    expires_at: str
    portal_url: str


class PortalDataResponse(BaseModel):
    """Response with portal data for external party."""

    transaction_id: str
    property_address: dict[str, Any]
    status: str
    status_label: str
    closing_date: str | None
    effective_date: str | None
    your_role: str
    purchase_price: float | None = None
    parties: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    deadlines: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    last_updated: str | None


@router.post("/generate-token", response_model=GenerateTokenResponse)
async def generate_portal_token(
    request: GenerateTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> GenerateTokenResponse:
    """
    Generate a portal access token for an external party.

    This creates a time-limited token that allows external parties
    (sellers, buyer agents, title companies, etc.) to view transaction
    status and key dates without full system access.
    """
    portal_service = get_portal_service(db)

    # Verify user has access to this transaction
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        request.transaction_id,
        UUID(current_user["organization_id"]),
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Generate token
    token = portal_service.generate_portal_token(
        transaction_id=request.transaction_id,
        party_email=request.party_email,
        party_role=request.party_role,
        expires_hours=request.expires_hours,
    )

    # Calculate expiry
    from datetime import datetime, timedelta

    expires_at = datetime.now() + timedelta(hours=request.expires_hours)

    # Build portal URL (would be configured in settings)
    from packages.core.config import settings

    base_url = getattr(settings, "portal_base_url", "https://portal.airporttc.com")
    portal_url = f"{base_url}/view?token={token}"

    return GenerateTokenResponse(
        token=token,
        expires_at=expires_at.isoformat(),
        portal_url=portal_url,
    )


@router.get("/view", response_model=PortalDataResponse)
async def get_portal_data(
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> PortalDataResponse:
    """
    Get portal data for an external party.

    This endpoint is used by external parties to view transaction
    information. Authentication is via the portal token, not standard auth.
    """
    portal_service = get_portal_service(db)

    try:
        data = await portal_service.get_portal_data(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return PortalDataResponse(**data)


@router.post("/validate-token")
async def validate_portal_token(
    token: str = Query(..., description="Portal access token"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Validate a portal token and return party info.

    Useful for checking if a token is still valid before redirecting
    to the full portal view.
    """
    portal_service = get_portal_service(db)

    try:
        payload = portal_service.validate_portal_token(token)
        return {
            "valid": True,
            "transaction_id": payload["tx"],
            "party_email": payload["email"],
            "party_role": payload["role"],
            "expires_at": payload.get("exp"),
        }
    except AuthenticationError as e:
        return {
            "valid": False,
            "error": str(e),
        }


@router.get("/tokens/{transaction_id}")
async def list_portal_tokens(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List active portal tokens for a transaction.

    Returns information about who has been given portal access.
    """
    portal_service = get_portal_service(db)

    # Verify user has access to this transaction
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        UUID(current_user["organization_id"]),
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tokens = await portal_service.list_active_tokens(transaction_id)

    return {
        "transaction_id": str(transaction_id),
        "tokens": tokens,
        "total": len(tokens),
    }


@router.delete("/tokens/{transaction_id}/{party_email}")
async def revoke_portal_token(
    transaction_id: UUID,
    party_email: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Revoke a portal token for a specific party.

    This invalidates any existing portal access for the given email.
    """
    portal_service = get_portal_service(db)

    # Verify user has access to this transaction
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        UUID(current_user["organization_id"]),
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await portal_service.revoke_token(transaction_id, party_email)

    return {
        "status": "revoked",
        "transaction_id": str(transaction_id),
        "party_email": party_email,
    }
