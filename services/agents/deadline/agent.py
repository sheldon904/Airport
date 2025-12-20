"""Deadline calculation agent implementation."""

from datetime import date, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel

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


class CalculatedDeadline(BaseModel):
    """A calculated deadline."""

    id: UUID
    deadline_type: str
    name: str
    due_date: date
    source: str  # "contract", "statute", "custom"
    description: str | None = None
    reminder_days: list[int] = [7, 3, 1]


class DeadlineOutput(BaseModel):
    """Output from deadline calculation."""

    transaction_id: UUID
    deadlines: list[CalculatedDeadline]
    warnings: list[str] = []


# === Florida-Specific Rules ===

FL_STATUTORY_DEADLINES = {
    # These are example statutory requirements - would need legal review
    "seller_disclosure": {
        "name": "Seller Disclosure Due",
        "days_from_effective": 3,
        "description": "Seller must provide property disclosures",
    },
    "hoa_disclosure": {
        "name": "HOA Documents Due",
        "days_from_effective": 3,
        "description": "HOA documents must be provided if applicable",
    },
}

FL_STANDARD_CONTINGENCIES = {
    "inspection_period": {
        "default_days": 15,
        "name": "Inspection Period Ends",
        "description": "Buyer inspection contingency expires",
    },
    "financing_contingency": {
        "default_days": 30,
        "name": "Financing Contingency Expires",
        "description": "Loan approval deadline",
    },
    "appraisal_contingency": {
        "default_days": 30,
        "name": "Appraisal Contingency Expires",
        "description": "Appraisal must be completed and accepted",
    },
}


# === Agent Implementation ===


class DeadlineAgent(BaseAgent[DeadlineInput, DeadlineOutput]):
    """
    Agent for calculating transaction deadlines from contract data.

    Generates a compliance timeline based on:
    1. Contract-specified dates and contingencies
    2. State statutory requirements
    3. Standard real estate practices

    Compliance Notes:
    - Calculates dates based on contract terms and FL statutes
    - Does NOT make recommendations about extending or waiving
    - Flags potential conflicts for human review
    """

    name = "deadline"
    version = "0.1.0"

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

        # Add effective date marker
        deadlines.append(
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.EFFECTIVE_DATE,
                name="Contract Effective Date",
                due_date=effective,
                source="contract",
                description="Contract becomes binding",
            )
        )

        # Add closing date
        deadlines.append(
            CalculatedDeadline(
                id=uuid4(),
                deadline_type=DeadlineType.CLOSING_DATE,
                name="Closing Date",
                due_date=closing,
                source="contract",
                description="Transaction must close by this date",
                reminder_days=[14, 7, 3, 1],
            )
        )

        # Calculate statutory deadlines
        for key, rule in FL_STATUTORY_DEADLINES.items():
            due = effective + timedelta(days=rule["days_from_effective"])
            deadlines.append(
                CalculatedDeadline(
                    id=uuid4(),
                    deadline_type=DeadlineType.DISCLOSURE_DEADLINE,
                    name=rule["name"],
                    due_date=due,
                    source="statute",
                    description=rule["description"],
                )
            )

        # Process contract contingencies
        for contingency in input_data.contingencies:
            deadline = self._process_contingency(contingency, effective, closing)
            if deadline:
                deadlines.append(deadline)
            else:
                warnings.append(f"Could not parse contingency: {contingency.get('type', 'unknown')}")

        # Check for deadline conflicts
        for deadline in deadlines:
            if deadline.due_date > closing and deadline.deadline_type != DeadlineType.CLOSING_DATE:
                warnings.append(
                    f"Deadline '{deadline.name}' ({deadline.due_date}) is after closing ({closing})"
                )

        # Sort by due date
        deadlines.sort(key=lambda d: d.due_date)

        # Determine if review needed
        needs_review = len(warnings) > 0
        review_reason = "; ".join(warnings) if warnings else None

        output = DeadlineOutput(
            transaction_id=input_data.transaction_id,
            deadlines=deadlines,
            warnings=warnings,
        )

        # High confidence if no warnings
        confidence = 0.95 if not warnings else 0.75

        return (output, confidence, needs_review, review_reason)

    def _process_contingency(
        self,
        contingency: dict,
        effective: date,
        closing: date,
    ) -> CalculatedDeadline | None:
        """Process a single contingency into a deadline."""
        contingency_type = contingency.get("contingency_type", "").lower()

        # If specific date provided, use it
        if contingency.get("deadline_date"):
            return CalculatedDeadline(
                id=uuid4(),
                deadline_type=self._map_contingency_type(contingency_type),
                name=contingency.get("description", f"{contingency_type} deadline"),
                due_date=contingency["deadline_date"],
                source="contract",
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
            )

        # Fall back to standard defaults
        if contingency_type in FL_STANDARD_CONTINGENCIES:
            rule = FL_STANDARD_CONTINGENCIES[contingency_type]
            due = effective + timedelta(days=rule["default_days"])
            return CalculatedDeadline(
                id=uuid4(),
                deadline_type=self._map_contingency_type(contingency_type),
                name=rule["name"],
                due_date=due,
                source="default",
                description=rule["description"],
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
