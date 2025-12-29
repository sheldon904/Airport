"""Deadline calculation agent implementation.

This agent calculates all transaction deadlines based on:
1. Contract-specified dates and contingencies
2. Florida statutory requirements (F.S.)
3. Federal requirements (TRID/RESPA)
4. Standard real estate practices (FAR/BAR contract)
"""

from datetime import date, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel

from packages.compliance.business_days import (
    add_business_days,
    subtract_business_days,
    trid_closing_disclosure_deadline,
)
from packages.core.models import DeadlineType
from services.agents.base import AgentContext, BaseAgent


# === Input/Output Models ===


class DeadlineInput(BaseModel):
    """Input for deadline calculation."""

    transaction_id: UUID
    effective_date: date
    closing_date: date
    contingencies: list[dict]  # From extraction
    state: str = "FL"

    # Property characteristics for conditional deadlines
    year_built: int | None = None
    is_hoa: bool = False
    is_condo: bool = False
    is_financed: bool = True


class CalculatedDeadline(BaseModel):
    """A calculated deadline."""

    id: UUID
    deadline_type: str
    name: str
    due_date: date
    source: str  # "contract", "statute", "federal", "default"
    description: str | None = None
    reminder_days: list[int] = [7, 3, 1]
    statute_reference: str | None = None  # e.g., "F.S. 720.401"
    is_business_days: bool = False  # True if calculated using business days
    priority: int = 0  # Higher = more important


class DeadlineOutput(BaseModel):
    """Output from deadline calculation."""

    transaction_id: UUID
    deadlines: list[CalculatedDeadline]
    warnings: list[str] = []


# === Florida Statutory Deadlines ===
# Reference: Florida Statutes, FAR/BAR Contract, Federal TRID

FL_STATUTORY_DEADLINES = {
    # ===== SELLER DISCLOSURES =====
    "seller_disclosure": {
        "name": "Seller's Property Disclosure Due",
        "days_from_effective": 3,
        "description": "Seller must provide property disclosure statement",
        "statute": "F.S. 689.25",
        "priority": 10,
    },
    "radon_disclosure": {
        "name": "Radon Gas Disclosure Due",
        "days_from_effective": 0,  # At signing
        "description": "Florida radon gas disclosure must be provided",
        "statute": "F.S. 404.056",
        "priority": 9,
    },
    "property_tax_disclosure": {
        "name": "Property Tax Disclosure Due",
        "days_from_effective": 0,  # At signing
        "description": "Property tax disclosure required per Florida law",
        "statute": "F.S. 689.261",
        "priority": 8,
    },
    "energy_disclosure": {
        "name": "Energy Efficiency Disclosure Due",
        "days_from_effective": 0,  # At signing
        "description": "Florida Building Energy-Efficiency Rating disclosure",
        "statute": "F.S. 553.996",
        "priority": 7,
    },

    # ===== CONDITIONAL DISCLOSURES =====
    "lead_paint_disclosure": {
        "name": "Lead-Based Paint Disclosure Due",
        "days_from_effective": 10,
        "description": "Lead-based paint disclosure for pre-1978 properties",
        "statute": "42 U.S.C. 4852d",
        "condition": "pre_1978",
        "priority": 10,
    },
    "hoa_disclosure": {
        "name": "HOA Disclosure Documents Due",
        "days_from_effective": 3,
        "description": "Homeowner's association disclosure documents",
        "statute": "F.S. 720.401",
        "condition": "is_hoa",
        "priority": 10,
    },
    "condo_disclosure": {
        "name": "Condo Association Documents Due",
        "days_from_effective": 3,
        "description": "Condominium association disclosure documents",
        "statute": "F.S. 718.503",
        "condition": "is_condo",
        "priority": 10,
    },
    "condo_rescission": {
        "name": "Condo Buyer Rescission Period Ends",
        "days_from_effective": 15,
        "description": "Buyer's 15-day right to cancel condo purchase",
        "statute": "F.S. 718.503",
        "condition": "is_condo",
        "priority": 10,
    },

    # ===== FINANCIAL DEADLINES =====
    "earnest_money_deposit": {
        "name": "Earnest Money Deposit Due",
        "days_from_effective": 3,
        "description": "Initial earnest money deposit must be received",
        "statute": "FAR/BAR Contract",
        "priority": 10,
    },
    "additional_deposit": {
        "name": "Additional Deposit Due",
        "days_from_effective": 10,  # Typical FAR/BAR default
        "description": "Additional earnest money deposit if specified",
        "statute": "FAR/BAR Contract",
        "priority": 8,
    },

    # ===== TITLE DEADLINES =====
    "title_commitment": {
        "name": "Title Commitment Due",
        "days_from_effective": 15,
        "description": "Title commitment must be provided to buyer",
        "statute": "F.S. 689.01",
        "priority": 9,
    },
    "title_examination": {
        "name": "Title Examination Period Ends",
        "days_from_effective": 21,
        "description": "Buyer must complete title review and raise objections",
        "statute": "F.S. 689.01",
        "priority": 8,
    },
    "title_defect_cure": {
        "name": "Title Defect Cure Deadline",
        "days_from_effective": 30,
        "description": "Seller must cure title defects within this period",
        "statute": "FAR/BAR Contract",
        "priority": 7,
    },

    # ===== CLOSING PREPARATION =====
    "survey_delivery": {
        "name": "Survey Delivery Due",
        "days_before_closing": 5,
        "description": "Property survey must be delivered before closing",
        "statute": "FAR/BAR Contract",
        "priority": 6,
    },
    "walk_through": {
        "name": "Final Walk-Through",
        "days_before_closing": 1,
        "description": "Buyer's final property inspection before closing",
        "statute": "FAR/BAR Contract",
        "priority": 8,
    },
}

# Federal TRID deadlines (business day calculations)
TRID_DEADLINES = {
    "loan_estimate": {
        "name": "Loan Estimate Delivery Due",
        "business_days_from_application": 3,
        "description": "Lender must provide Loan Estimate within 3 business days",
        "statute": "12 CFR 1026.19(e)",
        "condition": "is_financed",
        "priority": 10,
    },
    "closing_disclosure": {
        "name": "Closing Disclosure Must Be Received",
        "business_days_before_closing": 3,
        "description": "Buyer must receive Closing Disclosure 3 business days before closing",
        "statute": "12 CFR 1026.19(f)",
        "condition": "is_financed",
        "priority": 10,
    },
}

# Standard contingency defaults (FAR/BAR contract typical values)
FL_STANDARD_CONTINGENCIES = {
    "inspection_period": {
        "default_days": 15,
        "name": "Inspection Period Ends",
        "description": "Buyer inspection contingency expires",
        "priority": 10,
    },
    "financing_contingency": {
        "default_days": 30,
        "name": "Financing Contingency Expires",
        "description": "Loan approval deadline",
        "condition": "is_financed",
        "priority": 10,
    },
    "appraisal_contingency": {
        "default_days": 30,
        "name": "Appraisal Contingency Expires",
        "description": "Appraisal must be completed and accepted",
        "condition": "is_financed",
        "priority": 9,
    },
    "sale_contingency": {
        "default_days": 45,
        "name": "Sale Contingency Expires",
        "description": "Buyer's existing home must be under contract",
        "priority": 8,
    },
}


# === Agent Implementation ===


class DeadlineAgent(BaseAgent[DeadlineInput, DeadlineOutput]):
    """
    Agent for calculating transaction deadlines from contract data.

    Generates a comprehensive compliance timeline based on:
    1. Contract-specified dates and contingencies
    2. Florida statutory requirements (F.S.)
    3. Federal TRID/RESPA requirements
    4. Standard FAR/BAR contract provisions

    Compliance Notes:
    - Calculates dates based on contract terms and FL/Federal statutes
    - Uses business day calculations where required (TRID)
    - Applies conditional deadlines based on property characteristics
    - Does NOT make recommendations about extending or waiving
    - Flags potential conflicts for human review
    """

    name = "deadline"
    version = "0.2.0"

    async def process(
        self,
        context: AgentContext,
        input_data: DeadlineInput,
    ) -> tuple[DeadlineOutput, float | None, bool, str | None]:
        """
        Calculate all deadlines for a transaction.

        Returns:
            tuple: (deadlines, confidence, needs_review, review_reason)
        """
        deadlines: list[CalculatedDeadline] = []
        warnings: list[str] = []

        effective = input_data.effective_date
        closing = input_data.closing_date

        # 1. Add contract milestone dates
        deadlines.extend(self._add_contract_dates(effective, closing))

        # 2. Add Florida statutory deadlines
        deadlines.extend(
            self._add_statutory_deadlines(
                effective,
                closing,
                year_built=input_data.year_built,
                is_hoa=input_data.is_hoa,
                is_condo=input_data.is_condo,
                is_financed=input_data.is_financed,
            )
        )

        # 3. Add TRID deadlines (business days)
        if input_data.is_financed:
            deadlines.extend(self._add_trid_deadlines(effective, closing))

        # 4. Process contract-specified contingencies
        for contingency in input_data.contingencies:
            deadline = self._process_contingency(
                contingency, effective, closing, input_data.is_financed
            )
            if deadline:
                deadlines.append(deadline)
            else:
                warnings.append(
                    f"Could not parse contingency: {contingency.get('contingency_type', 'unknown')}"
                )

        # 5. Check for deadline conflicts
        for deadline in deadlines:
            if (
                deadline.due_date > closing
                and deadline.deadline_type != DeadlineType.CLOSING_DATE
            ):
                warnings.append(
                    f"Deadline '{deadline.name}' ({deadline.due_date}) is after closing ({closing})"
                )

        # 6. Check for impossibly tight timelines
        days_to_close = (closing - effective).days
        if days_to_close < 21:
            warnings.append(
                f"Very short timeline: only {days_to_close} days from effective to closing"
            )

        # 7. Sort by due date, then priority
        deadlines.sort(key=lambda d: (d.due_date, -d.priority))

        # Determine if review needed
        needs_review = len(warnings) > 0
        review_reason = "; ".join(warnings) if warnings else None

        output = DeadlineOutput(
            transaction_id=input_data.transaction_id,
            deadlines=deadlines,
            warnings=warnings,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(deadlines, warnings)

        return (output, confidence, needs_review, review_reason)

    def _add_contract_dates(
        self, effective: date, closing: date
    ) -> list[CalculatedDeadline]:
        """Add contract milestone dates."""
        return [
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.EFFECTIVE_DATE,
                name="Contract Effective Date",
                due_date=effective,
                source="contract",
                description="Contract becomes binding",
                priority=10,
            ),
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.CLOSING_DATE,
                name="Closing Date",
                due_date=closing,
                source="contract",
                description="Transaction must close by this date",
                reminder_days=[14, 7, 3, 1],
                priority=10,
            ),
        ]

    def _add_statutory_deadlines(
        self,
        effective: date,
        closing: date,
        year_built: int | None,
        is_hoa: bool,
        is_condo: bool,
        is_financed: bool,
    ) -> list[CalculatedDeadline]:
        """Add Florida statutory deadlines."""
        deadlines = []

        for key, rule in FL_STATUTORY_DEADLINES.items():
            # Check conditions
            condition = rule.get("condition")
            if condition:
                if condition == "pre_1978" and year_built and year_built >= 1978:
                    continue
                if condition == "is_hoa" and not is_hoa:
                    continue
                if condition == "is_condo" and not is_condo:
                    continue
                if condition == "is_financed" and not is_financed:
                    continue

            # Calculate due date
            if "days_from_effective" in rule:
                due = effective + timedelta(days=rule["days_from_effective"])
            elif "days_before_closing" in rule:
                due = closing - timedelta(days=rule["days_before_closing"])
            else:
                continue

            deadlines.append(
                CalculatedDeadline(
                    id=uuid4(),
                    deadline_type=DeadlineType.DISCLOSURE_DEADLINE,
                    name=rule["name"],
                    due_date=due,
                    source="statute",
                    description=rule["description"],
                    statute_reference=rule.get("statute"),
                    priority=rule.get("priority", 5),
                )
            )

        return deadlines

    def _add_trid_deadlines(
        self, effective: date, closing: date
    ) -> list[CalculatedDeadline]:
        """Add TRID/RESPA federal deadlines (business day calculations)."""
        deadlines = []

        # Closing Disclosure - 3 business days before closing
        cd_deadline = trid_closing_disclosure_deadline(closing)
        deadlines.append(
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.DISCLOSURE_DEADLINE,
                name="Closing Disclosure Must Be Received",
                due_date=cd_deadline,
                source="federal",
                description="Buyer must receive Closing Disclosure at least 3 business days before closing",
                statute_reference="12 CFR 1026.19(f)",
                is_business_days=True,
                priority=10,
                reminder_days=[7, 5, 3],
            )
        )

        # Loan Estimate - 3 business days from application
        # Note: This is from application date, not effective date
        # We'll use effective date as proxy since we may not have application date
        le_deadline = add_business_days(effective, 3)
        deadlines.append(
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.DISCLOSURE_DEADLINE,
                name="Loan Estimate Due (from application)",
                due_date=le_deadline,
                source="federal",
                description="Lender must provide Loan Estimate within 3 business days of application",
                statute_reference="12 CFR 1026.19(e)",
                is_business_days=True,
                priority=9,
            )
        )

        return deadlines

    def _process_contingency(
        self,
        contingency: dict,
        effective: date,
        closing: date,
        is_financed: bool,
    ) -> CalculatedDeadline | None:
        """Process a single contingency into a deadline."""
        contingency_type = contingency.get("contingency_type", "").lower()

        # Check if contingency is waived
        if contingency.get("waived", False):
            return None

        # If specific date provided, use it
        if contingency.get("deadline_date"):
            return CalculatedDeadline(
                id=uuid4(),
                deadline_type=self._map_contingency_type(contingency_type),
                name=contingency.get("description", f"{contingency_type} deadline"),
                due_date=contingency["deadline_date"],
                source="contract",
                priority=8,
            )

        # If days from effective provided
        if contingency.get("days_from_effective"):
            due = effective + timedelta(days=contingency["days_from_effective"])
            return CalculatedDeadline(
                id=uuid4(),
                deadline_type=self._map_contingency_type(contingency_type),
                name=contingency.get("description", f"{contingency_type} deadline"),
                due_date=due,
                source="contract",
                priority=8,
            )

        # Fall back to standard defaults
        if contingency_type in FL_STANDARD_CONTINGENCIES:
            rule = FL_STANDARD_CONTINGENCIES[contingency_type]

            # Check condition
            if rule.get("condition") == "is_financed" and not is_financed:
                return None

            due = effective + timedelta(days=rule["default_days"])
            return CalculatedDeadline(
                id=uuid4(),
                deadline_type=self._map_contingency_type(contingency_type),
                name=rule["name"],
                due_date=due,
                source="default",
                description=rule["description"],
                priority=rule.get("priority", 5),
            )

        return None

    def _map_contingency_type(self, contingency_type: str) -> str:
        """Map contingency type string to DeadlineType."""
        mapping = {
            "inspection": DeadlineType.INSPECTION_PERIOD,
            "inspection_period": DeadlineType.INSPECTION_PERIOD,
            "financing": DeadlineType.FINANCING_CONTINGENCY,
            "financing_contingency": DeadlineType.FINANCING_CONTINGENCY,
            "appraisal": DeadlineType.APPRAISAL_CONTINGENCY,
            "appraisal_contingency": DeadlineType.APPRAISAL_CONTINGENCY,
            "sale": DeadlineType.SALE_CONTINGENCY,
            "sale_contingency": DeadlineType.SALE_CONTINGENCY,
        }
        return mapping.get(contingency_type, DeadlineType.CUSTOM)

    def _calculate_confidence(
        self, deadlines: list[CalculatedDeadline], warnings: list[str]
    ) -> float:
        """Calculate confidence score for deadline calculation."""
        # Start with high confidence
        confidence = 0.95

        # Reduce for warnings
        confidence -= len(warnings) * 0.05

        # Reduce if we had to use many defaults
        default_count = sum(1 for d in deadlines if d.source == "default")
        if default_count > 3:
            confidence -= 0.05

        # Ensure within bounds
        return max(0.5, min(1.0, confidence))
