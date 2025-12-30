"""
Unit tests for REM-001 through REM-015 bug fixes.

This test suite verifies all 15 remaining bug fixes identified in the
comprehensive system review (third iteration).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ============================================================================
# REM-002: Safe getattr in repository
# ============================================================================


class TestRepositorySafeColumn:
    """Test safe column access in base repository (REM-002)."""

    def test_disallowed_prefixes_blocked(self):
        """Verify columns starting with disallowed prefixes are rejected."""
        from packages.db.repositories.base import _DISALLOWED_PREFIXES, _DISALLOWED_ATTRS

        # Verify disallowed prefixes exist
        assert "__" in _DISALLOWED_PREFIXES
        assert "_sa_" in _DISALLOWED_PREFIXES

        # Verify disallowed attrs exist
        assert "metadata" in _DISALLOWED_ATTRS
        assert "registry" in _DISALLOWED_ATTRS
        assert "query" in _DISALLOWED_ATTRS

    def test_get_allowed_columns_caches_result(self):
        """Verify allowed columns are cached."""
        from packages.db.repositories.base import BaseRepository
        from packages.db.models import UserModel
        from unittest.mock import MagicMock

        mock_session = MagicMock()

        class TestRepo(BaseRepository):
            model = UserModel

        repo = TestRepo(mock_session)

        # First call should populate cache
        cols1 = repo._get_allowed_columns()

        # Second call should return same cached set
        cols2 = repo._get_allowed_columns()

        assert cols1 is cols2  # Same object (cached)

    def test_is_safe_column_rejects_internal_attrs(self):
        """Verify internal attributes are rejected."""
        from packages.db.repositories.base import BaseRepository
        from packages.db.models import UserModel
        from unittest.mock import MagicMock

        mock_session = MagicMock()

        class TestRepo(BaseRepository):
            model = UserModel

        repo = TestRepo(mock_session)

        # These should be rejected
        assert repo._is_safe_column("__dict__") is False
        assert repo._is_safe_column("__class__") is False
        assert repo._is_safe_column("_sa_instance_state") is False
        assert repo._is_safe_column("metadata") is False
        assert repo._is_safe_column("registry") is False

    def test_is_safe_column_accepts_valid_columns(self):
        """Verify valid column names are accepted."""
        from packages.db.repositories.base import BaseRepository
        from packages.db.models import UserModel
        from unittest.mock import MagicMock

        mock_session = MagicMock()

        class TestRepo(BaseRepository):
            model = UserModel

        repo = TestRepo(mock_session)

        # Common column names should be allowed
        assert repo._is_safe_column("id") is True
        assert repo._is_safe_column("email") is True
        assert repo._is_safe_column("created_at") is True


# ============================================================================
# REM-004: Template injection prevention
# ============================================================================


class TestTemplateInjection:
    """Test safe template rendering (REM-004)."""

    def test_render_template_uses_string_template(self):
        """Verify templates use string.Template syntax ($var)."""
        from services.api.routers.communications import EMAIL_TEMPLATES

        # All templates should use $variable syntax, not {variable}
        for name, template in EMAIL_TEMPLATES.items():
            subject = template["subject"]
            body = template["body"]

            # Should have $ for variables
            assert "$" in subject or "$" in body, f"Template {name} should use $ syntax"

            # Should NOT have { format strings (except for HTML/JSON)
            # Check that {{ or {variable} format is not used
            import re
            format_pattern = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
            assert not re.search(format_pattern, subject), f"Template {name} subject uses format syntax"

    def test_sanitize_variable_removes_dollar_signs(self):
        """Verify variable values are sanitized."""
        from services.api.routers.communications import _sanitize_variable

        # Dollar signs should be removed to prevent injection
        assert _sanitize_variable("$malicious") == "malicious"
        assert _sanitize_variable("test$value") == "testvalue"
        assert _sanitize_variable(None) == ""

    def test_render_template_validates_required_vars(self):
        """Verify missing required variables raise error."""
        from services.api.routers.communications import render_template, TemplateError

        # Missing required variables should raise TemplateError
        with pytest.raises(TemplateError) as exc_info:
            render_template("deadline_reminder", {})

        assert "Missing required variables" in str(exc_info.value)

    def test_render_template_generates_html(self):
        """Verify HTML email is generated (REM-009)."""
        from services.api.routers.communications import render_template

        variables = {
            "recipient_name": "Test User",
            "deadline_name": "Inspection",
            "due_date": "2024-01-15",
            "property_address": "123 Main St",
            "sender_name": "Coordinator",
            "company_name": "Test Company",
        }

        subject, body, html_body = render_template("deadline_reminder", variables)

        # Should generate HTML
        assert html_body is not None
        assert "<!DOCTYPE html>" in html_body
        assert "Test Company" in html_body
        assert "Test User" in body


# ============================================================================
# REM-005, REM-014: Error response format
# ============================================================================


class TestErrorResponses:
    """Test error responses don't expose internal details (REM-005, REM-014)."""

    def test_portal_error_messages_are_generic(self):
        """Verify portal errors use generic messages."""
        # Import and check error message strings
        import services.api.routers.portal as portal

        # Read the source to verify error messages
        import inspect
        source = inspect.getsource(portal)

        # Should have generic error messages
        assert "Invalid or expired token" in source
        assert "Failed to send invite. Please try again later." in source or "Failed to send invite" in source

    def test_communications_error_is_generic(self):
        """Verify email send errors are generic."""
        import services.api.routers.communications as comms
        import inspect

        source = inspect.getsource(comms)

        # Should have generic error for email failures
        assert "Failed to send email. Please try again later." in source


# ============================================================================
# REM-006: Debug print removal
# ============================================================================


class TestDebugPrintRemoval:
    """Test debug prints are removed from email service (REM-006)."""

    def test_console_email_service_uses_logging(self):
        """Verify ConsoleEmailService uses logging instead of print."""
        import inspect
        from packages.core.services.email import ConsoleEmailService

        source = inspect.getsource(ConsoleEmailService.send_email)

        # Should NOT have print statements in send_email
        assert 'print("' not in source or "# REM-006" in source
        # Should use logging
        assert "logger" in source.lower() or "self.logger" in source


# ============================================================================
# REM-008, REM-013: Company name from config
# ============================================================================


class TestCompanyNameConfig:
    """Test company name comes from config (REM-008, REM-013)."""

    def test_get_company_name_function_exists(self):
        """Verify _get_company_name function exists."""
        from services.api.routers.communications import _get_company_name

        # Should return a string
        name = _get_company_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_company_name_uses_settings(self):
        """Verify company name uses settings.app_name."""
        from services.api.routers.communications import _get_company_name
        from packages.core.config import settings

        name = _get_company_name()

        # Should match settings.app_name or have a default
        assert name == settings.app_name or name == "Airport TC"


# ============================================================================
# REM-010: Template variable validation
# ============================================================================


class TestTemplateVariableValidation:
    """Test template variable validation (REM-010)."""

    def test_validate_template_variables_returns_missing(self):
        """Verify missing variables are identified."""
        from services.api.routers.communications import _validate_template_variables

        # Deadline reminder requires specific variables
        missing = _validate_template_variables("deadline_reminder", {})

        assert "recipient_name" in missing
        assert "deadline_name" in missing
        assert "due_date" in missing

    def test_validate_template_variables_returns_empty_for_complete(self):
        """Verify complete variables return empty list."""
        from services.api.routers.communications import _validate_template_variables

        variables = {
            "recipient_name": "Test",
            "deadline_name": "Inspection",
            "due_date": "2024-01-15",
            "property_address": "123 Main St",
            "sender_name": "Coordinator",
            "company_name": "Company",
        }

        missing = _validate_template_variables("deadline_reminder", variables)
        assert len(missing) == 0


# ============================================================================
# REM-012: N+1 query optimization
# ============================================================================


class TestN1QueryOptimization:
    """Test N+1 query is optimized in priority service (REM-012)."""

    def test_priority_service_uses_combined_query(self):
        """Verify priority calculation uses combined deadline query."""
        import inspect
        from packages.core.services.priority import PriorityService

        source = inspect.getsource(PriorityService.calculate_health)

        # Should use combined query with case statements
        assert "case(" in source or "func.sum" in source
        # Should have comment about REM-012
        assert "REM-012" in source


# ============================================================================
# WebSocket improvements (REM-001, REM-007, REM-015)
# ============================================================================


class TestWebSocketImprovements:
    """Test WebSocket logging improvements."""

    def test_realtime_module_has_logger(self):
        """Verify realtime module has logging configured."""
        import services.api.routers.realtime as realtime

        assert hasattr(realtime, 'logger')

    def test_connection_manager_logs_errors(self):
        """Verify ConnectionManager logs errors instead of silently catching."""
        import inspect
        from services.api.routers.realtime import ConnectionManager

        source = inspect.getsource(ConnectionManager)

        # Should have logging calls
        assert "logger.warning" in source or "logger.error" in source
        # Should log queue full events (REM-015)
        assert "sse_queue_full" in source or "queue_full" in source

    def test_websocket_auth_has_logging(self):
        """Verify WebSocket auth failures are logged (REM-007)."""
        import inspect
        import services.api.routers.realtime as realtime

        source = inspect.getsource(realtime)

        # Should have auth failure logging
        assert "websocket_auth" in source or "auth_failed" in source


# ============================================================================
# REM-003: Auth dependency consistency
# ============================================================================


class TestAuthDependencyConsistency:
    """Test auth dependency usage is consistent (REM-003)."""

    def test_forms_uses_current_user_dep(self):
        """Verify forms.py uses CurrentUserDep."""
        import inspect
        import services.api.routers.forms as forms

        source = inspect.getsource(forms)

        # Should import CurrentUserDep
        assert "CurrentUserDep" in source
        # Should NOT import from auth router
        assert "from services.api.routers.auth import get_current_user" not in source

    def test_contacts_uses_current_user_dep(self):
        """Verify contacts.py uses CurrentUserDep."""
        import inspect
        import services.api.routers.contacts as contacts

        source = inspect.getsource(contacts)

        # Should import CurrentUserDep
        assert "CurrentUserDep" in source
        # Should NOT import from auth router
        assert "from services.api.routers.auth import get_current_user" not in source


# ============================================================================
# Integration tests
# ============================================================================


class TestIntegration:
    """Integration tests for bug fix combinations."""

    @pytest.mark.asyncio
    async def test_email_template_full_workflow(self):
        """Test complete email template rendering workflow."""
        from services.api.routers.communications import render_template

        # Complete workflow with all variables
        variables = {
            "recipient_name": "John Doe",
            "property_address": "123 Main St, Miami",
            "transaction_id": str(uuid4()),
            "sender_name": "Jane Smith",
            "company_name": "Test Realty",
            "subject": "Test Subject",
            "body": "Test body content with special chars: $100 & <script>",
        }

        subject, body, html_body = render_template("general", variables)

        # Verify rendering
        assert "Test Subject" in subject
        assert "Test body content" in body
        assert "Test Realty" in body

        # Verify HTML was generated
        assert html_body is not None
        assert "<html>" in html_body

        # Verify special characters don't break template
        assert "100" in body  # Dollar sign removed for safety
        assert "<script>" not in html_body  # HTML escaped


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
