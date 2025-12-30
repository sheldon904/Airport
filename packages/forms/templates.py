"""Florida real estate form templates.

This module defines the structure and field mappings for standard Florida
real estate forms including FAR/BAR contracts, riders, and disclosures.

Forms are defined as JSON-mappable structures that map extracted document
data to form fields for population.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FormCategory(str, Enum):
    """Categories of Florida real estate forms."""

    CONTRACT = "contract"
    RIDER = "rider"
    ADDENDUM = "addendum"
    DISCLOSURE = "disclosure"
    CLOSING = "closing"
    FINANCIAL = "financial"


class FieldType(str, Enum):
    """Form field types."""

    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    CHECKBOX = "checkbox"
    SIGNATURE = "signature"
    INITIALS = "initials"


@dataclass
class FormField:
    """Definition of a form field."""

    name: str  # Field name in the PDF
    label: str  # Human-readable label
    field_type: FieldType
    data_path: str  # JSONPath-like path to data
    required: bool = False
    default: Any = None
    format_pattern: str | None = None  # For dates, currencies, etc.


@dataclass
class FormTemplate:
    """Florida real estate form template definition."""

    id: str
    name: str
    description: str
    category: FormCategory
    version: str
    form_number: str  # Official form number (e.g., "ASIS-7")
    pages: int
    fields: list[FormField] = field(default_factory=list)
    required_for: list[str] = field(default_factory=list)  # Transaction conditions
    source: str = "Florida Realtors / Florida Bar"


# =============================================================================
# FAR/BAR AS-IS RESIDENTIAL CONTRACT FOR SALE AND PURCHASE
# =============================================================================

FAR_BAR_AS_IS_FIELDS = [
    # Header / Identification
    FormField("ContractDate", "Contract Date", FieldType.DATE, "effective_date", True),

    # Parties - Buyer(s)
    FormField("Buyer1Name", "Buyer 1 Name", FieldType.TEXT, "parties[?role=='buyer'].name | [0]", True),
    FormField("Buyer1Address", "Buyer 1 Address", FieldType.TEXT, "parties[?role=='buyer'].address | [0]"),
    FormField("Buyer1Phone", "Buyer 1 Phone", FieldType.TEXT, "parties[?role=='buyer'].phone | [0]"),
    FormField("Buyer1Email", "Buyer 1 Email", FieldType.TEXT, "parties[?role=='buyer'].email | [0]"),
    FormField("Buyer2Name", "Buyer 2 Name", FieldType.TEXT, "parties[?role=='buyer'].name | [1]"),

    # Parties - Seller(s)
    FormField("Seller1Name", "Seller 1 Name", FieldType.TEXT, "parties[?role=='seller'].name | [0]", True),
    FormField("Seller1Address", "Seller 1 Address", FieldType.TEXT, "parties[?role=='seller'].address | [0]"),
    FormField("Seller1Phone", "Seller 1 Phone", FieldType.TEXT, "parties[?role=='seller'].phone | [0]"),
    FormField("Seller1Email", "Seller 1 Email", FieldType.TEXT, "parties[?role=='seller'].email | [0]"),
    FormField("Seller2Name", "Seller 2 Name", FieldType.TEXT, "parties[?role=='seller'].name | [1]"),

    # Property Description
    FormField("PropertyStreet", "Property Street Address", FieldType.TEXT, "property_address.street", True),
    FormField("PropertyCity", "Property City", FieldType.TEXT, "property_address.city", True),
    FormField("PropertyState", "Property State", FieldType.TEXT, "property_address.state", True, "FL"),
    FormField("PropertyZip", "Property ZIP", FieldType.TEXT, "property_address.zip_code", True),
    FormField("PropertyCounty", "Property County", FieldType.TEXT, "property_address.county"),
    FormField("LegalDescription", "Legal Description", FieldType.TEXT, "legal_description"),
    FormField("TaxParcelID", "Tax Parcel ID", FieldType.TEXT, "tax_parcel_id"),

    # Purchase Price and Financing
    FormField("PurchasePrice", "Purchase Price", FieldType.CURRENCY, "purchase_price", True, format_pattern="${:,.2f}"),
    FormField("EarnestMoney", "Earnest Money Deposit", FieldType.CURRENCY, "earnest_money", True, format_pattern="${:,.2f}"),
    FormField("EarnestMoneyDays", "Earnest Money Due (days)", FieldType.NUMBER, "earnest_money_days", default=3),
    FormField("AdditionalDeposit", "Additional Deposit", FieldType.CURRENCY, "additional_deposit", format_pattern="${:,.2f}"),
    FormField("AdditionalDepositDays", "Additional Deposit Due (days)", FieldType.NUMBER, "additional_deposit_days"),
    FormField("FinancingAmount", "Financing Amount", FieldType.CURRENCY, "financing_amount", format_pattern="${:,.2f}"),
    FormField("BalanceAtClosing", "Balance Due at Closing", FieldType.CURRENCY, "balance_at_closing", format_pattern="${:,.2f}"),

    # Financing Contingency
    FormField("FinancingContingency", "Financing Contingency", FieldType.CHECKBOX, "has_financing_contingency"),
    FormField("LoanType", "Loan Type", FieldType.TEXT, "loan_type"),  # Conventional, FHA, VA, etc.
    FormField("LoanTerm", "Loan Term (years)", FieldType.NUMBER, "loan_term_years"),
    FormField("InterestRate", "Interest Rate (max)", FieldType.NUMBER, "max_interest_rate"),
    FormField("FinancingDeadlineDays", "Financing Contingency Days", FieldType.NUMBER, "financing_deadline_days", default=30),

    # Dates and Deadlines
    FormField("EffectiveDate", "Effective Date", FieldType.DATE, "effective_date", True),
    FormField("ClosingDate", "Closing Date", FieldType.DATE, "closing_date", True),
    FormField("InspectionPeriodDays", "Inspection Period (days)", FieldType.NUMBER, "inspection_period_days", True, default=15),
    FormField("WalkThroughDate", "Walk-Through Date", FieldType.DATE, "walkthrough_date"),

    # Escrow Agent / Title Company
    FormField("EscrowAgentName", "Escrow Agent Name", FieldType.TEXT, "parties[?role=='title_company'].name | [0]"),
    FormField("EscrowAgentAddress", "Escrow Agent Address", FieldType.TEXT, "parties[?role=='title_company'].address | [0]"),
    FormField("EscrowAgentPhone", "Escrow Agent Phone", FieldType.TEXT, "parties[?role=='title_company'].phone | [0]"),
    FormField("EscrowAgentEmail", "Escrow Agent Email", FieldType.TEXT, "parties[?role=='title_company'].email | [0]"),

    # Title Evidence
    FormField("TitleEvidenceType", "Title Evidence Type", FieldType.TEXT, "title_evidence_type", default="Title Insurance"),
    FormField("TitleCommitmentDays", "Title Commitment Days", FieldType.NUMBER, "title_commitment_days", default=15),
    FormField("TitleExaminationDays", "Title Examination Days", FieldType.NUMBER, "title_examination_days", default=5),

    # Property Condition (AS-IS specific)
    FormField("AsIsCondition", "Property Sold As-Is", FieldType.CHECKBOX, "is_as_is", default=True),

    # Inclusions / Exclusions
    FormField("PersonalPropertyIncluded", "Personal Property Included", FieldType.TEXT, "personal_property_included"),
    FormField("PersonalPropertyExcluded", "Personal Property Excluded", FieldType.TEXT, "personal_property_excluded"),

    # HOA / Condo
    FormField("IsHOA", "Subject to HOA", FieldType.CHECKBOX, "is_hoa"),
    FormField("IsCondo", "Is Condominium", FieldType.CHECKBOX, "is_condo"),
    FormField("HOAName", "HOA Name", FieldType.TEXT, "hoa_name"),
    FormField("HOAFee", "HOA Fee (monthly)", FieldType.CURRENCY, "hoa_monthly_fee", format_pattern="${:,.2f}"),

    # Agents
    FormField("BuyerAgentName", "Buyer's Agent Name", FieldType.TEXT, "parties[?role=='buyer_agent'].name | [0]"),
    FormField("BuyerAgentLicense", "Buyer's Agent License #", FieldType.TEXT, "parties[?role=='buyer_agent'].license_number | [0]"),
    FormField("BuyerAgentCompany", "Buyer's Agent Company", FieldType.TEXT, "parties[?role=='buyer_agent'].company | [0]"),
    FormField("BuyerAgentPhone", "Buyer's Agent Phone", FieldType.TEXT, "parties[?role=='buyer_agent'].phone | [0]"),
    FormField("BuyerAgentEmail", "Buyer's Agent Email", FieldType.TEXT, "parties[?role=='buyer_agent'].email | [0]"),

    FormField("SellerAgentName", "Seller's Agent Name", FieldType.TEXT, "parties[?role=='seller_agent'].name | [0]"),
    FormField("SellerAgentLicense", "Seller's Agent License #", FieldType.TEXT, "parties[?role=='seller_agent'].license_number | [0]"),
    FormField("SellerAgentCompany", "Seller's Agent Company", FieldType.TEXT, "parties[?role=='seller_agent'].company | [0]"),
    FormField("SellerAgentPhone", "Seller's Agent Phone", FieldType.TEXT, "parties[?role=='seller_agent'].phone | [0]"),
    FormField("SellerAgentEmail", "Seller's Agent Email", FieldType.TEXT, "parties[?role=='seller_agent'].email | [0]"),

    # Signatures (placeholders - not auto-filled)
    FormField("BuyerSignature1", "Buyer 1 Signature", FieldType.SIGNATURE, "", False),
    FormField("BuyerSignature1Date", "Buyer 1 Signature Date", FieldType.DATE, "", False),
    FormField("SellerSignature1", "Seller 1 Signature", FieldType.SIGNATURE, "", False),
    FormField("SellerSignature1Date", "Seller 1 Signature Date", FieldType.DATE, "", False),
]

# =============================================================================
# SELLER'S PROPERTY DISCLOSURE (SPD)
# =============================================================================

SELLER_DISCLOSURE_FIELDS = [
    # Property Information
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),
    FormField("PropertyCity", "City", FieldType.TEXT, "property_address.city", True),
    FormField("PropertyZip", "ZIP Code", FieldType.TEXT, "property_address.zip_code", True),
    FormField("SellerName", "Seller Name", FieldType.TEXT, "parties[?role=='seller'].name | [0]", True),
    FormField("YearBuilt", "Year Built", FieldType.NUMBER, "year_built"),
    FormField("YearsOccupied", "Years Seller Occupied", FieldType.NUMBER, "years_occupied"),

    # Structural
    FormField("RoofAge", "Roof Age (years)", FieldType.NUMBER, "roof_age"),
    FormField("RoofLeaks", "Known Roof Leaks", FieldType.CHECKBOX, "has_roof_leaks"),
    FormField("RoofRepairs", "Roof Repairs Made", FieldType.TEXT, "roof_repairs"),
    FormField("FoundationIssues", "Foundation Issues", FieldType.CHECKBOX, "has_foundation_issues"),
    FormField("FoundationDetails", "Foundation Details", FieldType.TEXT, "foundation_details"),
    FormField("WaterIntrusion", "Water Intrusion History", FieldType.CHECKBOX, "has_water_intrusion"),
    FormField("WaterIntrusionDetails", "Water Intrusion Details", FieldType.TEXT, "water_intrusion_details"),
    FormField("TermiteDamage", "Termite/Pest Damage", FieldType.CHECKBOX, "has_termite_damage"),
    FormField("TermiteDetails", "Termite Details", FieldType.TEXT, "termite_details"),
    FormField("TermiteBond", "Active Termite Bond", FieldType.CHECKBOX, "has_termite_bond"),

    # Plumbing
    FormField("PlumbingType", "Plumbing Type", FieldType.TEXT, "plumbing_type"),  # Copper, PVC, Polybutylene
    FormField("PlumbingIssues", "Known Plumbing Issues", FieldType.CHECKBOX, "has_plumbing_issues"),
    FormField("PlumbingDetails", "Plumbing Details", FieldType.TEXT, "plumbing_details"),
    FormField("WaterHeaterAge", "Water Heater Age", FieldType.NUMBER, "water_heater_age"),
    FormField("WaterSource", "Water Source", FieldType.TEXT, "water_source", default="Public"),
    FormField("WellPresent", "Well on Property", FieldType.CHECKBOX, "has_well"),
    FormField("SepticPresent", "Septic System", FieldType.CHECKBOX, "has_septic"),
    FormField("SepticLastPumped", "Septic Last Pumped", FieldType.DATE, "septic_last_pumped"),

    # Electrical
    FormField("ElectricalPanelAge", "Electrical Panel Age", FieldType.NUMBER, "electrical_panel_age"),
    FormField("ElectricalAmperage", "Service Amperage", FieldType.NUMBER, "electrical_amperage"),
    FormField("ElectricalIssues", "Known Electrical Issues", FieldType.CHECKBOX, "has_electrical_issues"),
    FormField("ElectricalDetails", "Electrical Details", FieldType.TEXT, "electrical_details"),
    FormField("AluminumWiring", "Aluminum Wiring Present", FieldType.CHECKBOX, "has_aluminum_wiring"),
    FormField("GFCIOutlets", "GFCI Outlets Installed", FieldType.CHECKBOX, "has_gfci_outlets"),

    # HVAC
    FormField("HVACAge", "HVAC System Age", FieldType.NUMBER, "hvac_age"),
    FormField("HVACType", "HVAC Type", FieldType.TEXT, "hvac_type"),  # Central, Window, Split
    FormField("HVACIssues", "Known HVAC Issues", FieldType.CHECKBOX, "has_hvac_issues"),
    FormField("HVACDetails", "HVAC Details", FieldType.TEXT, "hvac_details"),
    FormField("LastHVACService", "Last HVAC Service", FieldType.DATE, "last_hvac_service"),

    # Appliances
    FormField("AppliancesIncluded", "Appliances Included", FieldType.TEXT, "appliances_included"),
    FormField("ApplianceIssues", "Known Appliance Issues", FieldType.CHECKBOX, "has_appliance_issues"),
    FormField("ApplianceDetails", "Appliance Details", FieldType.TEXT, "appliance_details"),

    # Pool/Spa
    FormField("PoolPresent", "Pool Present", FieldType.CHECKBOX, "has_pool"),
    FormField("PoolType", "Pool Type", FieldType.TEXT, "pool_type"),  # In-ground, Above-ground
    FormField("PoolEquipmentAge", "Pool Equipment Age", FieldType.NUMBER, "pool_equipment_age"),
    FormField("PoolIssues", "Known Pool Issues", FieldType.CHECKBOX, "has_pool_issues"),
    FormField("PoolDetails", "Pool Details", FieldType.TEXT, "pool_details"),
    FormField("PoolFence", "Pool Fence/Barrier", FieldType.CHECKBOX, "has_pool_fence"),

    # Environmental
    FormField("FloodZone", "In Flood Zone", FieldType.CHECKBOX, "in_flood_zone"),
    FormField("FloodInsurance", "Flood Insurance Required", FieldType.CHECKBOX, "requires_flood_insurance"),
    FormField("FloodClaims", "Prior Flood Insurance Claims", FieldType.CHECKBOX, "has_flood_claims"),
    FormField("FloodClaimDetails", "Flood Claim Details", FieldType.TEXT, "flood_claim_details"),
    FormField("SinkholeClaim", "Prior Sinkhole Claim", FieldType.CHECKBOX, "has_sinkhole_claim"),
    FormField("SinkholeDetails", "Sinkhole Details", FieldType.TEXT, "sinkhole_details"),
    FormField("AsbestosPresent", "Asbestos Present", FieldType.CHECKBOX, "has_asbestos"),
    FormField("LeadPaintPresent", "Lead-Based Paint", FieldType.CHECKBOX, "has_lead_paint"),
    FormField("MoldIssues", "Known Mold Issues", FieldType.CHECKBOX, "has_mold"),
    FormField("MoldDetails", "Mold Details", FieldType.TEXT, "mold_details"),

    # HOA / Legal
    FormField("HOAMember", "HOA Membership", FieldType.CHECKBOX, "is_hoa"),
    FormField("HOAName", "HOA Name", FieldType.TEXT, "hoa_name"),
    FormField("HOAMonthlyFee", "Monthly HOA Fee", FieldType.CURRENCY, "hoa_monthly_fee"),
    FormField("HOASpecialAssessment", "Pending Special Assessment", FieldType.CHECKBOX, "has_special_assessment"),
    FormField("HOAViolations", "HOA Violations", FieldType.CHECKBOX, "has_hoa_violations"),
    FormField("CodeViolations", "Code Enforcement Violations", FieldType.CHECKBOX, "has_code_violations"),
    FormField("CodeViolationDetails", "Code Violation Details", FieldType.TEXT, "code_violation_details"),
    FormField("Encroachments", "Known Encroachments", FieldType.CHECKBOX, "has_encroachments"),
    FormField("BoundaryDisputes", "Boundary Disputes", FieldType.CHECKBOX, "has_boundary_disputes"),
    FormField("Easements", "Known Easements", FieldType.CHECKBOX, "has_easements"),
    FormField("EasementDetails", "Easement Details", FieldType.TEXT, "easement_details"),
    FormField("Liens", "Outstanding Liens", FieldType.CHECKBOX, "has_liens"),
    FormField("LienDetails", "Lien Details", FieldType.TEXT, "lien_details"),

    # Insurance
    FormField("InsuranceClaims", "Insurance Claims (past 5 years)", FieldType.CHECKBOX, "has_insurance_claims"),
    FormField("InsuranceClaimDetails", "Insurance Claim Details", FieldType.TEXT, "insurance_claim_details"),

    # Other
    FormField("OtherDefects", "Other Known Defects", FieldType.TEXT, "other_defects"),
    FormField("AdditionalDisclosures", "Additional Disclosures", FieldType.TEXT, "additional_disclosures"),

    # Signatures
    FormField("SellerSignature", "Seller Signature", FieldType.SIGNATURE, "", False),
    FormField("SellerSignatureDate", "Date", FieldType.DATE, "", False),
    FormField("BuyerAcknowledgment", "Buyer Acknowledgment", FieldType.SIGNATURE, "", False),
    FormField("BuyerAcknowledgmentDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# LEAD-BASED PAINT DISCLOSURE
# =============================================================================

LEAD_PAINT_DISCLOSURE_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),
    FormField("PropertyCity", "City", FieldType.TEXT, "property_address.city", True),
    FormField("PropertyZip", "ZIP Code", FieldType.TEXT, "property_address.zip_code", True),
    FormField("YearBuilt", "Year Built", FieldType.NUMBER, "year_built", True),

    # Seller Disclosure
    FormField("LeadPaintKnown", "Known Lead-Based Paint", FieldType.CHECKBOX, "has_lead_paint"),
    FormField("LeadPaintLocation", "Location of Known Lead Paint", FieldType.TEXT, "lead_paint_location"),
    FormField("LeadHazardsKnown", "Known Lead Hazards", FieldType.CHECKBOX, "has_lead_hazards"),
    FormField("LeadHazardLocation", "Location of Lead Hazards", FieldType.TEXT, "lead_hazard_location"),
    FormField("LeadReportsAvailable", "Lead Reports Available", FieldType.CHECKBOX, "has_lead_reports"),

    # Buyer Acknowledgment
    FormField("BuyerReceivedDisclosure", "Buyer Received Disclosure", FieldType.CHECKBOX, "", default=True),
    FormField("BuyerReceivedPamphlet", "Buyer Received EPA Pamphlet", FieldType.CHECKBOX, "", default=True),
    FormField("InspectionPeriodDays", "Inspection Period (days)", FieldType.NUMBER, "lead_inspection_days", default=10),
    FormField("BuyerWaivesInspection", "Buyer Waives Lead Inspection", FieldType.CHECKBOX, "waives_lead_inspection"),

    # Signatures
    FormField("SellerSignature", "Seller Signature", FieldType.SIGNATURE, "", False),
    FormField("SellerDate", "Date", FieldType.DATE, "", False),
    FormField("BuyerSignature", "Buyer Signature", FieldType.SIGNATURE, "", False),
    FormField("BuyerDate", "Date", FieldType.DATE, "", False),
    FormField("AgentSignature", "Agent Signature", FieldType.SIGNATURE, "", False),
    FormField("AgentDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# RADON GAS DISCLOSURE
# =============================================================================

RADON_DISCLOSURE_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),

    # Statutory Language (pre-filled)
    FormField("RadonDisclosureText", "Disclosure Text", FieldType.TEXT, "", default=(
        "RADON GAS: Radon is a naturally occurring radioactive gas that, when it has "
        "accumulated in a building in sufficient quantities, may present health risks to "
        "persons who are exposed to it over time. Levels of radon that exceed federal and "
        "state guidelines have been found in buildings in Florida. Additional information "
        "regarding radon and radon testing may be obtained from your county health department."
    )),

    # Test Results (if available)
    FormField("RadonTestConducted", "Radon Test Conducted", FieldType.CHECKBOX, "has_radon_test"),
    FormField("RadonTestDate", "Test Date", FieldType.DATE, "radon_test_date"),
    FormField("RadonLevel", "Radon Level (pCi/L)", FieldType.NUMBER, "radon_level"),
    FormField("RadonMitigationInstalled", "Mitigation System Installed", FieldType.CHECKBOX, "has_radon_mitigation"),

    # Acknowledgments
    FormField("BuyerAcknowledgment", "Buyer Acknowledgment", FieldType.SIGNATURE, "", False),
    FormField("BuyerDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# PROPERTY TAX DISCLOSURE (F.S. 689.261)
# =============================================================================

PROPERTY_TAX_DISCLOSURE_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),

    # Statutory Language
    FormField("TaxDisclosureText", "Disclosure Text", FieldType.TEXT, "", default=(
        "PROPERTY TAX DISCLOSURE SUMMARY: The buyer should not rely on the seller's current "
        "property taxes as the amount of property taxes that the buyer may be obligated to pay "
        "in the year subsequent to purchase. A change in ownership may reset the assessed "
        "value of the property to full market value, which could result in higher property taxes. "
        "If you have any questions concerning valuation, contact the county property appraiser's "
        "office for information."
    )),

    # Current Tax Information
    FormField("CurrentAnnualTax", "Current Annual Property Tax", FieldType.CURRENCY, "current_property_tax"),
    FormField("CurrentAssessedValue", "Current Assessed Value", FieldType.CURRENCY, "assessed_value"),
    FormField("HomesteadExemption", "Homestead Exemption Applied", FieldType.CHECKBOX, "has_homestead"),
    FormField("OtherExemptions", "Other Exemptions", FieldType.TEXT, "other_exemptions"),

    # Acknowledgments
    FormField("BuyerAcknowledgment", "Buyer Acknowledgment", FieldType.SIGNATURE, "", False),
    FormField("BuyerDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# HOA DISCLOSURE (F.S. 720.401)
# =============================================================================

HOA_DISCLOSURE_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),
    FormField("HOAName", "HOA Name", FieldType.TEXT, "hoa_name", True),
    FormField("HOAContact", "HOA Contact", FieldType.TEXT, "hoa_contact"),
    FormField("HOAPhone", "HOA Phone", FieldType.TEXT, "hoa_phone"),
    FormField("HOAEmail", "HOA Email", FieldType.TEXT, "hoa_email"),
    FormField("HOAManagementCompany", "Management Company", FieldType.TEXT, "hoa_management_company"),

    # Fees and Assessments
    FormField("MonthlyAssessment", "Monthly Assessment", FieldType.CURRENCY, "hoa_monthly_fee"),
    FormField("QuarterlyAssessment", "Quarterly Assessment", FieldType.CURRENCY, "hoa_quarterly_fee"),
    FormField("AnnualAssessment", "Annual Assessment", FieldType.CURRENCY, "hoa_annual_fee"),
    FormField("SpecialAssessment", "Current/Pending Special Assessment", FieldType.CURRENCY, "hoa_special_assessment"),
    FormField("SpecialAssessmentDetails", "Special Assessment Details", FieldType.TEXT, "hoa_special_assessment_details"),
    FormField("TransferFee", "Transfer Fee", FieldType.CURRENCY, "hoa_transfer_fee"),
    FormField("ApplicationFee", "Application Fee", FieldType.CURRENCY, "hoa_application_fee"),

    # Documents to be Provided
    FormField("GoverningDocs", "Governing Documents Provided", FieldType.CHECKBOX, "hoa_docs_provided"),
    FormField("FinancialStatements", "Financial Statements Provided", FieldType.CHECKBOX, "hoa_financials_provided"),
    FormField("RulesAndRegs", "Rules and Regulations Provided", FieldType.CHECKBOX, "hoa_rules_provided"),
    FormField("FAQ", "Frequently Asked Questions Provided", FieldType.CHECKBOX, "hoa_faq_provided"),

    # Buyer Rights
    FormField("CancellationPeriod", "Cancellation Period (days)", FieldType.NUMBER, "", default=3),

    # Acknowledgments
    FormField("BuyerAcknowledgment", "Buyer Acknowledgment", FieldType.SIGNATURE, "", False),
    FormField("BuyerDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# CONDOMINIUM RIDER (F.S. 718.503)
# =============================================================================

CONDO_RIDER_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),
    FormField("UnitNumber", "Unit Number", FieldType.TEXT, "property_address.unit", True),
    FormField("CondoName", "Condominium Name", FieldType.TEXT, "condo_name", True),
    FormField("CondoAssociationName", "Association Name", FieldType.TEXT, "condo_association_name"),

    # Documents Required
    FormField("DeclarationProvided", "Declaration of Condominium", FieldType.CHECKBOX, "condo_declaration_provided"),
    FormField("ArticlesProvided", "Articles of Incorporation", FieldType.CHECKBOX, "condo_articles_provided"),
    FormField("BylawsProvided", "Bylaws", FieldType.CHECKBOX, "condo_bylaws_provided"),
    FormField("RulesProvided", "Rules and Regulations", FieldType.CHECKBOX, "condo_rules_provided"),
    FormField("MostRecentEndOfYearFinancial", "Most Recent Year-End Financial", FieldType.CHECKBOX, "condo_financials_provided"),
    FormField("FrequentlyAskedQuestions", "FAQ Sheet", FieldType.CHECKBOX, "condo_faq_provided"),

    # Fees
    FormField("MonthlyAssessment", "Monthly Assessment", FieldType.CURRENCY, "condo_monthly_fee"),
    FormField("SpecialAssessment", "Special Assessment", FieldType.CURRENCY, "condo_special_assessment"),

    # Buyer Rights
    FormField("RescissionPeriod", "Rescission Period (days)", FieldType.NUMBER, "", default=15),
    FormField("VoidableUntil", "Contract Voidable Until", FieldType.DATE, "condo_voidable_until"),

    # Acknowledgments
    FormField("BuyerAcknowledgment", "Buyer Acknowledgment", FieldType.SIGNATURE, "", False),
    FormField("BuyerDate", "Date", FieldType.DATE, "", False),
]

# =============================================================================
# COMPREHENSIVE RIDER
# =============================================================================

COMPREHENSIVE_RIDER_FIELDS = [
    FormField("PropertyAddress", "Property Address", FieldType.TEXT, "property_address.street", True),
    FormField("EffectiveDate", "Contract Effective Date", FieldType.DATE, "effective_date", True),

    # Property Condition Clauses
    FormField("RepairLimit", "Seller Repair Limit", FieldType.CURRENCY, "repair_limit"),
    FormField("WDOInspection", "WDO Inspection Required", FieldType.CHECKBOX, "requires_wdo_inspection"),
    FormField("SurveyRequired", "Survey Required", FieldType.CHECKBOX, "requires_survey"),

    # Financing Provisions
    FormField("AppraisalContingency", "Appraisal Contingency", FieldType.CHECKBOX, "has_appraisal_contingency"),
    FormField("MinimumAppraisal", "Minimum Appraisal Value", FieldType.CURRENCY, "minimum_appraisal"),

    # Additional Provisions
    FormField("HomeWarranty", "Home Warranty Included", FieldType.CHECKBOX, "includes_home_warranty"),
    FormField("HomeWarrantyCost", "Home Warranty Cost", FieldType.CURRENCY, "home_warranty_cost"),
    FormField("HomeWarrantyPaidBy", "Home Warranty Paid By", FieldType.TEXT, "home_warranty_paid_by"),

    FormField("SellerConcession", "Seller Concession", FieldType.CURRENCY, "seller_concession"),
    FormField("SellerConcessionFor", "Concession Applied To", FieldType.TEXT, "seller_concession_for"),

    # Sale Contingency
    FormField("SaleContingency", "Sale of Buyer's Property Contingency", FieldType.CHECKBOX, "has_sale_contingency"),
    FormField("ContingentPropertyAddress", "Contingent Property Address", FieldType.TEXT, "contingent_property_address"),
    FormField("SaleContingencyDays", "Sale Contingency Period (days)", FieldType.NUMBER, "sale_contingency_days"),

    # Kick-Out Clause
    FormField("KickOutClause", "Kick-Out Clause", FieldType.CHECKBOX, "has_kickout_clause"),
    FormField("KickOutHours", "Kick-Out Period (hours)", FieldType.NUMBER, "kickout_hours", default=72),

    # Acknowledgments
    FormField("BuyerInitials", "Buyer Initials", FieldType.INITIALS, "", False),
    FormField("SellerInitials", "Seller Initials", FieldType.INITIALS, "", False),
]

# =============================================================================
# FORM TEMPLATE REGISTRY
# =============================================================================

FL_FORM_TEMPLATES: dict[str, FormTemplate] = {
    "far_bar_as_is": FormTemplate(
        id="far_bar_as_is",
        name="FAR/BAR AS-IS Residential Contract for Sale and Purchase",
        description="Standard Florida Realtors/Florida Bar 'As-Is' residential purchase contract",
        category=FormCategory.CONTRACT,
        version="Rev. 7 (2024)",
        form_number="ASIS-7",
        pages=12,
        fields=FAR_BAR_AS_IS_FIELDS,
        required_for=["all_residential"],
    ),

    "seller_disclosure": FormTemplate(
        id="seller_disclosure",
        name="Seller's Property Disclosure - Residential",
        description="Florida Realtors Seller's Property Disclosure form covering property condition",
        category=FormCategory.DISCLOSURE,
        version="SPD-1",
        form_number="SPD-1",
        pages=5,
        fields=SELLER_DISCLOSURE_FIELDS,
        required_for=["all_residential"],
    ),

    "lead_paint_disclosure": FormTemplate(
        id="lead_paint_disclosure",
        name="Lead-Based Paint Disclosure",
        description="Federal lead-based paint disclosure required for pre-1978 properties",
        category=FormCategory.DISCLOSURE,
        version="2024",
        form_number="LBP-1",
        pages=2,
        fields=LEAD_PAINT_DISCLOSURE_FIELDS,
        required_for=["pre_1978"],
        source="EPA / HUD",
    ),

    "radon_disclosure": FormTemplate(
        id="radon_disclosure",
        name="Radon Gas Disclosure",
        description="Florida statutory radon gas disclosure (F.S. 404.056)",
        category=FormCategory.DISCLOSURE,
        version="2024",
        form_number="RGD-1",
        pages=1,
        fields=RADON_DISCLOSURE_FIELDS,
        required_for=["all_residential"],
    ),

    "property_tax_disclosure": FormTemplate(
        id="property_tax_disclosure",
        name="Property Tax Disclosure Summary",
        description="Florida statutory property tax disclosure (F.S. 689.261)",
        category=FormCategory.DISCLOSURE,
        version="2024",
        form_number="PTD-1",
        pages=1,
        fields=PROPERTY_TAX_DISCLOSURE_FIELDS,
        required_for=["all_residential"],
    ),

    "hoa_disclosure": FormTemplate(
        id="hoa_disclosure",
        name="HOA Disclosure Summary",
        description="Florida statutory HOA disclosure (F.S. 720.401)",
        category=FormCategory.DISCLOSURE,
        version="2024",
        form_number="HOA-1",
        pages=2,
        fields=HOA_DISCLOSURE_FIELDS,
        required_for=["hoa_property"],
    ),

    "condo_rider": FormTemplate(
        id="condo_rider",
        name="Condominium Rider",
        description="Condominium-specific rider (F.S. 718.503)",
        category=FormCategory.RIDER,
        version="CR-7_A (2024)",
        form_number="CR-7_A",
        pages=2,
        fields=CONDO_RIDER_FIELDS,
        required_for=["condominium"],
    ),

    "comprehensive_rider": FormTemplate(
        id="comprehensive_rider",
        name="Comprehensive Rider",
        description="Additional terms and conditions rider",
        category=FormCategory.RIDER,
        version="2024",
        form_number="CR-6",
        pages=3,
        fields=COMPREHENSIVE_RIDER_FIELDS,
        required_for=[],  # Optional
    ),
}


def get_template(template_id: str) -> FormTemplate | None:
    """Get a form template by ID."""
    return FL_FORM_TEMPLATES.get(template_id)


def get_templates_by_category(category: FormCategory) -> list[FormTemplate]:
    """Get all templates in a category."""
    return [t for t in FL_FORM_TEMPLATES.values() if t.category == category]


def get_required_templates(
    *,
    is_residential: bool = True,
    year_built: int | None = None,
    is_hoa: bool = False,
    is_condo: bool = False,
) -> list[FormTemplate]:
    """Get list of required form templates based on transaction characteristics."""
    required = []

    for template in FL_FORM_TEMPLATES.values():
        for condition in template.required_for:
            if condition == "all_residential" and is_residential:
                required.append(template)
                break
            elif condition == "pre_1978" and year_built and year_built < 1978:
                required.append(template)
                break
            elif condition == "hoa_property" and is_hoa:
                required.append(template)
                break
            elif condition == "condominium" and is_condo:
                required.append(template)
                break

    return required
