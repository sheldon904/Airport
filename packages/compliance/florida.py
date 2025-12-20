"""Florida-specific compliance rules and checklist templates."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class FLDocumentCategory(str, Enum):
    """Florida document categories."""

    CONTRACT = "contract"
    DISCLOSURE = "disclosure"
    FINANCIAL = "financial"
    TITLE = "title"
    INSPECTION = "inspection"
    CLOSING = "closing"


@dataclass
class ChecklistRequirement:
    """A single checklist requirement."""

    id: str
    name: str
    description: str
    category: FLDocumentCategory
    required: bool = True
    condition: str | None = None  # e.g., "if property built before 1978"
    deadline_days: int | None = None  # Days from effective date


# Florida Residential Purchase Checklist Template
FL_RESIDENTIAL_PURCHASE_CHECKLIST = [
    # Contract Documents
    ChecklistRequirement(
        id="fl_contract_executed",
        name="Executed Purchase Contract",
        description="Fully signed residential purchase contract (FAR/BAR As-Is or standard)",
        category=FLDocumentCategory.CONTRACT,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_earnest_money_receipt",
        name="Earnest Money Receipt",
        description="Proof of earnest money deposit",
        category=FLDocumentCategory.CONTRACT,
        required=True,
        deadline_days=3,
    ),
    # Seller Disclosures
    ChecklistRequirement(
        id="fl_seller_disclosure",
        name="Seller's Property Disclosure",
        description="Florida seller's property disclosure statement",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
        deadline_days=3,
    ),
    ChecklistRequirement(
        id="fl_lead_paint",
        name="Lead-Based Paint Disclosure",
        description="Lead-based paint disclosure and acknowledgment",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
        condition="property built before 1978",
        deadline_days=10,
    ),
    ChecklistRequirement(
        id="fl_hoa_disclosure",
        name="HOA/Condo Disclosure",
        description="Homeowner's association or condominium documents",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
        condition="property in HOA or condo",
        deadline_days=3,
    ),
    ChecklistRequirement(
        id="fl_property_tax_disclosure",
        name="Property Tax Disclosure",
        description="Current property tax information",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_radon_disclosure",
        name="Radon Gas Disclosure",
        description="Florida radon gas disclosure",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_energy_disclosure",
        name="Energy Efficiency Disclosure",
        description="Florida Building Energy-Efficiency Rating System disclosure",
        category=FLDocumentCategory.DISCLOSURE,
        required=True,
    ),
    # Financial Documents
    ChecklistRequirement(
        id="fl_preapproval",
        name="Loan Pre-Approval Letter",
        description="Buyer's mortgage pre-approval or proof of funds",
        category=FLDocumentCategory.FINANCIAL,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_loan_commitment",
        name="Loan Commitment",
        description="Final loan commitment from lender",
        category=FLDocumentCategory.FINANCIAL,
        required=True,
    ),
    # Inspections
    ChecklistRequirement(
        id="fl_home_inspection",
        name="Home Inspection Report",
        description="General home inspection report",
        category=FLDocumentCategory.INSPECTION,
        required=False,
    ),
    ChecklistRequirement(
        id="fl_termite_inspection",
        name="WDO (Termite) Inspection",
        description="Wood-destroying organism inspection report",
        category=FLDocumentCategory.INSPECTION,
        required=False,
    ),
    ChecklistRequirement(
        id="fl_appraisal",
        name="Appraisal Report",
        description="Property appraisal for lender",
        category=FLDocumentCategory.INSPECTION,
        required=True,
        condition="financed purchase",
    ),
    ChecklistRequirement(
        id="fl_survey",
        name="Survey",
        description="Property boundary survey",
        category=FLDocumentCategory.INSPECTION,
        required=False,
    ),
    # Title Documents
    ChecklistRequirement(
        id="fl_title_commitment",
        name="Title Commitment",
        description="Title insurance commitment",
        category=FLDocumentCategory.TITLE,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_title_search",
        name="Title Search",
        description="Property title search results",
        category=FLDocumentCategory.TITLE,
        required=True,
    ),
    # Closing Documents
    ChecklistRequirement(
        id="fl_closing_disclosure",
        name="Closing Disclosure",
        description="Final closing disclosure (must receive 3 days before closing)",
        category=FLDocumentCategory.CLOSING,
        required=True,
    ),
    ChecklistRequirement(
        id="fl_deed",
        name="Warranty Deed",
        description="Deed transferring property ownership",
        category=FLDocumentCategory.CLOSING,
        required=True,
    ),
]


class FloridaComplianceEngine:
    """
    Florida-specific compliance rule engine.

    Provides:
    - Checklist templates for FL transactions
    - Deadline calculation based on FL statutes
    - Disclosure requirement validation
    """

    STATE = "FL"

    @classmethod
    def get_residential_purchase_checklist(
        cls,
        property_year_built: int | None = None,
        is_hoa: bool = False,
        is_financed: bool = True,
    ) -> list[ChecklistRequirement]:
        """
        Get the applicable checklist for a residential purchase.

        Filters requirements based on property characteristics.
        """
        checklist = []

        for req in FL_RESIDENTIAL_PURCHASE_CHECKLIST:
            # Apply condition filters
            if req.condition:
                if "before 1978" in req.condition:
                    if property_year_built and property_year_built >= 1978:
                        continue
                if "HOA or condo" in req.condition:
                    if not is_hoa:
                        continue
                if "financed purchase" in req.condition:
                    if not is_financed:
                        continue

            checklist.append(req)

        return checklist

    @classmethod
    def calculate_disclosure_deadline(
        cls,
        disclosure_type: str,
        effective_date: date,
    ) -> date | None:
        """Calculate deadline for a specific disclosure type."""
        for req in FL_RESIDENTIAL_PURCHASE_CHECKLIST:
            if req.id == disclosure_type and req.deadline_days:
                from datetime import timedelta

                return effective_date + timedelta(days=req.deadline_days)
        return None

    @classmethod
    def validate_required_documents(
        cls,
        provided_documents: list[str],
        property_year_built: int | None = None,
        is_hoa: bool = False,
        is_financed: bool = True,
    ) -> tuple[list[str], list[str]]:
        """
        Validate that all required documents are present.

        Returns:
            tuple: (missing_required, missing_optional)
        """
        checklist = cls.get_residential_purchase_checklist(
            property_year_built=property_year_built,
            is_hoa=is_hoa,
            is_financed=is_financed,
        )

        missing_required = []
        missing_optional = []

        for req in checklist:
            if req.id not in provided_documents:
                if req.required:
                    missing_required.append(req.id)
                else:
                    missing_optional.append(req.id)

        return (missing_required, missing_optional)
