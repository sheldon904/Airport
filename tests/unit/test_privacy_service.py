"""Unit tests for PII detection and privacy service."""

import pytest
from datetime import datetime

from packages.core.services.privacy import (
    PrivacyService,
    PIIPattern,
    PIIType,
    get_privacy_service,
)


class TestPIIPatterns:
    """Tests for PII detection patterns."""

    def test_detect_ssn_with_dashes(self):
        """Detects SSN with dashes."""
        match = PIIPattern.SSN.search("My SSN is 123-45-6789")
        assert match is not None
        assert match.group() == "123-45-6789"

    def test_detect_ssn_with_spaces(self):
        """Detects SSN with spaces."""
        match = PIIPattern.SSN.search("SSN: 123 45 6789")
        assert match is not None

    def test_detect_ssn_no_separator(self):
        """Detects SSN without separators."""
        match = PIIPattern.SSN.search("SSN 123456789")
        assert match is not None

    def test_no_false_positive_short_number(self):
        """Short numbers don't match SSN pattern."""
        match = PIIPattern.SSN.search("Call 123-4567")
        assert match is None

    def test_detect_phone_standard(self):
        """Detects standard phone format."""
        match = PIIPattern.PHONE.search("Call (555) 123-4567")
        assert match is not None

    def test_detect_phone_with_country_code(self):
        """Detects phone with country code."""
        match = PIIPattern.PHONE.search("Phone: +1-555-123-4567")
        assert match is not None

    def test_detect_phone_dots(self):
        """Detects phone with dots."""
        match = PIIPattern.PHONE.search("555.123.4567")
        assert match is not None

    def test_detect_email(self):
        """Detects email addresses."""
        match = PIIPattern.EMAIL.search("Contact: john.doe@example.com")
        assert match is not None
        assert match.group() == "john.doe@example.com"

    def test_detect_email_with_plus(self):
        """Detects email with plus sign."""
        match = PIIPattern.EMAIL.search("Email: user+tag@gmail.com")
        assert match is not None

    def test_detect_bank_account(self):
        """Detects bank account patterns."""
        match = PIIPattern.BANK_ACCOUNT.search("Account: 1234567890123")
        assert match is not None

    def test_detect_credit_card(self):
        """Detects credit card patterns."""
        match = PIIPattern.CREDIT_CARD.search("Card: 4111-1111-1111-1111")
        assert match is not None


class TestPrivacyService:
    """Tests for PrivacyService."""

    @pytest.fixture
    def service(self):
        """Create privacy service instance."""
        return PrivacyService(session=None)

    def test_detect_pii_ssn(self, service):
        """Detects SSN in text."""
        result = service.detect_pii("John's SSN is 123-45-6789")
        assert len(result) == 1
        assert result[0]["type"] == PIIType.SSN
        assert result[0]["value"] == "123-45-6789"

    def test_detect_pii_multiple(self, service):
        """Detects multiple PII types."""
        text = """
        Name: John Doe
        SSN: 123-45-6789
        Phone: (555) 123-4567
        Email: john@example.com
        """
        result = service.detect_pii(text)

        types_found = {r["type"] for r in result}
        assert PIIType.SSN in types_found
        assert PIIType.PHONE in types_found
        assert PIIType.EMAIL in types_found

    def test_detect_pii_none(self, service):
        """Returns empty list when no PII found."""
        result = service.detect_pii("This is just regular text.")
        assert result == []

    def test_redact_text_ssn(self, service):
        """Redacts SSN from text."""
        text = "SSN: 123-45-6789"
        redacted = service.redact_text(text)
        assert "123-45-6789" not in redacted
        # Implementation uses XXX-XX-XXXX format
        assert "XXX-XX-XXXX" in redacted or "[REDACTED]" in redacted

    def test_redact_text_multiple(self, service):
        """Redacts multiple PII types."""
        text = "SSN: 123-45-6789, Phone: 555-123-4567"
        redacted = service.redact_text(text)
        assert "123-45-6789" not in redacted
        assert "555-123-4567" not in redacted

    def test_redact_text_specific_types(self, service):
        """Redacts only specified PII types."""
        text = "SSN: 123-45-6789, Phone: 555-123-4567"
        redacted = service.redact_text(text, pii_types=[PIIType.SSN])
        assert "123-45-6789" not in redacted
        assert "555-123-4567" in redacted

    def test_redact_dict_basic(self, service):
        """Redacts PII from dictionary values."""
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "notes": "Call 555-123-4567",
        }
        redacted, pii_found = service.redact_dict(data)

        assert "123-45-6789" not in str(redacted)
        assert len(pii_found) >= 2

    def test_redact_dict_nested(self, service):
        """Redacts PII from nested dictionary."""
        data = {
            "contact": {
                "email": "john@example.com",
                "phone": "555-123-4567",
            }
        }
        redacted, pii_found = service.redact_dict(data)

        assert "john@example.com" not in str(redacted)
        assert len(pii_found) >= 2

    def test_redact_dict_list(self, service):
        """Redacts PII from list values."""
        data = {
            "phones": ["555-123-4567", "555-987-6543"],
        }
        redacted, pii_found = service.redact_dict(data)

        assert "555-123-4567" not in str(redacted)
        assert "555-987-6543" not in str(redacted)
        assert len(pii_found) == 2

    def test_get_safe_data_internal_user(self, service):
        """Internal users see full data."""
        extracted = {"ssn": "123-45-6789", "name": "John"}
        redacted = {"ssn": "[REDACTED]", "name": "John"}

        result = service.get_safe_data(extracted, redacted, "admin")
        assert result["ssn"] == "123-45-6789"

    def test_get_safe_data_external_user(self, service):
        """External users see redacted data."""
        extracted = {"ssn": "123-45-6789", "name": "John"}
        redacted = {"ssn": "[REDACTED]", "name": "John"}

        result = service.get_safe_data(extracted, redacted, "buyer")
        assert result["ssn"] == "[REDACTED]"


class TestPrivacyServiceFactory:
    """Tests for privacy service factory function."""

    def test_get_privacy_service(self):
        """Factory returns PrivacyService instance."""
        service = get_privacy_service(None)
        assert isinstance(service, PrivacyService)
