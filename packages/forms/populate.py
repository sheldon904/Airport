"""Form population service - fills Florida real estate forms with extracted data."""

import io
import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from packages.forms.templates import (
    FL_FORM_TEMPLATES,
    FieldType,
    FormField,
    FormTemplate,
    get_template,
)


class FormPopulationError(Exception):
    """Error during form population."""

    pass


class DataExtractor:
    """
    Extracts values from nested data structures using JSONPath-like expressions.

    Supports:
    - Simple paths: "property_address.street"
    - Array indexing: "parties[0].name"
    - Array filtering: "parties[?role=='buyer'].name | [0]"
    """

    @staticmethod
    def extract(data: dict[str, Any], path: str) -> Any:
        """
        Extract a value from data using a JSONPath-like path.

        Args:
            data: Source data dictionary
            path: JSONPath-like expression

        Returns:
            Extracted value or None if not found
        """
        if not path or not data:
            return None

        # Handle filter expressions: parties[?role=='buyer'].name | [0]
        if "[?" in path:
            return DataExtractor._extract_with_filter(data, path)

        # Handle simple paths with array indices
        return DataExtractor._extract_simple(data, path)

    @staticmethod
    def _extract_simple(data: Any, path: str) -> Any:
        """Extract using simple dot notation with optional array indices."""
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # Remove empty strings

        current = data
        for part in parts:
            if current is None:
                return None

            # Check if part is a numeric index
            if part.isdigit():
                idx = int(part)
                if isinstance(current, list) and idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    @staticmethod
    def _extract_with_filter(data: dict[str, Any], path: str) -> Any:
        """Extract using filter expressions like parties[?role=='buyer'].name | [0]."""
        # Parse the filter expression
        # Example: parties[?role=='buyer'].name | [0]

        # Split on pipe for post-processing
        main_path, *post_ops = path.split("|")
        main_path = main_path.strip()

        # Parse: array_path[?field=='value'].result_field
        match = re.match(
            r"(\w+)\[\?(\w+)==['\"](.+?)['\"]\]\.?(\w+)?",
            main_path
        )

        if not match:
            return None

        array_path, filter_field, filter_value, result_field = match.groups()

        # Get the array
        array = data.get(array_path, [])
        if not isinstance(array, list):
            return None

        # Filter the array
        filtered = [
            item for item in array
            if isinstance(item, dict) and item.get(filter_field) == filter_value
        ]

        # Extract result field if specified
        if result_field:
            filtered = [item.get(result_field) for item in filtered if result_field in item]

        # Apply post-operations
        result = filtered
        for op in post_ops:
            op = op.strip()
            if op.startswith("[") and op.endswith("]"):
                idx_str = op[1:-1]
                if idx_str.isdigit():
                    idx = int(idx_str)
                    if isinstance(result, list) and idx < len(result):
                        result = result[idx]
                    else:
                        return None

        return result


class FormPopulationService:
    """
    Service for populating Florida real estate forms with transaction data.

    Takes extracted document data and transaction information and fills
    in form fields according to predefined templates.
    """

    def __init__(self) -> None:
        self.extractor = DataExtractor()

    def populate_form(
        self,
        template_id: str,
        transaction_data: dict[str, Any],
        extracted_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Populate a form template with transaction and extracted data.

        Args:
            template_id: ID of the form template to populate
            transaction_data: Transaction data (parties, dates, etc.)
            extracted_data: Optional extracted document data

        Returns:
            Dictionary of populated field values

        Raises:
            FormPopulationError: If template not found or required field missing
        """
        template = get_template(template_id)
        if not template:
            raise FormPopulationError(f"Template not found: {template_id}")

        # Merge data sources (extracted data takes precedence for matching fields)
        combined_data = self._merge_data(transaction_data, extracted_data or {})

        # Populate fields
        populated: dict[str, Any] = {}
        missing_required: list[str] = []
        warnings: list[str] = []

        for field in template.fields:
            # Skip signature/initials fields - these require human action
            if field.field_type in (FieldType.SIGNATURE, FieldType.INITIALS):
                populated[field.name] = None
                continue

            # Extract value
            value = self.extractor.extract(combined_data, field.data_path)

            # Apply default if no value found
            if value is None and field.default is not None:
                value = field.default

            # Format the value
            if value is not None:
                value = self._format_value(value, field)

            # Check required fields
            if field.required and value is None:
                missing_required.append(field.label)

            populated[field.name] = value

        return {
            "template_id": template_id,
            "template_name": template.name,
            "form_number": template.form_number,
            "populated_fields": populated,
            "missing_required": missing_required,
            "warnings": warnings,
            "is_complete": len(missing_required) == 0,
            "populated_at": datetime.now().isoformat(),
        }

    def populate_all_required_forms(
        self,
        transaction_data: dict[str, Any],
        extracted_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Populate all required forms for a transaction.

        Determines which forms are required based on transaction characteristics
        and populates each one.

        Returns:
            List of populated form results
        """
        from packages.forms.templates import get_required_templates

        # Determine required templates
        required = get_required_templates(
            is_residential=True,
            year_built=transaction_data.get("year_built"),
            is_hoa=transaction_data.get("is_hoa", False),
            is_condo=transaction_data.get("is_condo", False),
        )

        results = []
        for template in required:
            try:
                result = self.populate_form(
                    template.id,
                    transaction_data,
                    extracted_data,
                )
                results.append(result)
            except FormPopulationError as e:
                results.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "error": str(e),
                    "is_complete": False,
                })

        return results

    def get_missing_data_summary(
        self,
        template_id: str,
        transaction_data: dict[str, Any],
        extracted_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze what data is missing to complete a form.

        Returns:
            Summary of missing required and optional fields
        """
        template = get_template(template_id)
        if not template:
            raise FormPopulationError(f"Template not found: {template_id}")

        combined_data = self._merge_data(transaction_data, extracted_data or {})

        missing_required = []
        missing_optional = []
        filled_count = 0
        total_count = 0

        for field in template.fields:
            if field.field_type in (FieldType.SIGNATURE, FieldType.INITIALS):
                continue

            total_count += 1
            value = self.extractor.extract(combined_data, field.data_path)

            if value is None and field.default is None:
                if field.required:
                    missing_required.append({
                        "field": field.name,
                        "label": field.label,
                        "data_path": field.data_path,
                    })
                else:
                    missing_optional.append({
                        "field": field.name,
                        "label": field.label,
                        "data_path": field.data_path,
                    })
            else:
                filled_count += 1

        return {
            "template_id": template_id,
            "template_name": template.name,
            "total_fields": total_count,
            "filled_fields": filled_count,
            "completion_percentage": round((filled_count / total_count * 100), 1) if total_count > 0 else 0,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "is_complete": len(missing_required) == 0,
        }

    def _merge_data(
        self,
        transaction_data: dict[str, Any],
        extracted_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge transaction and extracted data, with transaction taking precedence."""
        merged = {}

        # Start with extracted data
        merged.update(extracted_data)

        # Override with transaction data
        merged.update(transaction_data)

        # Special handling for nested structures
        # Merge parties arrays
        if "parties" in transaction_data and "parties" in extracted_data:
            # Use transaction parties as base, supplement with extracted
            merged["parties"] = self._merge_parties(
                transaction_data.get("parties", []),
                extracted_data.get("parties", []),
            )

        return merged

    def _merge_parties(
        self,
        transaction_parties: list[dict],
        extracted_parties: list[dict],
    ) -> list[dict]:
        """Merge party lists, preferring transaction data for duplicates."""
        merged = {p.get("email", p.get("name", "")): p for p in extracted_parties}

        for party in transaction_parties:
            key = party.get("email", party.get("name", ""))
            if key in merged:
                # Merge, with transaction data taking precedence
                merged[key] = {**merged[key], **party}
            else:
                merged[key] = party

        return list(merged.values())

    def _format_value(self, value: Any, field: FormField) -> str | None:
        """Format a value according to field type."""
        if value is None:
            return None

        if field.field_type == FieldType.CURRENCY:
            return self._format_currency(value, field.format_pattern)
        elif field.field_type == FieldType.DATE:
            return self._format_date(value)
        elif field.field_type == FieldType.NUMBER:
            return str(value)
        elif field.field_type == FieldType.CHECKBOX:
            return "Yes" if value else "No"
        else:
            return str(value)

    def _format_currency(self, value: Any, pattern: str | None = None) -> str:
        """Format a numeric value as currency."""
        try:
            if isinstance(value, str):
                # Remove existing currency symbols and commas
                value = value.replace("$", "").replace(",", "")
            num_value = float(value)

            if pattern:
                # Use pattern like "${:,.2f}"
                return pattern.format(num_value)
            else:
                return f"${num_value:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def _format_date(self, value: Any) -> str:
        """Format a date value as MM/DD/YYYY."""
        if isinstance(value, date):
            return value.strftime("%m/%d/%Y")
        elif isinstance(value, datetime):
            return value.strftime("%m/%d/%Y")
        elif isinstance(value, str):
            # Try to parse and reformat
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
                try:
                    parsed = datetime.strptime(value, fmt)
                    return parsed.strftime("%m/%d/%Y")
                except ValueError:
                    continue
            return value
        else:
            return str(value)

    def generate_form_json(
        self,
        template_id: str,
        transaction_data: dict[str, Any],
        extracted_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate JSON representation of populated form for API response.

        Returns:
            JSON string of populated form data
        """
        result = self.populate_form(template_id, transaction_data, extracted_data)
        return json.dumps(result, indent=2, default=str)


def get_form_service() -> FormPopulationService:
    """Factory function for FormPopulationService."""
    return FormPopulationService()
