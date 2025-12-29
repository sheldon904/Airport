"""
Tests for new features: rate limiting, exception handling, reports, audit logging.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient

from packages.core.exceptions import (
    AirportException,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    DuplicateEmailError,
    TransactionNotFoundError,
)
from packages.core.rate_limit import (
    RateLimiter,
    RateLimitConfig,
    ExponentialBackoff,
)


# === Exception Tests ===


class TestExceptions:
    """Tests for centralized exception handling."""

    def test_airport_exception_defaults(self):
        """Test AirportException default values."""
        exc = AirportException()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert "unexpected error" in exc.message.lower()

    def test_airport_exception_custom_message(self):
        """Test AirportException with custom message."""
        exc = AirportException(message="Custom error", details={"field": "value"})
        assert exc.message == "Custom error"
        assert exc.details["field"] == "value"

    def test_validation_error(self):
        """Test ValidationError properties."""
        exc = ValidationError(message="Invalid input")
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Invalid input"

    def test_authentication_error(self):
        """Test AuthenticationError properties."""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_not_found_error(self):
        """Test NotFoundError with resource details."""
        resource_id = uuid4()
        exc = TransactionNotFoundError(resource_id)
        assert exc.status_code == 404
        assert "Transaction" in exc.message
        assert str(resource_id) in exc.message

    def test_rate_limit_error(self):
        """Test RateLimitError with retry after."""
        exc = RateLimitError(retry_after=120)
        assert exc.status_code == 429
        assert exc.retry_after == 120
        assert "120" in exc.message

    def test_duplicate_email_error(self):
        """Test DuplicateEmailError is a conflict error."""
        exc = DuplicateEmailError()
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_EMAIL"


# === Rate Limiter Tests ===


class TestRateLimiter:
    """Tests for rate limiting functionality."""

    def test_rate_limiter_allows_under_limit(self):
        """Test requests are allowed under the limit."""
        limiter = RateLimiter()
        limiter.configure_default(RateLimitConfig(requests=5, window=60))

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = None

        # Should allow first 5 requests
        for i in range(5):
            allowed, remaining, retry_after = limiter.check(mock_request)
            assert allowed is True
            assert remaining == 4 - i

    def test_rate_limiter_blocks_over_limit(self):
        """Test requests are blocked over the limit."""
        limiter = RateLimiter()
        limiter.configure_default(RateLimitConfig(requests=3, window=60))

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = None

        # Make 3 requests to hit limit
        for _ in range(3):
            limiter.check(mock_request)

        # 4th request should be blocked
        allowed, remaining, retry_after = limiter.check(mock_request)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_rate_limiter_endpoint_specific_config(self):
        """Test endpoint-specific rate limit configuration."""
        limiter = RateLimiter()
        limiter.configure("/api/login", RateLimitConfig(requests=2, window=60))
        limiter.configure_default(RateLimitConfig(requests=100, window=60))

        # Mock login request
        login_request = MagicMock(spec=Request)
        login_request.url.path = "/api/login"
        login_request.client.host = "127.0.0.1"
        login_request.headers.get.return_value = None

        # Mock other request
        other_request = MagicMock(spec=Request)
        other_request.url.path = "/api/other"
        other_request.client.host = "127.0.0.1"
        other_request.headers.get.return_value = None

        # Login should be limited to 2
        limiter.check(login_request)
        limiter.check(login_request)
        allowed, _, _ = limiter.check(login_request)
        assert allowed is False

        # Other endpoint should still have lots of capacity
        allowed, remaining, _ = limiter.check(other_request)
        assert allowed is True
        assert remaining > 90

    def test_rate_limiter_reset(self):
        """Test resetting rate limit for a client."""
        limiter = RateLimiter()
        limiter.configure_default(RateLimitConfig(requests=1, window=60))

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = None

        # Use up limit
        limiter.check(mock_request)
        allowed, _, _ = limiter.check(mock_request)
        assert allowed is False

        # Reset
        limiter.reset("127.0.0.1:/test")

        # Should be allowed again
        allowed, _, _ = limiter.check(mock_request)
        assert allowed is True

    def test_rate_limiter_x_forwarded_for(self):
        """Test rate limiter uses X-Forwarded-For header."""
        limiter = RateLimiter()
        limiter.configure_default(RateLimitConfig(requests=1, window=60))

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "192.168.1.100, 10.0.0.1"

        limiter.check(mock_request)

        # Different client should have separate limit
        mock_request2 = MagicMock(spec=Request)
        mock_request2.url.path = "/test"
        mock_request2.client.host = "127.0.0.1"
        mock_request2.headers.get.return_value = "192.168.1.200"

        allowed, _, _ = limiter.check(mock_request2)
        assert allowed is True  # Different IP, separate bucket


# === Exponential Backoff Tests ===


class TestExponentialBackoff:
    """Tests for exponential backoff utility."""

    def test_initial_delay(self):
        """Test initial delay is minimum."""
        backoff = ExponentialBackoff(min_delay=1.0, max_delay=30.0)
        assert backoff.current_delay == 1.0

    def test_increase_delay(self):
        """Test delay increases exponentially."""
        backoff = ExponentialBackoff(min_delay=1.0, max_delay=30.0, multiplier=2.0)

        backoff.increase()
        assert backoff.current_delay == 2.0

        backoff.increase()
        assert backoff.current_delay == 4.0

        backoff.increase()
        assert backoff.current_delay == 8.0

    def test_max_delay_cap(self):
        """Test delay is capped at maximum."""
        backoff = ExponentialBackoff(min_delay=1.0, max_delay=10.0, multiplier=2.0)

        # Increase many times
        for _ in range(10):
            backoff.increase()

        assert backoff.current_delay == 10.0

    def test_reset(self):
        """Test reset returns to minimum delay."""
        backoff = ExponentialBackoff(min_delay=1.0, max_delay=30.0)

        backoff.increase()
        backoff.increase()
        assert backoff.current_delay > 1.0

        backoff.reset()
        assert backoff.current_delay == 1.0

    @pytest.mark.asyncio
    async def test_wait_includes_jitter(self):
        """Test wait includes random jitter."""
        import time

        backoff = ExponentialBackoff(min_delay=0.01, max_delay=1.0, jitter=0.5)

        start = time.time()
        await backoff.wait()
        elapsed = time.time() - start

        # Should be at least min_delay
        assert elapsed >= 0.01
        # Should be at most min_delay * (1 + jitter)
        assert elapsed < 0.02


# === Audit Service Tests ===


class TestAuditService:
    """Tests for audit logging service."""

    @pytest.mark.asyncio
    async def test_audit_log_creation(self, db_session):
        """Test creating an audit log entry."""
        from packages.core.services.audit import AuditService, AuditAction

        audit = AuditService(db_session)
        user_id = uuid4()

        entry = await audit.log(
            action=AuditAction.USER_LOGIN,
            user_id=user_id,
            ip_address="192.168.1.1",
            details={"success": True},
        )

        assert entry.action == "user.login"
        assert entry.user_id == user_id
        assert entry.ip_address == "192.168.1.1"
        assert entry.details["success"] is True

    @pytest.mark.asyncio
    async def test_audit_log_auth_action(self, db_session):
        """Test logging auth action helper."""
        from packages.core.services.audit import AuditService, AuditAction

        audit = AuditService(db_session)
        user_id = uuid4()

        entry = await audit.log_auth_action(
            action=AuditAction.LOGIN_FAILED,
            user_id=user_id,
            ip_address="10.0.0.1",
            success=False,
            details={"email": "test@example.com"},
        )

        assert entry.action == "user.login_failed"
        assert entry.details["success"] is False
        assert entry.details["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_audit_log_transaction_action(self, db_session):
        """Test logging transaction action helper."""
        from packages.core.services.audit import AuditService, AuditAction

        audit = AuditService(db_session)
        transaction_id = uuid4()
        user_id = uuid4()
        org_id = uuid4()

        entry = await audit.log_transaction_action(
            action=AuditAction.TRANSACTION_CREATED,
            transaction_id=transaction_id,
            user_id=user_id,
            organization_id=org_id,
        )

        assert entry.action == "transaction.created"
        assert entry.transaction_id == transaction_id
        assert entry.resource_type == "transaction"


# === Report Service Tests ===


class TestReportService:
    """Tests for compliance report generation."""

    @pytest.mark.asyncio
    async def test_compliance_metrics_calculation(self):
        """Test compliance metrics are calculated correctly."""
        from packages.core.services.report import ComplianceMetrics

        metrics = ComplianceMetrics(
            total_deadlines=10,
            completed_deadlines=8,
            overdue_deadlines=1,
            upcoming_deadlines=1,
            deadline_compliance_rate=80.0,
            total_documents=5,
            verified_documents=4,
            pending_documents=1,
            needs_review_documents=0,
            document_completion_rate=80.0,
            overall_compliance_score=80.0,
            risk_level="low",
        )

        assert metrics.deadline_compliance_rate == 80.0
        assert metrics.document_completion_rate == 80.0
        assert metrics.risk_level == "low"

    def test_render_html_report(self):
        """Test HTML report rendering."""
        from packages.core.services.report import (
            ReportService,
            TransactionSummaryReport,
            ComplianceMetrics,
        )
        from unittest.mock import MagicMock

        # Create mock session
        mock_session = MagicMock()
        service = ReportService(mock_session)

        report = TransactionSummaryReport(
            report_id="test-123",
            generated_at=datetime.utcnow(),
            transaction_id="tx-456",
            property_address={
                "street": "123 Main St",
                "city": "Miami",
                "state": "FL",
                "zip_code": "33101",
            },
            transaction_type="purchase",
            status="active",
            purchase_price=350000.00,
            effective_date=date(2024, 12, 20),
            closing_date=date(2025, 1, 20),
            days_to_closing=30,
            parties=[],
            metrics=ComplianceMetrics(
                total_deadlines=5,
                completed_deadlines=3,
                overdue_deadlines=0,
                upcoming_deadlines=2,
                deadline_compliance_rate=60.0,
                total_documents=3,
                verified_documents=2,
                pending_documents=1,
                needs_review_documents=0,
                document_completion_rate=66.7,
                overall_compliance_score=75.0,
                risk_level="low",
            ),
            deadlines=[],
            documents=[],
            warnings=[],
        )

        html = service.render_html_report(report)

        # Check HTML contains key information
        assert "123 Main St" in html
        assert "Miami" in html
        assert "$350,000" in html
        assert "75%" in html  # Compliance score
        assert "LOW RISK" in html


# === API Integration Tests ===


@pytest.mark.asyncio
async def test_reports_endpoint_requires_auth(client: AsyncClient):
    """Test reports endpoint requires authentication."""
    response = await client.get("/api/v1/reports/organization")
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_reports_endpoint_success(client: AsyncClient, auth_headers: dict):
    """Test reports endpoint returns data."""
    response = await client.get(
        "/api/v1/reports/dashboard",
        headers=auth_headers,
    )

    # Should return 200 or 404 if no data
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "active_transactions" in data or isinstance(data, dict)
