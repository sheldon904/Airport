"""Florida real estate disclosure requirements.

This module defines the statutory disclosure requirements for Florida
residential real estate transactions, tracking which disclosures are
required based on property characteristics and transaction type.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DisclosureCategory(str, Enum):
    """Categories of required disclosures."""

    ENVIRONMENTAL = "environmental"
    PROPERTY_CONDITION = "property_condition"
    FINANCIAL = "financial"
    ASSOCIATION = "association"
    LEGAL = "legal"


class DisclosureStatus(str, Enum):
    """Status of a disclosure requirement."""

    PENDING = "pending"
    PROVIDED = "provided"
    ACKNOWLEDGED = "acknowledged"
    WAIVED = "waived"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class DisclosureRequirement:
    """Definition of a disclosure requirement."""

    id: str
    name: str
    description: str
    category: DisclosureCategory
    statute: str  # Florida Statute or federal law reference
    deadline_days: int  # Days from effective date, 0 = at signing
    required_condition: str  # Condition that makes this required
    form_template_id: str | None  # Associated form template
    statutory_text: str  # Required disclosure language


# =============================================================================
# FLORIDA STATUTORY DISCLOSURES
# =============================================================================

FL_DISCLOSURE_REQUIREMENTS: dict[str, DisclosureRequirement] = {
    # Environmental Disclosures
    "radon_gas": DisclosureRequirement(
        id="radon_gas",
        name="Radon Gas Disclosure",
        description="Disclosure about radon gas and its potential health risks",
        category=DisclosureCategory.ENVIRONMENTAL,
        statute="F.S. 404.056(5)",
        deadline_days=0,  # At signing
        required_condition="all_residential",
        form_template_id="radon_disclosure",
        statutory_text=(
            "RADON GAS: Radon is a naturally occurring radioactive gas that, when it "
            "has accumulated in a building in sufficient quantities, may present health "
            "risks to persons who are exposed to it over time. Levels of radon that exceed "
            "federal and state guidelines have been found in buildings in Florida. "
            "Additional information regarding radon and radon testing may be obtained "
            "from your county health department."
        ),
    ),

    "lead_paint": DisclosureRequirement(
        id="lead_paint",
        name="Lead-Based Paint Disclosure",
        description="Federal disclosure for properties built before 1978",
        category=DisclosureCategory.ENVIRONMENTAL,
        statute="42 U.S.C. 4852d",
        deadline_days=0,  # At signing
        required_condition="pre_1978",
        form_template_id="lead_paint_disclosure",
        statutory_text=(
            "Housing built before 1978 may contain lead-based paint. Lead from paint, "
            "paint chips, and dust can pose health hazards if not managed properly. "
            "Lead exposure is especially harmful to young children and pregnant women. "
            "Before renting pre-1978 housing, lessors must disclose the presence of "
            "known lead-based paint and/or lead-based paint hazards in the dwelling."
        ),
    ),

    "coastal_construction": DisclosureRequirement(
        id="coastal_construction",
        name="Coastal Construction Control Line Disclosure",
        description="Disclosure for properties in coastal construction control zones",
        category=DisclosureCategory.ENVIRONMENTAL,
        statute="F.S. 161.57",
        deadline_days=0,
        required_condition="coastal_zone",
        form_template_id=None,
        statutory_text=(
            "The property may be subject to coastal construction control line regulations "
            "and may be subject to special building requirements and restrictions."
        ),
    ),

    # Financial Disclosures
    "property_tax": DisclosureRequirement(
        id="property_tax",
        name="Property Tax Disclosure Summary",
        description="Disclosure that property taxes may increase after sale",
        category=DisclosureCategory.FINANCIAL,
        statute="F.S. 689.261",
        deadline_days=0,  # At signing
        required_condition="all_residential",
        form_template_id="property_tax_disclosure",
        statutory_text=(
            "PROPERTY TAX DISCLOSURE SUMMARY: The buyer should not rely on the seller's "
            "current property taxes as the amount of property taxes that the buyer may be "
            "obligated to pay in the year subsequent to purchase. A change in ownership "
            "may reset the assessed value of the property to full market value, which "
            "could result in higher property taxes. If you have any questions concerning "
            "valuation, contact the county property appraiser's office for information."
        ),
    ),

    "energy_efficiency": DisclosureRequirement(
        id="energy_efficiency",
        name="Energy Efficiency Rating Disclosure",
        description="Disclosure of building energy efficiency rating if available",
        category=DisclosureCategory.FINANCIAL,
        statute="F.S. 553.996",
        deadline_days=0,
        required_condition="all_residential",
        form_template_id=None,
        statutory_text=(
            "The energy efficiency rating of this building is [RATING]. This rating is "
            "based on a scale of 0 to 100, with 100 being the most efficient."
        ),
    ),

    # Property Condition Disclosures
    "seller_property_disclosure": DisclosureRequirement(
        id="seller_property_disclosure",
        name="Seller's Property Disclosure",
        description="Seller's disclosure of known property defects and conditions",
        category=DisclosureCategory.PROPERTY_CONDITION,
        statute="Johnson v. Davis, 480 So. 2d 625 (Fla. 1985)",
        deadline_days=3,  # Within 3 days of effective date
        required_condition="all_residential",
        form_template_id="seller_disclosure",
        statutory_text=(
            "Seller is obligated to disclose to buyer all known facts that materially "
            "and adversely affect the value of the property which are not readily "
            "observable by the buyer. This disclosure is not a warranty."
        ),
    ),

    "flood_disclosure": DisclosureRequirement(
        id="flood_disclosure",
        name="Flood Zone and Claims Disclosure",
        description="Disclosure of flood zone status and prior flood claims",
        category=DisclosureCategory.PROPERTY_CONDITION,
        statute="F.S. 689.25(1)(b)",
        deadline_days=0,
        required_condition="all_residential",
        form_template_id=None,
        statutory_text=(
            "If the property is located in a flood zone or has been the subject of a "
            "flood insurance claim or federal assistance for flood damage, seller must "
            "disclose this information to buyer."
        ),
    ),

    "sinkhole_disclosure": DisclosureRequirement(
        id="sinkhole_disclosure",
        name="Sinkhole Disclosure",
        description="Disclosure of prior sinkhole claims or known sinkhole activity",
        category=DisclosureCategory.PROPERTY_CONDITION,
        statute="F.S. 627.7073",
        deadline_days=0,
        required_condition="sinkhole_claim",
        form_template_id=None,
        statutory_text=(
            "Seller has filed a claim for sinkhole damage with an insurer and received "
            "payment for such claim. Buyer should conduct their own investigation."
        ),
    ),

    # Association Disclosures
    "hoa_disclosure": DisclosureRequirement(
        id="hoa_disclosure",
        name="Homeowners Association Disclosure",
        description="Disclosure of mandatory HOA membership and fees",
        category=DisclosureCategory.ASSOCIATION,
        statute="F.S. 720.401",
        deadline_days=3,
        required_condition="hoa_property",
        form_template_id="hoa_disclosure",
        statutory_text=(
            "The property is subject to a mandatory homeowners association. Buyer will "
            "be obligated to be a member of the homeowners association. Buyer will be "
            "obligated to pay assessments to the association. Assessments are subject "
            "to periodic change. Buyer should contact the association for current amounts."
        ),
    ),

    "condo_disclosure": DisclosureRequirement(
        id="condo_disclosure",
        name="Condominium Disclosure",
        description="Required condominium documents and rescission rights",
        category=DisclosureCategory.ASSOCIATION,
        statute="F.S. 718.503",
        deadline_days=3,
        required_condition="condominium",
        form_template_id="condo_rider",
        statutory_text=(
            "Buyer has a right to receive from seller the following documents: "
            "Declaration of Condominium, Articles of Incorporation, Bylaws, Rules, "
            "most recent year-end financial statement, and a Frequently Asked Questions "
            "and Answers document. Buyer may void the contract within 15 days after "
            "receiving all required documents, or up to closing if documents not received."
        ),
    ),

    # Legal Disclosures
    "code_violations": DisclosureRequirement(
        id="code_violations",
        name="Code Enforcement Disclosure",
        description="Disclosure of pending code enforcement violations",
        category=DisclosureCategory.LEGAL,
        statute="Case Law / Common Practice",
        deadline_days=0,
        required_condition="has_violations",
        form_template_id=None,
        statutory_text=(
            "Seller must disclose any pending code enforcement violations or liens "
            "against the property that may affect value or use of the property."
        ),
    ),

    "special_assessment": DisclosureRequirement(
        id="special_assessment",
        name="Special Assessment Disclosure",
        description="Disclosure of pending or approved special assessments",
        category=DisclosureCategory.LEGAL,
        statute="F.S. 718.503 / F.S. 720.401",
        deadline_days=0,
        required_condition="has_special_assessment",
        form_template_id=None,
        statutory_text=(
            "Seller must disclose any pending, approved, or contemplated special "
            "assessments that will be charged to the property."
        ),
    ),
}


def get_required_disclosures(
    *,
    is_residential: bool = True,
    year_built: int | None = None,
    is_hoa: bool = False,
    is_condo: bool = False,
    in_flood_zone: bool = False,
    in_coastal_zone: bool = False,
    has_sinkhole_claim: bool = False,
    has_code_violations: bool = False,
    has_special_assessment: bool = False,
) -> list[DisclosureRequirement]:
    """
    Get list of required disclosures based on property/transaction characteristics.

    Args:
        is_residential: Whether this is a residential transaction
        year_built: Year the property was built (for lead paint)
        is_hoa: Whether property is in an HOA
        is_condo: Whether property is a condominium
        in_flood_zone: Whether property is in a flood zone
        in_coastal_zone: Whether property is in a coastal construction zone
        has_sinkhole_claim: Whether there has been a prior sinkhole claim
        has_code_violations: Whether there are pending code violations
        has_special_assessment: Whether there are pending special assessments

    Returns:
        List of applicable DisclosureRequirement objects
    """
    required = []

    condition_map = {
        "all_residential": is_residential,
        "pre_1978": year_built is not None and year_built < 1978,
        "hoa_property": is_hoa,
        "condominium": is_condo,
        "flood_zone": in_flood_zone,
        "coastal_zone": in_coastal_zone,
        "sinkhole_claim": has_sinkhole_claim,
        "has_violations": has_code_violations,
        "has_special_assessment": has_special_assessment,
    }

    for disclosure in FL_DISCLOSURE_REQUIREMENTS.values():
        condition = disclosure.required_condition
        if condition in condition_map and condition_map[condition]:
            required.append(disclosure)

    return required


def get_disclosure_checklist(
    transaction_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Generate a disclosure checklist for a transaction.

    Returns list of disclosure items with status tracking.
    """
    required = get_required_disclosures(
        is_residential=True,
        year_built=transaction_data.get("year_built"),
        is_hoa=transaction_data.get("is_hoa", False),
        is_condo=transaction_data.get("is_condo", False),
        in_flood_zone=transaction_data.get("in_flood_zone", False),
        has_sinkhole_claim=transaction_data.get("has_sinkhole_claim", False),
        has_code_violations=transaction_data.get("has_code_violations", False),
        has_special_assessment=transaction_data.get("has_special_assessment", False),
    )

    return [
        {
            "disclosure_id": d.id,
            "name": d.name,
            "statute": d.statute,
            "deadline_days": d.deadline_days,
            "form_template_id": d.form_template_id,
            "status": DisclosureStatus.PENDING.value,
            "provided_at": None,
            "acknowledged_at": None,
        }
        for d in required
    ]
