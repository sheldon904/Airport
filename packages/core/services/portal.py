"""Portal service - external party access to transaction data."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import settings
from packages.core.exceptions import AuthenticationError, NotFoundError
from packages.core.services.privacy import PrivacyService, get_privacy_service
from packages.db.models import TransactionModel, DocumentModel, DeadlineModel


# Portal token expiration (30 days)
PORTAL_TOKEN_EXPIRY_DAYS = 30

# Party roles that can have portal access
PORTAL_ELIGIBLE_ROLES = [
    "buyer",
    "seller",
    "buyer_agent",
    "seller_agent",
    "lender",
    "title_company",
]


class PortalService:
    """
    Service for managing external party portal access.

    Handles:
    - Generating secure portal access tokens
    - Validating portal tokens
    - Providing filtered/redacted transaction data for external parties
    - Tracking portal access
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.privacy_service = get_privacy_service(session)

    def generate_portal_token(
        self,
        transaction_id: UUID,
        party_email: str,
        party_role: str,
        expires_in_days: int | None = None,
        expires_hours: int | None = None,
    ) -> str:
        """
        Generate a secure portal access token for an external party.

        Args:
            transaction_id: Transaction to grant access to
            party_email: Email of the party
            party_role: Role of the party (buyer, seller, etc.)
            expires_in_days: Token expiration in days (default: PORTAL_TOKEN_EXPIRY_DAYS)
            expires_hours: Token expiration in hours (overrides expires_in_days)

        Returns:
            JWT token string
        """
        if party_role not in PORTAL_ELIGIBLE_ROLES:
            raise ValueError(f"Role '{party_role}' is not eligible for portal access")

        # Calculate expiration
        if expires_hours is not None:
            expiry = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        else:
            days = expires_in_days if expires_in_days is not None else PORTAL_TOKEN_EXPIRY_DAYS
            expiry = datetime.now(timezone.utc) + timedelta(days=days)

        payload = {
            "tx": str(transaction_id),
            "email": party_email,
            "role": party_role,
            "type": "portal",
            "exp": expiry,
            "iat": datetime.now(timezone.utc),
        }

        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    def validate_portal_token(self, token: str) -> dict[str, Any]:
        """
        Validate a portal access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=["HS256"],
            )

            if payload.get("type") != "portal":
                raise AuthenticationError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Portal access token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid portal token: {str(e)}")

    async def get_portal_data(
        self,
        token: str,
    ) -> dict[str, Any]:
        """
        Get transaction data for portal display.

        Data is filtered and redacted based on the party's role.

        Args:
            token: Portal access token

        Returns:
            Filtered transaction data suitable for external party view
        """
        # Validate token
        payload = self.validate_portal_token(token)

        transaction_id = UUID(payload["tx"])
        party_email = payload["email"]
        party_role = payload["role"]

        # Get transaction
        tx_stmt = select(TransactionModel).where(
            TransactionModel.id == transaction_id
        )
        tx_result = await self.session.execute(tx_stmt)
        transaction = tx_result.scalar_one_or_none()

        if not transaction:
            raise NotFoundError("Transaction not found")

        # Check if transaction is deleted
        if transaction.deleted_at:
            raise NotFoundError("Transaction not found")

        # Build portal data based on role
        return await self._build_portal_data(transaction, party_role, party_email)

    async def _build_portal_data(
        self,
        transaction: TransactionModel,
        party_role: str,
        party_email: str,
    ) -> dict[str, Any]:
        """Build filtered portal data for a party."""
        # Basic transaction info (always visible)
        portal_data = {
            "transaction_id": str(transaction.id),
            "property_address": {
                "street": transaction.property_address.get("street", ""),
                "city": transaction.property_address.get("city", ""),
                "state": transaction.property_address.get("state", "FL"),
                "zip_code": transaction.property_address.get("zip_code", ""),
            },
            "status": transaction.status,
            "status_label": self._get_status_label(transaction.status),
            "closing_date": str(transaction.closing_date) if transaction.closing_date else None,
            "effective_date": str(transaction.effective_date) if transaction.effective_date else None,
            "your_role": party_role,
        }

        # Add purchase price (visible to most parties)
        if party_role in ["buyer", "seller", "buyer_agent", "seller_agent", "lender", "title_company"]:
            portal_data["purchase_price"] = float(transaction.purchase_price) if transaction.purchase_price else None

        # Add parties (filtered based on role)
        portal_data["parties"] = self._filter_parties(transaction.parties or [], party_role)

        # Add timeline/milestones
        portal_data["timeline"] = await self._get_timeline(transaction)

        # Add deadlines (filtered)
        portal_data["deadlines"] = await self._get_deadlines(transaction.id, party_role)

        # Add documents (filtered and redacted)
        portal_data["documents"] = await self._get_documents(transaction.id, party_role)

        # Add last updated
        portal_data["last_updated"] = transaction.updated_at.isoformat() if transaction.updated_at else None

        return portal_data

    def _get_status_label(self, status: str) -> str:
        """Get human-readable status label."""
        labels = {
            "draft": "Draft",
            "pending": "Pending Review",
            "active": "Under Contract",
            "pending_close": "Preparing to Close",
            "closed": "Closed",
            "cancelled": "Cancelled",
            "on_hold": "On Hold",
        }
        return labels.get(status, status.replace("_", " ").title())

    def _filter_parties(self, parties: list[dict], viewer_role: str) -> list[dict]:
        """Filter party information based on viewer's role."""
        filtered = []

        for party in parties:
            role = party.get("role", "")

            # Create filtered party info
            filtered_party = {
                "role": role,
                "role_label": role.replace("_", " ").title(),
            }

            # Principals (buyer/seller) see agent names/contact
            # Agents see client names but limited contact info
            # Title/lender see basic info
            if viewer_role in ["buyer", "seller", "buyer_agent", "seller_agent"]:
                filtered_party["name"] = party.get("name")
                if role not in ["buyer", "seller"]:  # Don't expose principal contact to other parties
                    filtered_party["company"] = party.get("company")
                    filtered_party["email"] = party.get("email")
                    filtered_party["phone"] = party.get("phone")
            elif viewer_role in ["title_company", "lender"]:
                filtered_party["name"] = party.get("name")
                filtered_party["company"] = party.get("company")
                # Contact info for professionals only
                if role in ["buyer_agent", "seller_agent", "lender", "title_company"]:
                    filtered_party["email"] = party.get("email")
                    filtered_party["phone"] = party.get("phone")

            filtered.append(filtered_party)

        return filtered

    async def _get_timeline(self, transaction: TransactionModel) -> list[dict]:
        """Build transaction timeline/milestones."""
        timeline = []

        # Add key dates
        if transaction.effective_date:
            timeline.append({
                "date": str(transaction.effective_date),
                "event": "Contract Effective",
                "status": "completed",
            })

        # Add status changes as milestones
        status_milestones = {
            "active": ("Under Contract", "completed"),
            "pending_close": ("Clear to Close", "completed"),
            "closed": ("Closing Complete", "completed"),
        }

        if transaction.status in status_milestones:
            label, status = status_milestones[transaction.status]
            timeline.append({
                "date": str(transaction.updated_at.date()) if transaction.updated_at else None,
                "event": label,
                "status": status,
            })

        if transaction.closing_date:
            is_past = transaction.closing_date <= datetime.now().date()
            timeline.append({
                "date": str(transaction.closing_date),
                "event": "Scheduled Closing",
                "status": "completed" if is_past and transaction.status == "closed" else "upcoming",
            })

        return timeline

    async def _get_deadlines(
        self,
        transaction_id: UUID,
        party_role: str,
    ) -> list[dict]:
        """Get deadlines visible to this party."""
        stmt = select(DeadlineModel).where(
            DeadlineModel.transaction_id == transaction_id
        ).order_by(DeadlineModel.due_date)

        result = await self.session.execute(stmt)
        deadlines = result.scalars().all()

        # Filter deadlines based on role
        visible = []
        for d in deadlines:
            # Most deadlines are visible to all parties
            visible.append({
                "id": str(d.id),
                "name": d.name,
                "due_date": str(d.due_date),
                "status": d.status,
                "is_overdue": d.due_date < datetime.now().date() and d.status not in ["completed", "waived"],
            })

        return visible

    async def _get_documents(
        self,
        transaction_id: UUID,
        party_role: str,
    ) -> list[dict]:
        """Get documents visible to this party (metadata only, not content)."""
        stmt = select(DocumentModel).where(
            DocumentModel.transaction_id == transaction_id
        ).order_by(DocumentModel.uploaded_at.desc())

        result = await self.session.execute(stmt)
        documents = result.scalars().all()

        visible = []
        for doc in documents:
            # Skip confidential documents for external parties
            if getattr(doc, "is_confidential", False):
                if party_role in ["buyer", "seller", "lender", "title_company"]:
                    continue

            # Skip documents that haven't been verified
            if doc.status not in ["verified", "extracted"]:
                continue

            visible.append({
                "id": str(doc.id),
                "filename": doc.filename,
                "document_type": doc.document_type,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "can_download": self._can_download(doc.document_type, party_role),
            })

        return visible

    def _can_download(self, document_type: str, party_role: str) -> bool:
        """Determine if a party can download a document type."""
        # Define download permissions per role
        always_downloadable = [
            "purchase_contract",
            "closing_disclosure",
            "deed",
        ]

        if document_type.lower() in always_downloadable:
            return True

        # Agents can download most documents
        if party_role in ["buyer_agent", "seller_agent"]:
            return True

        # Title company can download title-related docs
        if party_role == "title_company":
            return document_type.lower() in [
                "title_commitment", "survey", "deed", "closing_disclosure"
            ]

        # Lender can download financial docs
        if party_role == "lender":
            return document_type.lower() in [
                "appraisal", "closing_disclosure", "pre_approval"
            ]

        # Buyers/sellers get limited access
        return False

    async def update_party_portal_access(
        self,
        transaction_id: UUID,
        party_email: str,
        portal_token: str,
    ) -> bool:
        """
        Update party record with portal token.

        Stores token in the parties JSONB for tracking.
        """
        stmt = select(TransactionModel).where(
            TransactionModel.id == transaction_id
        )
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False

        parties = list(transaction.parties or [])
        updated = False

        for party in parties:
            if party.get("email") == party_email:
                party["portal_token"] = portal_token
                party["portal_token_created"] = datetime.now().isoformat()
                party["portal_last_accessed"] = None
                updated = True
                break

        if updated:
            transaction.parties = parties
            await self.session.flush()

        return updated

    async def record_portal_access(
        self,
        transaction_id: UUID,
        party_email: str,
    ) -> None:
        """Record that a party accessed the portal."""
        stmt = select(TransactionModel).where(
            TransactionModel.id == transaction_id
        )
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            return

        parties = list(transaction.parties or [])

        for party in parties:
            if party.get("email") == party_email:
                party["portal_last_accessed"] = datetime.now().isoformat()
                break

        transaction.parties = parties
        await self.session.flush()

    async def list_active_tokens(
        self,
        transaction_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        List active portal tokens for a transaction.

        Returns information about parties with portal access.
        """
        stmt = select(TransactionModel).where(
            TransactionModel.id == transaction_id
        )
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            return []

        tokens = []
        for party in (transaction.parties or []):
            if party.get("portal_token"):
                tokens.append({
                    "party_email": party.get("email"),
                    "party_role": party.get("role"),
                    "party_name": party.get("name"),
                    "created_at": party.get("portal_token_created"),
                    "last_accessed": party.get("portal_last_accessed"),
                })

        return tokens

    async def revoke_token(
        self,
        transaction_id: UUID,
        party_email: str,
    ) -> bool:
        """
        Revoke a portal token for a party.

        Removes the portal token from the party record.

        Returns:
            True if token was revoked, False if not found
        """
        stmt = select(TransactionModel).where(
            TransactionModel.id == transaction_id
        )
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False

        parties = list(transaction.parties or [])
        revoked = False

        for party in parties:
            if party.get("email") == party_email:
                party.pop("portal_token", None)
                party.pop("portal_token_created", None)
                party["portal_revoked_at"] = datetime.now().isoformat()
                revoked = True
                break

        if revoked:
            transaction.parties = parties
            await self.session.flush()

        return revoked


def get_portal_service(session: AsyncSession) -> PortalService:
    """Factory function for PortalService."""
    return PortalService(session)
