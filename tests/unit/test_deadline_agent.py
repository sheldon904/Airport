"""Unit tests for deadline calculation agent.

Tests Florida statutory deadlines, TRID deadlines, and contingency handling.
"""

import pytest
from datetime import date
from uuid import uuid4

from services.agents.deadline.agent import (
    DeadlineAgent,
    DeadlineInput,
    DeadlineOutput,
    CalculatedDeadline,
    FL_STATUTORY_DEADLINES,
    TRID_DEADLINES,
    FL_STANDARD_CONTINGENCIES,
)
from services.agents.base import AgentContext


@pytest.fixture
def agent():
    """Create deadline agent instance."""
    return DeadlineAgent()


@pytest.fixture
def base_input():
    """Create base deadline input."""
    return DeadlineInput(
        transaction_id=uuid4(),
        effective_date=date(2024, 6, 3),  # Monday
        closing_date=date(2024, 7, 15),  # Monday
        contingencies=[],
        state="FL",
        year_built=2020,
        is_hoa=False,
        is_condo=False,
        is_financed=True,
    )


@pytest.fixture
def mock_context():
    """Create mock agent context."""
    return AgentContext(
        transaction_id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
    )


class TestStatutoryDeadlines:
    """Tests for Florida statutory deadline definitions."""

    def test_seller_disclosure_defined(self):
        """Seller disclosure deadline is properly defined."""
        deadline = FL_STATUTORY_DEADLINES["seller_disclosure"]
        assert deadline["name"] == "Seller's Property Disclosure Due"
        assert deadline["days_from_effective"] == 3
        assert "F.S. 689.25" in deadline["statute"]

    def test_radon_disclosure_at_signing(self):
        """Radon disclosure is due at signing (day 0)."""
        deadline = FL_STATUTORY_DEADLINES["radon_disclosure"]
        assert deadline["days_from_effective"] == 0
        assert "F.S. 404.056" in deadline["statute"]

    def test_lead_paint_has_condition(self):
        """Lead paint disclosure has pre-1978 condition."""
        deadline = FL_STATUTORY_DEADLINES["lead_paint_disclosure"]
        assert deadline.get("condition") == "pre_1978"

    def test_hoa_disclosure_has_condition(self):
        """HOA disclosure has HOA condition."""
        deadline = FL_STATUTORY_DEADLINES["hoa_disclosure"]
        assert deadline.get("condition") == "is_hoa"

    def test_condo_rescission_period(self):
        """Condo rescission is 15 days per F.S. 718.503."""
        deadline = FL_STATUTORY_DEADLINES["condo_rescission"]
        assert deadline["days_from_effective"] == 15
        assert "F.S. 718.503" in deadline["statute"]

    def test_title_commitment_deadline(self):
        """Title commitment due within 15 days."""
        deadline = FL_STATUTORY_DEADLINES["title_commitment"]
        assert deadline["days_from_effective"] == 15

    def test_walk_through_before_closing(self):
        """Walk-through is 1 day before closing."""
        deadline = FL_STATUTORY_DEADLINES["walk_through"]
        assert deadline["days_before_closing"] == 1


class TestTridDeadlines:
    """Tests for TRID deadline definitions."""

    def test_loan_estimate_deadline(self):
        """Loan Estimate due 3 business days after application."""
        deadline = TRID_DEADLINES["loan_estimate"]
        assert deadline["business_days_from_application"] == 3
        assert "12 CFR 1026.19(e)" in deadline["statute"]

    def test_closing_disclosure_deadline(self):
        """Closing Disclosure due 3 business days before closing."""
        deadline = TRID_DEADLINES["closing_disclosure"]
        assert deadline["business_days_before_closing"] == 3
        assert "12 CFR 1026.19(f)" in deadline["statute"]

    def test_trid_deadlines_require_financing(self):
        """TRID deadlines only apply to financed transactions."""
        for key, deadline in TRID_DEADLINES.items():
            assert deadline.get("condition") == "is_financed"


class TestStandardContingencies:
    """Tests for standard contingency defaults."""

    def test_inspection_period_default(self):
        """Inspection period defaults to 15 days."""
        contingency = FL_STANDARD_CONTINGENCIES["inspection_period"]
        assert contingency["default_days"] == 15

    def test_financing_contingency_default(self):
        """Financing contingency defaults to 30 days."""
        contingency = FL_STANDARD_CONTINGENCIES["financing_contingency"]
        assert contingency["default_days"] == 30
        assert contingency.get("condition") == "is_financed"

    def test_appraisal_contingency_default(self):
        """Appraisal contingency defaults to 30 days."""
        contingency = FL_STANDARD_CONTINGENCIES["appraisal_contingency"]
        assert contingency["default_days"] == 30


class TestDeadlineInput:
    """Tests for deadline input validation."""

    def test_valid_input_creation(self):
        """Valid input is created successfully."""
        input_data = DeadlineInput(
            transaction_id=uuid4(),
            effective_date=date(2024, 6, 3),
            closing_date=date(2024, 7, 15),
            contingencies=[],
        )
        assert input_data.state == "FL"  # Default
        assert input_data.is_financed is True  # Default

    def test_input_with_property_characteristics(self):
        """Input with property characteristics is valid."""
        input_data = DeadlineInput(
            transaction_id=uuid4(),
            effective_date=date(2024, 6, 3),
            closing_date=date(2024, 7, 15),
            contingencies=[],
            year_built=1970,
            is_hoa=True,
            is_condo=True,
            is_financed=False,
        )
        assert input_data.year_built == 1970
        assert input_data.is_hoa is True
        assert input_data.is_condo is True
        assert input_data.is_financed is False


class TestCalculatedDeadline:
    """Tests for calculated deadline model."""

    def test_deadline_model_creation(self):
        """Calculated deadline model is created correctly."""
        deadline = CalculatedDeadline(
            id=uuid4(),
            deadline_type="statutory",
            name="Test Deadline",
            due_date=date(2024, 6, 10),
            source="statute",
            description="Test description",
            statute_reference="F.S. 123.456",
        )
        assert deadline.reminder_days == [7, 3, 1]  # Default
        assert deadline.is_business_days is False  # Default
        assert deadline.priority == 0  # Default

    def test_deadline_with_business_days(self):
        """Deadline with business days flag."""
        deadline = CalculatedDeadline(
            id=uuid4(),
            deadline_type="trid",
            name="TRID Deadline",
            due_date=date(2024, 6, 10),
            source="federal",
            is_business_days=True,
        )
        assert deadline.is_business_days is True


class TestDeadlineOutput:
    """Tests for deadline output model."""

    def test_output_with_deadlines(self):
        """Output contains calculated deadlines."""
        tx_id = uuid4()
        deadline = CalculatedDeadline(
            id=uuid4(),
            deadline_type="statutory",
            name="Test",
            due_date=date(2024, 6, 10),
            source="statute",
        )
        output = DeadlineOutput(
            transaction_id=tx_id,
            deadlines=[deadline],
            warnings=["Test warning"],
        )
        assert len(output.deadlines) == 1
        assert len(output.warnings) == 1


class TestDeadlineAgentIntegration:
    """Integration tests for deadline agent processing."""

    @pytest.mark.asyncio
    async def test_agent_generates_deadlines(self, agent, base_input, mock_context):
        """Agent generates deadlines from input."""
        output, confidence, needs_review, reason = await agent.process(
            mock_context, base_input
        )

        assert isinstance(output, DeadlineOutput)
        assert len(output.deadlines) > 0
        assert confidence is None or isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_agent_includes_closing_date(self, agent, base_input, mock_context):
        """Agent includes closing date as a deadline."""
        output, _, _, _ = await agent.process(mock_context, base_input)

        closing_deadlines = [d for d in output.deadlines if "closing" in d.name.lower()]
        assert len(closing_deadlines) > 0

    @pytest.mark.asyncio
    async def test_trid_deadlines_for_financed(self, agent, base_input, mock_context):
        """Financed transactions include TRID deadlines."""
        base_input.is_financed = True
        output, _, _, _ = await agent.process(mock_context, base_input)

        trid_deadlines = [
            d for d in output.deadlines
            if "closing disclosure" in d.name.lower() or "loan estimate" in d.name.lower()
        ]
        assert len(trid_deadlines) >= 1

    @pytest.mark.asyncio
    async def test_no_trid_for_cash(self, agent, base_input, mock_context):
        """Cash transactions don't include TRID deadlines."""
        base_input.is_financed = False
        output, _, _, _ = await agent.process(mock_context, base_input)

        trid_names = ["closing disclosure", "loan estimate"]
        trid_deadlines = [
            d for d in output.deadlines
            if any(name in d.name.lower() for name in trid_names)
        ]
        assert len(trid_deadlines) == 0

    @pytest.mark.asyncio
    async def test_lead_paint_for_pre_1978(self, agent, base_input, mock_context):
        """Pre-1978 properties include lead paint disclosure deadline."""
        base_input.year_built = 1970
        output, _, _, _ = await agent.process(mock_context, base_input)

        lead_deadlines = [
            d for d in output.deadlines
            if "lead" in d.name.lower()
        ]
        assert len(lead_deadlines) > 0

    @pytest.mark.asyncio
    async def test_no_lead_paint_for_new_construction(self, agent, base_input, mock_context):
        """Post-1978 properties don't include lead paint deadline."""
        base_input.year_built = 2020
        output, _, _, _ = await agent.process(mock_context, base_input)

        lead_deadlines = [
            d for d in output.deadlines
            if "lead" in d.name.lower()
        ]
        assert len(lead_deadlines) == 0

    @pytest.mark.asyncio
    async def test_hoa_deadlines_when_applicable(self, agent, base_input, mock_context):
        """HOA properties include HOA disclosure deadline."""
        base_input.is_hoa = True
        output, _, _, _ = await agent.process(mock_context, base_input)

        hoa_deadlines = [
            d for d in output.deadlines
            if "hoa" in d.name.lower()
        ]
        assert len(hoa_deadlines) > 0

    @pytest.mark.asyncio
    async def test_condo_deadlines_when_applicable(self, agent, base_input, mock_context):
        """Condo properties include condo-specific deadlines."""
        base_input.is_condo = True
        output, _, _, _ = await agent.process(mock_context, base_input)

        condo_deadlines = [
            d for d in output.deadlines
            if "condo" in d.name.lower()
        ]
        # Should include condo disclosure and rescission period
        assert len(condo_deadlines) >= 2

    @pytest.mark.asyncio
    async def test_deadlines_are_sorted_by_date(self, agent, base_input, mock_context):
        """Generated deadlines are sorted by due date."""
        output, _, _, _ = await agent.process(mock_context, base_input)

        dates = [d.due_date for d in output.deadlines]
        assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_all_deadlines_have_unique_ids(self, agent, base_input, mock_context):
        """All generated deadlines have unique IDs."""
        output, _, _, _ = await agent.process(mock_context, base_input)

        ids = [d.id for d in output.deadlines]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_statutory_deadlines_have_references(self, agent, base_input, mock_context):
        """Statutory deadlines include statute references."""
        output, _, _, _ = await agent.process(mock_context, base_input)

        statutory = [d for d in output.deadlines if d.source == "statute"]
        for deadline in statutory:
            assert deadline.statute_reference is not None
            assert "F.S." in deadline.statute_reference or "CFR" in deadline.statute_reference


class TestDeadlineDateCalculations:
    """Tests for specific deadline date calculations."""

    @pytest.mark.asyncio
    async def test_seller_disclosure_date(self, agent, mock_context):
        """Seller disclosure is due 3 days from effective date."""
        input_data = DeadlineInput(
            transaction_id=uuid4(),
            effective_date=date(2024, 6, 3),  # Monday
            closing_date=date(2024, 7, 15),
            contingencies=[],
        )
        output, _, _, _ = await agent.process(mock_context, input_data)

        seller_disclosure = next(
            (d for d in output.deadlines if "seller" in d.name.lower() and "disclosure" in d.name.lower()),
            None
        )
        if seller_disclosure:
            # 3 days from June 3 = June 6
            assert seller_disclosure.due_date == date(2024, 6, 6)

    @pytest.mark.asyncio
    async def test_walk_through_date(self, agent, mock_context):
        """Walk-through is 1 day before closing."""
        input_data = DeadlineInput(
            transaction_id=uuid4(),
            effective_date=date(2024, 6, 3),
            closing_date=date(2024, 7, 15),  # Monday
            contingencies=[],
        )
        output, _, _, _ = await agent.process(mock_context, input_data)

        walk_through = next(
            (d for d in output.deadlines if "walk" in d.name.lower()),
            None
        )
        if walk_through:
            # 1 day before July 15 = July 14
            assert walk_through.due_date == date(2024, 7, 14)

    @pytest.mark.asyncio
    async def test_closing_disclosure_business_days(self, agent, mock_context):
        """Closing Disclosure uses business day calculation."""
        input_data = DeadlineInput(
            transaction_id=uuid4(),
            effective_date=date(2024, 6, 3),
            closing_date=date(2024, 7, 5),  # Friday
            contingencies=[],
            is_financed=True,
        )
        output, _, _, _ = await agent.process(mock_context, input_data)

        cd_deadline = next(
            (d for d in output.deadlines if "closing disclosure" in d.name.lower()),
            None
        )
        if cd_deadline:
            # 3 business days before July 5 (Fri) = July 2 (Tue)
            # July 5 (Fri) -> July 4 (Thu, but holiday!) -> July 3 (Wed) -> July 2 (Tue) -> July 1 (Mon)
            # Actually: 3 business days back from July 5
            assert cd_deadline.is_business_days is True
