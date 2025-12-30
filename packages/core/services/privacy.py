"""Privacy service - PII detection and redaction for document data."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.repositories.document import DocumentRepository


class PIIPattern:
    """PII detection patterns."""

    # Social Security Number: XXX-XX-XXXX or XXXXXXXXX
    SSN = re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b')

    # Phone numbers: various formats
    PHONE = re.compile(
        r'\b(?:\+?1[-.\s]?)?'
        r'(?:\(?\d{3}\)?[-.\s]?)'
        r'\d{3}[-.\s]?\d{4}\b'
    )

    # Email addresses
    EMAIL = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    )

    # Driver's license (Florida format: letter + 12 digits)
    FL_DRIVERS_LICENSE = re.compile(r'\b[A-Za-z]\d{12}\b')

    # Bank account numbers (8-17 digits)
    BANK_ACCOUNT = re.compile(r'\b\d{8,17}\b')

    # Credit card numbers (13-19 digits with optional spaces/dashes)
    CREDIT_CARD = re.compile(
        r'\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b'
    )

    # Street addresses (number + street name patterns)
    STREET_ADDRESS = re.compile(
        r'\b\d{1,6}\s+(?:[A-Za-z]+\s+){1,4}'
        r'(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|'
        r'Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl|Terrace|Ter)\b',
        re.IGNORECASE
    )


class PIIType:
    """PII type constants."""

    SSN = "ssn"
    PHONE = "phone"
    EMAIL = "email"
    DRIVERS_LICENSE = "drivers_license"
    BANK_ACCOUNT = "bank_account"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"


# Mapping of PII types to their patterns and redaction masks
PII_CONFIG = {
    PIIType.SSN: {
        "pattern": PIIPattern.SSN,
        "mask": "XXX-XX-XXXX",
        "sensitivity": "high",
    },
    PIIType.PHONE: {
        "pattern": PIIPattern.PHONE,
        "mask": "(XXX) XXX-XXXX",
        "sensitivity": "medium",
    },
    PIIType.EMAIL: {
        "pattern": PIIPattern.EMAIL,
        "mask": "[EMAIL REDACTED]",
        "sensitivity": "medium",
    },
    PIIType.DRIVERS_LICENSE: {
        "pattern": PIIPattern.FL_DRIVERS_LICENSE,
        "mask": "[DL REDACTED]",
        "sensitivity": "high",
    },
    PIIType.BANK_ACCOUNT: {
        "pattern": PIIPattern.BANK_ACCOUNT,
        "mask": "[ACCOUNT REDACTED]",
        "sensitivity": "high",
    },
    PIIType.CREDIT_CARD: {
        "pattern": PIIPattern.CREDIT_CARD,
        "mask": "XXXX-XXXX-XXXX-XXXX",
        "sensitivity": "high",
    },
    PIIType.ADDRESS: {
        "pattern": PIIPattern.STREET_ADDRESS,
        "mask": "[ADDRESS REDACTED]",
        "sensitivity": "medium",
    },
}

# Fields that commonly contain PII and should be checked
PII_FIELD_PATHS = [
    "parties.*.name",
    "parties.*.email",
    "parties.*.phone",
    "parties.*.ssn",
    "parties.*.drivers_license",
    "property_address.street",
    "property_address.full_address",
    "buyer_name",
    "seller_name",
    "buyer_email",
    "seller_email",
    "buyer_phone",
    "seller_phone",
    "lender_info.account_number",
]

# Roles that can view unredacted PII
PII_VIEWER_ROLES = ["admin", "broker"]


class PrivacyService:
    """
    Service for PII detection, redaction, and access control.

    Handles:
    - Detecting PII in extracted document data
    - Creating redacted versions for external sharing
    - Role-based access to sensitive data
    - Audit logging for PII access
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        if session:
            self.document_repo = DocumentRepository(session)

    def detect_pii(self, text: str) -> list[dict[str, Any]]:
        """
        Detect PII in text.

        Returns list of detected PII with type, value, position, and sensitivity.
        """
        detected = []

        for pii_type, config in PII_CONFIG.items():
            pattern = config["pattern"]
            for match in pattern.finditer(text):
                detected.append({
                    "type": pii_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "sensitivity": config["sensitivity"],
                })

        return detected

    def redact_text(self, text: str, pii_types: list[str] | None = None) -> str:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            pii_types: Optional list of PII types to redact. If None, redacts all.

        Returns:
            Redacted text
        """
        if pii_types is None:
            pii_types = list(PII_CONFIG.keys())

        result = text
        for pii_type in pii_types:
            if pii_type in PII_CONFIG:
                config = PII_CONFIG[pii_type]
                result = config["pattern"].sub(config["mask"], result)

        return result

    def redact_dict(
        self,
        data: dict[str, Any],
        pii_types: list[str] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Redact PII from a dictionary (like extracted_data).

        Returns:
            tuple: (redacted_data, list of detected PII fields)
        """
        if pii_types is None:
            pii_types = list(PII_CONFIG.keys())

        detected_fields: list[dict[str, Any]] = []
        redacted = self._redact_dict_recursive(data, pii_types, detected_fields, "")

        return redacted, detected_fields

    def _redact_dict_recursive(
        self,
        data: Any,
        pii_types: list[str],
        detected_fields: list[dict[str, Any]],
        path: str,
    ) -> Any:
        """Recursively redact PII in nested dict/list structures."""
        if isinstance(data, dict):
            return {
                k: self._redact_dict_recursive(
                    v, pii_types, detected_fields, f"{path}.{k}" if path else k
                )
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [
                self._redact_dict_recursive(
                    item, pii_types, detected_fields, f"{path}[{i}]"
                )
                for i, item in enumerate(data)
            ]
        elif isinstance(data, str):
            detected = self.detect_pii(data)
            if detected:
                detected_fields.append({
                    "path": path,
                    "pii_types": [d["type"] for d in detected],
                    "original_length": len(data),
                })
                return self.redact_text(data, pii_types)
            return data
        else:
            return data

    def get_safe_data(
        self,
        extracted_data: dict[str, Any] | None,
        redacted_data: dict[str, Any] | None,
        user_role: str,
    ) -> dict[str, Any] | None:
        """
        Get appropriate data based on user role.

        Args:
            extracted_data: Original extracted data with PII
            redacted_data: Pre-redacted data
            user_role: Role of the requesting user

        Returns:
            Full data for authorized roles, redacted data for others
        """
        if extracted_data is None:
            return None

        if user_role in PII_VIEWER_ROLES:
            return extracted_data

        # Return redacted version if available
        if redacted_data:
            return redacted_data

        # Generate redacted version on the fly
        redacted, _ = self.redact_dict(extracted_data)
        return redacted

    async def process_extraction_for_privacy(
        self,
        document_id: UUID,
        extracted_data: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Process extracted data for privacy compliance.

        Creates redacted version and records detected PII fields.

        Returns:
            tuple: (redacted_data, list of PII detections)
        """
        redacted_data, pii_fields = self.redact_dict(extracted_data)

        # Update document with redacted data and PII detection results
        if self.session and self.document_repo:
            await self.document_repo.update(
                document_id,
                redacted_data=redacted_data,
                pii_detected=pii_fields,
            )

        return redacted_data, pii_fields

    def should_redact_for_party(
        self,
        party_role: str,
        document_type: str,
        is_confidential: bool,
    ) -> bool:
        """
        Determine if data should be redacted for a specific party.

        Args:
            party_role: Role of the party (buyer, seller, title_company, etc.)
            document_type: Type of document
            is_confidential: Whether document is marked confidential

        Returns:
            True if data should be redacted for this party
        """
        # Always redact SSN for external parties
        if party_role in ["buyer", "seller", "title_company", "lender"]:
            return True

        # Agents can see full data unless confidential
        if party_role in ["buyer_agent", "seller_agent"]:
            return is_confidential

        return False

    def get_redaction_level(self, party_role: str) -> list[str]:
        """
        Get list of PII types to redact based on party role.

        Different parties need different redaction levels:
        - External parties: Full redaction
        - Agents: Minimal redaction (just SSN/bank accounts)
        - Title company: Partial (keep addresses, redact SSN)
        """
        if party_role in ["buyer", "seller"]:
            # Full redaction for principals viewing their own transaction
            # They know their own info, but shouldn't see other party's PII
            return [PIIType.SSN, PIIType.BANK_ACCOUNT, PIIType.CREDIT_CARD]

        if party_role == "title_company":
            # Title needs addresses but not SSN
            return [PIIType.SSN, PIIType.BANK_ACCOUNT]

        if party_role == "lender":
            # Lender needs most info for underwriting
            return [PIIType.SSN]  # Only redact SSN

        if party_role in ["buyer_agent", "seller_agent"]:
            # Agents see most data
            return [PIIType.SSN, PIIType.BANK_ACCOUNT]

        # Default: redact everything high-sensitivity
        return [PIIType.SSN, PIIType.BANK_ACCOUNT, PIIType.CREDIT_CARD, PIIType.DRIVERS_LICENSE]


# Document access levels
class AccessLevel:
    """Document access level constants."""

    ORGANIZATION = "organization"  # All org members
    TRANSACTION_PARTIES = "transaction_parties"  # Only assigned users
    RESTRICTED = "restricted"  # Admin/broker only


# Document types that should be confidential by default
CONFIDENTIAL_DOCUMENT_TYPES = [
    "addendum",
    "amendment",
    "counteroffer",
    "correspondence",
]


def is_confidential_document_type(document_type: str) -> bool:
    """Check if document type should be marked confidential by default."""
    return document_type.lower() in CONFIDENTIAL_DOCUMENT_TYPES


def get_privacy_service(session: AsyncSession | None = None) -> PrivacyService:
    """Factory function for PrivacyService."""
    return PrivacyService(session)
