"""Portal router - external party portal access endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from packages.db.session import get_db
from packages.core.services import PortalService, get_portal_service
from packages.core.services.email import get_email_service
from packages.core.exceptions import AuthenticationError, NotFoundError
from services.api.dependencies import CurrentUserDep


router = APIRouter()


# === Request/Response Models ===


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


class SendInviteRequest(BaseModel):
    """Request to send a portal invite email."""

    transaction_id: UUID
    party_email: EmailStr
    party_name: str
    party_role: str
    expires_hours: int = 72
    custom_message: str | None = None


class SendInviteResponse(BaseModel):
    """Response after sending invite."""

    success: bool
    portal_url: str
    expires_at: str
    message: str


class BulkInviteRequest(BaseModel):
    """Request to send invites to all parties on a transaction."""

    transaction_id: UUID
    exclude_roles: list[str] = []  # Roles to skip
    custom_message: str | None = None


class BulkInviteResponse(BaseModel):
    """Response after sending bulk invites."""

    total: int
    sent: int
    failed: int
    skipped: int
    results: list[dict[str, Any]]


class AcceptInviteRequest(BaseModel):
    """Request to accept an invite and optionally register."""

    token: str
    name: str | None = None
    phone: str | None = None


class AcceptInviteResponse(BaseModel):
    """Response after accepting invite."""

    success: bool
    transaction_id: str
    party_role: str
    message: str


# === Email Template ===


PORTAL_INVITE_TEMPLATE = """Dear {party_name},

You have been invited to view the transaction details for:

Property: {property_address}

As the {party_role} on this transaction, you can access:
- Transaction status and key dates
- Important deadlines
- Required documents
- Contact information for all parties

{custom_message}

Click the link below to access the portal:
{portal_url}

This link will expire on {expires_date}.

If you have any questions, please contact your transaction coordinator.

Best regards,
{sender_name}
{company_name}
"""


# === Endpoints ===


@router.post("/generate-token", response_model=GenerateTokenResponse)
async def generate_portal_token(
    request: GenerateTokenRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
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
        current_user.organization_id,
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
    expires_at = datetime.now() + timedelta(hours=request.expires_hours)

    # Build portal URL
    from packages.core.config import settings

    base_url = getattr(settings, "portal_base_url", "https://portal.airporttc.com")
    portal_url = f"{base_url}/view?token={token}"

    return GenerateTokenResponse(
        token=token,
        expires_at=expires_at.isoformat(),
        portal_url=portal_url,
    )


@router.post("/invite", response_model=SendInviteResponse)
async def send_portal_invite(
    request: SendInviteRequest,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SendInviteResponse:
    """
    Send a portal invite email to an external party.

    This generates a portal token and sends an email with the
    access link. The party can click the link to view transaction details.
    """
    portal_service = get_portal_service(db)
    email_service = get_email_service()

    # Verify user has access to this transaction
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        request.transaction_id,
        current_user.organization_id,
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
    expires_at = datetime.now() + timedelta(hours=request.expires_hours)

    # Build portal URL
    from packages.core.config import settings

    base_url = getattr(settings, "portal_base_url", "https://portal.airporttc.com")
    portal_url = f"{base_url}/view?token={token}"

    # Format property address
    prop_addr = transaction.property_address or {}
    property_address = f"{prop_addr.get('street', '')}, {prop_addr.get('city', '')}"

    # Format role for display
    role_display = request.party_role.replace("_", " ").title()

    # Prepare email
    custom_msg = request.custom_message or ""
    if custom_msg:
        custom_msg = f"\nNote from coordinator:\n{custom_msg}\n"

    email_body = PORTAL_INVITE_TEMPLATE.format(
        party_name=request.party_name,
        property_address=property_address,
        party_role=role_display,
        custom_message=custom_msg,
        portal_url=portal_url,
        expires_date=expires_at.strftime("%B %d, %Y at %I:%M %p"),
        sender_name=current_user.name or "Transaction Coordinator",
        company_name="Airport TC",
    )

    # Send email
    try:
        await email_service.send_email(
            to_email=request.party_email,
            subject=f"Portal Access: {property_address}",
            body=email_body,
        )
        success = True
        message = f"Invite sent to {request.party_email}"
    except Exception as e:
        success = False
        message = f"Failed to send invite: {str(e)}"

    return SendInviteResponse(
        success=success,
        portal_url=portal_url,
        expires_at=expires_at.isoformat(),
        message=message,
    )


@router.post("/invite-all", response_model=BulkInviteResponse)
async def send_bulk_invites(
    request: BulkInviteRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> BulkInviteResponse:
    """
    Send portal invites to all parties on a transaction.

    This is a convenience endpoint that sends invites to all parties
    who have email addresses. You can exclude certain roles.
    """
    portal_service = get_portal_service(db)
    email_service = get_email_service()

    # Verify user has access to this transaction
    from packages.core.services import TransactionService

    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        request.transaction_id,
        current_user.organization_id,
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    parties = transaction.parties or []
    results = []
    sent = 0
    failed = 0
    skipped = 0

    # Format property address
    prop_addr = transaction.property_address or {}
    property_address = f"{prop_addr.get('street', '')}, {prop_addr.get('city', '')}"

    from packages.core.config import settings
    base_url = getattr(settings, "portal_base_url", "https://portal.airporttc.com")

    for party in parties:
        role = party.get("role", "")
        email = party.get("email")
        name = party.get("name", "")

        # Skip if no email or excluded role
        if not email:
            results.append({
                "name": name,
                "role": role,
                "status": "skipped",
                "reason": "No email address",
            })
            skipped += 1
            continue

        if role in request.exclude_roles:
            results.append({
                "name": name,
                "role": role,
                "email": email,
                "status": "skipped",
                "reason": f"Role '{role}' excluded",
            })
            skipped += 1
            continue

        # Generate token
        try:
            token = portal_service.generate_portal_token(
                transaction_id=request.transaction_id,
                party_email=email,
                party_role=role,
                expires_hours=72,
            )
            expires_at = datetime.now() + timedelta(hours=72)
            portal_url = f"{base_url}/view?token={token}"

            # Format email
            role_display = role.replace("_", " ").title()
            custom_msg = request.custom_message or ""
            if custom_msg:
                custom_msg = f"\nNote from coordinator:\n{custom_msg}\n"

            email_body = PORTAL_INVITE_TEMPLATE.format(
                party_name=name or "Valued Party",
                property_address=property_address,
                party_role=role_display,
                custom_message=custom_msg,
                portal_url=portal_url,
                expires_date=expires_at.strftime("%B %d, %Y at %I:%M %p"),
                sender_name=current_user.name or "Transaction Coordinator",
                company_name="Airport TC",
            )

            await email_service.send_email(
                to_email=email,
                subject=f"Portal Access: {property_address}",
                body=email_body,
            )

            results.append({
                "name": name,
                "role": role,
                "email": email,
                "status": "sent",
                "portal_url": portal_url,
            })
            sent += 1

        except Exception as e:
            results.append({
                "name": name,
                "role": role,
                "email": email,
                "status": "failed",
                "error": str(e),
            })
            failed += 1

    return BulkInviteResponse(
        total=len(parties),
        sent=sent,
        failed=failed,
        skipped=skipped,
        results=results,
    )


@router.post("/accept-invite", response_model=AcceptInviteResponse)
async def accept_portal_invite(
    request: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> AcceptInviteResponse:
    """
    Accept a portal invite and optionally update contact info.

    This is called when an external party first accesses the portal.
    They can optionally provide their name and phone if not already on file.
    """
    portal_service = get_portal_service(db)

    try:
        payload = portal_service.validate_portal_token(request.token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    transaction_id = payload.get("tx")
    party_email = payload.get("email")
    party_role = payload.get("role")

    # Update party info if provided
    if request.name or request.phone:
        from packages.db.repositories.transaction import TransactionRepository
        from sqlalchemy.orm.attributes import flag_modified

        tx_repo = TransactionRepository(db)
        transaction = await tx_repo.get_by_id(UUID(transaction_id))

        if transaction and transaction.parties:
            parties = list(transaction.parties)
            for party in parties:
                if party.get("email") == party_email:
                    if request.name:
                        party["name"] = request.name
                    if request.phone:
                        party["phone"] = request.phone
                    break

            # Save updated parties
            await tx_repo.update(UUID(transaction_id), parties=parties)

    return AcceptInviteResponse(
        success=True,
        transaction_id=transaction_id,
        party_role=party_role,
        message="Invite accepted successfully",
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
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
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
        current_user.organization_id,
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
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
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
        current_user.organization_id,
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await portal_service.revoke_token(transaction_id, party_email)

    return {
        "status": "revoked",
        "transaction_id": str(transaction_id),
        "party_email": party_email,
    }
