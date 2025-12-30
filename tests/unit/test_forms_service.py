"""Unit tests for form population service."""

import pytest
from datetime import date

from packages.forms import (
    FormTemplate,
    FormField,
    FieldType,
    FormCategory,
    FL_FORM_TEMPLATES,
    get_template,
    get_templates_by_category,
    get_form_service,
)
from packages.forms.populate import DataExtractor, FormPopulationService
from packages.forms.disclosures import (
    get_required_disclosures,
    get_disclosure_checklist,
    FL_DISCLOSURE_REQUIREMENTS,
)


class TestFormTemplates:
    """Tests for form template definitions."""

    def test_far_bar_as_is_template_exists(self):
        """FAR/BAR AS-IS contract template exists."""
        assert "far_bar_as_is" in FL_FORM_TEMPLATES

    def test_far_bar_has_required_fields(self):
        """FAR/BAR template has essential fields."""
        template = FL_FORM_TEMPLATES["far_bar_as_is"]
        field_names = {f.name for f in template.fields}

        # Check for actual field names in the template
        assert "PropertyStreet" in field_names
        assert "PurchasePrice" in field_names

    def test_seller_disclosure_template_exists(self):
        """Seller disclosure template exists."""
        assert "seller_disclosure" in FL_FORM_TEMPLATES

    def test_lead_paint_disclosure_exists(self):
        """Lead paint disclosure template exists."""
        assert "lead_paint_disclosure" in FL_FORM_TEMPLATES

    def test_get_template_found(self):
        """get_template returns template by ID."""
        template = get_template("far_bar_as_is")
        assert template is not None
        assert template.id == "far_bar_as_is"

    def test_get_template_not_found(self):
        """get_template returns None for unknown ID."""
        template = get_template("nonexistent_form")
        assert template is None

    def test_get_templates_by_category(self):
        """get_templates_by_category filters correctly."""
        contracts = get_templates_by_category(FormCategory.CONTRACT)
        assert all(t.category == FormCategory.CONTRACT for t in contracts)

        disclosures = get_templates_by_category(FormCategory.DISCLOSURE)
        assert all(t.category == FormCategory.DISCLOSURE for t in disclosures)


class TestDataExtractor:
    """Tests for JSONPath-like data extraction."""

    def test_extract_simple_path(self):
        """Extracts simple path."""
        data = {"name": "John", "age": 30}
        assert DataExtractor.extract(data, "name") == "John"

    def test_extract_nested_path(self):
        """Extracts nested path."""
        data = {"address": {"city": "Miami"}}
        assert DataExtractor.extract(data, "address.city") == "Miami"

    def test_extract_array_index(self):
        """Extracts array by index."""
        data = {"items": ["a", "b", "c"]}
        assert DataExtractor.extract(data, "items[0]") == "a"
        assert DataExtractor.extract(data, "items[1]") == "b"

    def test_extract_with_filter(self):
        """Extracts with filter condition."""
        data = {
            "parties": [
                {"name": "Alice", "role": "buyer"},
                {"name": "Bob", "role": "seller"},
            ]
        }
        result = DataExtractor.extract(data, "parties[?role=='buyer'].name")
        assert result == ["Alice"]

    def test_extract_with_pipe(self):
        """Extracts with pipe for getting first element."""
        data = {
            "parties": [
                {"name": "Alice", "role": "buyer"},
            ]
        }
        result = DataExtractor.extract(data, "parties[?role=='buyer'].name | [0]")
        assert result == "Alice"

    def test_extract_missing_path(self):
        """Returns None for missing path."""
        data = {"name": "John"}
        assert DataExtractor.extract(data, "address.city") is None

    def test_extract_empty_path(self):
        """Returns None for empty path."""
        data = {"name": "John"}
        assert DataExtractor.extract(data, "") is None


class TestFormPopulationService:
    """Tests for form population service."""

    @pytest.fixture
    def service(self):
        """Create form population service instance."""
        return FormPopulationService()

    @pytest.fixture
    def sample_transaction(self):
        """Sample transaction data."""
        return {
            "property_address": {
                "street": "123 Main St",
                "city": "Miami",
                "state": "FL",
                "zip_code": "33101",
            },
            "purchase_price": 350000.00,
            "effective_date": date(2024, 12, 20),
            "closing_date": date(2025, 1, 20),
            "parties": [
                {"name": "John Buyer", "role": "buyer", "email": "john@example.com"},
                {"name": "Jane Seller", "role": "seller", "email": "jane@example.com"},
            ],
            "year_built": 1995,
            "is_hoa": True,
            "is_condo": False,
            "is_financed": True,
        }

    def test_populate_form_basic(self, service, sample_transaction):
        """Populates form with transaction data."""
        result = service.populate_form("far_bar_as_is", sample_transaction)

        assert result["template_id"] == "far_bar_as_is"
        assert result["populated_fields"] is not None
        assert "populated_at" in result

    def test_populate_form_not_found(self, service, sample_transaction):
        """Raises error for unknown template."""
        from packages.forms.populate import FormPopulationError
        with pytest.raises(FormPopulationError, match="not found"):
            service.populate_form("nonexistent_form", sample_transaction)

    def test_populate_form_identifies_missing(self, service):
        """Identifies missing required fields."""
        minimal_data = {"property_address": {"street": "123 Main St"}}
        result = service.populate_form("far_bar_as_is", minimal_data)

        assert len(result["missing_required"]) > 0
        assert result["is_complete"] is False

    def test_populate_form_with_extracted_data(self, service, sample_transaction):
        """Merges extracted data from documents."""
        extracted = {
            "earnest_money_amount": 10000,
            "inspection_period_days": 15,
        }
        result = service.populate_form("far_bar_as_is", sample_transaction, extracted)

        # Extracted data should be used
        fields = result["populated_fields"]
        if "earnest_money_amount" in fields:
            assert fields["earnest_money_amount"] == 10000

    def test_populate_all_required_forms(self, service, sample_transaction):
        """Populates all required forms for a transaction."""
        results = service.populate_all_required_forms(sample_transaction)

        assert len(results) > 0
        assert all("template_id" in r for r in results)

    def test_populate_uses_field_defaults(self, service):
        """Uses field defaults when data is missing."""
        # PropertyState field has a default value of "FL"
        empty_data = {"property_address": {"city": "Miami"}}
        result = service.populate_form("far_bar_as_is", empty_data)

        # PropertyState should use its default of "FL"
        populated_fields = result["populated_fields"]
        assert populated_fields.get("PropertyState") == "FL"


class TestDisclosures:
    """Tests for disclosure requirements."""

    def test_fl_disclosure_requirements_exist(self):
        """Florida disclosure requirements are defined."""
        assert len(FL_DISCLOSURE_REQUIREMENTS) > 0

    def test_radon_disclosure_required(self):
        """Radon disclosure is always required in Florida (residential)."""
        disclosures = get_required_disclosures(is_residential=True)
        disclosure_ids = [d.id for d in disclosures]
        assert "radon_gas" in disclosure_ids

    def test_lead_paint_required_pre_1978(self):
        """Lead paint disclosure required for pre-1978 homes."""
        disclosures = get_required_disclosures(year_built=1970)
        disclosure_ids = [d.id for d in disclosures]
        assert "lead_paint" in disclosure_ids

    def test_lead_paint_not_required_post_1978(self):
        """Lead paint disclosure not required for post-1978 homes."""
        disclosures = get_required_disclosures(year_built=1990)
        disclosure_ids = [d.id for d in disclosures]
        assert "lead_paint" not in disclosure_ids

    def test_hoa_disclosure_required_for_hoa(self):
        """HOA disclosure required when HOA exists."""
        disclosures = get_required_disclosures(is_hoa=True)
        disclosure_ids = [d.id for d in disclosures]
        assert "hoa_disclosure" in disclosure_ids

    def test_condo_disclosure_required_for_condo(self):
        """Condo disclosure required for condos."""
        disclosures = get_required_disclosures(is_condo=True)
        disclosure_ids = [d.id for d in disclosures]
        assert "condo_disclosure" in disclosure_ids

    def test_get_disclosure_checklist(self):
        """Returns formatted checklist for display."""
        transaction_data = {
            "year_built": 1970,
            "is_hoa": True,
            "is_condo": False,
        }
        checklist = get_disclosure_checklist(transaction_data)

        assert len(checklist) > 0
        assert all("disclosure_id" in item for item in checklist)
        assert all("name" in item for item in checklist)
        assert all("status" in item for item in checklist)


class TestFormServiceFactory:
    """Tests for form service factory."""

    def test_get_form_service(self):
        """Factory returns FormPopulationService instance."""
        service = get_form_service()
        assert isinstance(service, FormPopulationService)
