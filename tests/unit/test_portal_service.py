"""Unit tests for external party portal service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import jwt

from packages.core.services.portal import (
    PortalService,
    PORTAL_ELIGIBLE_ROLES,
    PORTAL_TOKEN_EXPIRY_DAYS,
    get_portal_service,
)
from packages.core.exceptions import AuthenticationError


class TestPortalConstants:
    """Tests for portal constants."""

    def test_eligible_roles_defined(self):
        """Portal eligible roles are defined."""
        assert "buyer" in PORTAL_ELIGIBLE_ROLES
        assert "seller" in PORTAL_ELIGIBLE_ROLES
        assert "buyer_agent" in PORTAL_ELIGIBLE_ROLES
        assert "seller_agent" in PORTAL_ELIGIBLE_ROLES
        assert "lender" in PORTAL_ELIGIBLE_ROLES
        assert "title_company" in PORTAL_ELIGIBLE_ROLES

    def test_token_expiry_reasonable(self):
        """Token expiry is a reasonable duration."""
        assert PORTAL_TOKEN_EXPIRY_DAYS > 0
        assert PORTAL_TOKEN_EXPIRY_DAYS <= 90


class TestPortalTokenGeneration:
    """Tests for portal token generation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            return PortalService(mock_session)

    def test_generate_token_valid_role(self, service):
        """Generates token for valid role."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            token = service.generate_portal_token(
                transaction_id=uuid4(),
                party_email="buyer@example.com",
                party_role="buyer",
            )

            assert token is not None
            assert len(token) > 0

    def test_generate_token_invalid_role(self, service):
        """Raises error for invalid role."""
        with pytest.raises(ValueError, match="not eligible"):
            service.generate_portal_token(
                transaction_id=uuid4(),
                party_email="random@example.com",
                party_role="random_person",
            )

    def test_generate_token_custom_expiry_days(self, service):
        """Accepts custom expiry in days."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            token = service.generate_portal_token(
                transaction_id=uuid4(),
                party_email="buyer@example.com",
                party_role="buyer",
                expires_in_days=7,
            )

            payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
            exp_datetime = datetime.utcfromtimestamp(payload["exp"])
            expected = datetime.utcnow() + timedelta(days=7)

            # Within 1 minute tolerance
            assert abs((exp_datetime - expected).total_seconds()) < 60

    def test_generate_token_custom_expiry_hours(self, service):
        """Accepts custom expiry in hours."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            token = service.generate_portal_token(
                transaction_id=uuid4(),
                party_email="seller@example.com",
                party_role="seller",
                expires_hours=24,
            )

            payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])
            exp_datetime = datetime.utcfromtimestamp(payload["exp"])
            expected = datetime.utcnow() + timedelta(hours=24)

            assert abs((exp_datetime - expected).total_seconds()) < 60

    def test_token_contains_required_claims(self, service):
        """Token contains required claims."""
        tx_id = uuid4()
        email = "agent@example.com"
        role = "buyer_agent"

        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            token = service.generate_portal_token(
                transaction_id=tx_id,
                party_email=email,
                party_role=role,
            )

            payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"])

            assert payload["tx"] == str(tx_id)
            assert payload["email"] == email
            assert payload["role"] == role
            assert payload["type"] == "portal"
            assert "exp" in payload
            assert "iat" in payload


class TestPortalTokenValidation:
    """Tests for portal token validation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            return PortalService(mock_session)

    def test_validate_token_success(self, service):
        """Validates a valid token."""
        tx_id = uuid4()

        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            token = service.generate_portal_token(
                transaction_id=tx_id,
                party_email="buyer@example.com",
                party_role="buyer",
            )

            payload = service.validate_portal_token(token)

            assert payload["tx"] == str(tx_id)
            assert payload["email"] == "buyer@example.com"
            assert payload["role"] == "buyer"

    def test_validate_token_expired(self, service):
        """Raises error for expired token."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"

            # Create manually with past expiry
            payload = {
                "tx": str(uuid4()),
                "email": "test@example.com",
                "role": "buyer",
                "type": "portal",
                "exp": datetime.utcnow() - timedelta(hours=1),
            }
            token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

            with pytest.raises(AuthenticationError, match="expired"):
                service.validate_portal_token(token)

    def test_validate_token_invalid_type(self, service):
        """Raises error for wrong token type."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"

            payload = {
                "tx": str(uuid4()),
                "email": "test@example.com",
                "role": "buyer",
                "type": "access",  # Wrong type
                "exp": datetime.utcnow() + timedelta(days=1),
            }
            token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

            with pytest.raises(AuthenticationError, match="Invalid token type"):
                service.validate_portal_token(token)

    def test_validate_token_invalid_signature(self, service):
        """Raises error for invalid signature."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"

            payload = {
                "tx": str(uuid4()),
                "email": "test@example.com",
                "role": "buyer",
                "type": "portal",
                "exp": datetime.utcnow() + timedelta(days=1),
            }
            # Sign with different key
            token = jwt.encode(payload, "wrong-key", algorithm="HS256")

            with pytest.raises(AuthenticationError, match="Invalid"):
                service.validate_portal_token(token)


class TestPortalPartyFiltering:
    """Tests for party information filtering."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            return PortalService(mock_session)

    def test_filter_parties_buyer_view(self, service):
        """Buyer sees appropriate party info."""
        parties = [
            {"name": "John Buyer", "role": "buyer", "email": "john@example.com", "phone": "555-1234"},
            {"name": "Agent Smith", "role": "buyer_agent", "company": "RE/MAX", "email": "agent@example.com"},
            {"name": "Jane Seller", "role": "seller", "email": "jane@example.com"},
        ]

        filtered = service._filter_parties(parties, "buyer")

        # Buyer should see names
        assert any(p.get("name") == "John Buyer" for p in filtered)
        assert any(p.get("name") == "Agent Smith" for p in filtered)

        # Agent contact info visible
        agent = next(p for p in filtered if p.get("role") == "buyer_agent")
        assert "company" in agent
        assert "email" in agent

    def test_filter_parties_title_company_view(self, service):
        """Title company sees professional contact info."""
        parties = [
            {"name": "John Buyer", "role": "buyer", "email": "john@example.com"},
            {"name": "Agent Smith", "role": "buyer_agent", "email": "agent@example.com", "company": "RE/MAX"},
            {"name": "Lender Corp", "role": "lender", "email": "lender@bank.com"},
        ]

        filtered = service._filter_parties(parties, "title_company")

        # Should see agent and lender contact
        agent = next((p for p in filtered if p.get("role") == "buyer_agent"), None)
        assert agent is not None
        assert "email" in agent

        lender = next((p for p in filtered if p.get("role") == "lender"), None)
        assert lender is not None
        assert "email" in lender


class TestPortalStatusLabels:
    """Tests for status label generation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create service with mock session."""
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            return PortalService(mock_session)

    def test_status_labels(self, service):
        """Status labels are human-readable."""
        assert "Contract" in service._get_status_label("active")
        assert "Close" in service._get_status_label("pending_close")
        assert "Closed" in service._get_status_label("closed")
        assert "Cancelled" in service._get_status_label("cancelled")


class TestPortalServiceFactory:
    """Tests for service factory."""

    def test_get_portal_service(self):
        """Factory returns service instance."""
        mock_session = MagicMock()
        with patch("packages.core.services.portal.settings") as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            service = get_portal_service(mock_session)
            assert isinstance(service, PortalService)
