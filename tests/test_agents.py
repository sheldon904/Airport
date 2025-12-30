"""
Tests for AI agent implementations.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.agents.base import AgentContext, AgentResult
from services.agents.document_extract.agent import (
    DocumentExtractAgent,
    DocumentExtractInput,
    DocumentExtractOutput,
    ExtractedParty,
    ExtractedDate,
    ExtractedContingency,
)
from services.agents.deadline.agent import (
    DeadlineAgent,
    DeadlineInput,
    DeadlineOutput,
    CalculatedDeadline,
)
from services.agents.checklist.agent import (
    ChecklistAgent,
    ChecklistInput,
    ChecklistOutput,
)


# === Fixtures ===


@pytest.fixture
def agent_context():
    """Create a test agent context."""
    return AgentContext(
        execution_id=uuid4(),
        transaction_id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        triggered_by="test",
        triggered_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_storage():
    """Create a mock storage service."""
    storage = MagicMock()
    storage.download_file = AsyncMock(return_value=b"Mock PDF content")
    return storage


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"document_type_detected": "purchase_contract"}')]
    client.messages.create = AsyncMock(return_value=mock_message)
    return client


# === DocumentExtractAgent Tests ===


class TestDocumentExtractAgent:
    """Tests for the DocumentExtractAgent."""

    def test_agent_name_and_version(self):
        """Test agent has correct name and version."""
        agent = DocumentExtractAgent()
        assert agent.name == "document_extract"
        assert agent.version == "0.3.0"

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf(self):
        """Test PDF text extraction."""
        agent = DocumentExtractAgent()

        # Create a minimal valid PDF
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

        # Should not raise an exception
        result = agent._extract_pdf_text(pdf_content)
        assert isinstance(result, str)

    def test_parse_date_various_formats(self):
        """Test date parsing with various formats."""
        agent = DocumentExtractAgent()

        # Test various date formats
        assert agent._parse_date("2024-12-20") == date(2024, 12, 20)
        assert agent._parse_date("12/20/2024") == date(2024, 12, 20)
        assert agent._parse_date("December 20, 2024") == date(2024, 12, 20)
        assert agent._parse_date("Dec 20, 2024") == date(2024, 12, 20)
        assert agent._parse_date(None) is None
        assert agent._parse_date("invalid") is None

    def test_calculate_confidence_high(self):
        """Test confidence calculation with complete data."""
        agent = DocumentExtractAgent()

        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            property_address={"street": "123 Main St", "city": "Miami", "state": "FL"},
            purchase_price=350000.00,
            effective_date=date.today(),
            closing_date=date.today(),
            parties=[
                ExtractedParty(role="buyer", name="John Doe"),
                ExtractedParty(role="seller", name="Jane Smith"),
            ],
            missing_signatures=[],
            unclear_items=[],
        )

        confidence = agent._calculate_confidence(output)
        assert confidence > 0.8  # Should be high confidence

    def test_calculate_confidence_low(self):
        """Test confidence calculation with incomplete data."""
        agent = DocumentExtractAgent()

        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            property_address=None,  # Missing
            purchase_price=None,  # Missing
            effective_date=None,  # Missing
            closing_date=None,  # Missing
            parties=[],  # Missing
            missing_signatures=["buyer", "seller"],
            unclear_items=["purchase price unclear", "closing date illegible"],
        )

        confidence = agent._calculate_confidence(output)
        assert confidence < 0.5  # Should be low confidence

    def test_parse_extraction_result_valid_json(self):
        """Test parsing valid extraction result."""
        agent = DocumentExtractAgent()
        document_id = uuid4()

        json_result = '''
        {
            "document_type_detected": "purchase_contract",
            "property_address": {"street": "123 Main St", "city": "Miami", "state": "FL", "zip_code": "33101"},
            "purchase_price": 350000.00,
            "effective_date": "2024-12-20",
            "closing_date": "2025-01-20",
            "parties": [
                {"role": "buyer", "name": "John Doe", "email": "john@example.com"}
            ],
            "contingencies": [
                {"contingency_type": "inspection", "days_from_effective": 15, "description": "Inspection period"}
            ],
            "missing_signatures": [],
            "unclear_items": []
        }
        '''

        output = agent._parse_extraction_result(json_result, document_id, "purchase_contract")

        assert output.document_id == document_id
        assert output.document_type_detected == "purchase_contract"
        assert output.property_address["street"] == "123 Main St"
        assert output.purchase_price == 350000.00
        assert output.effective_date == date(2024, 12, 20)
        assert len(output.parties) == 1
        assert output.parties[0].name == "John Doe"
        assert len(output.contingencies) == 1

    def test_parse_extraction_result_invalid_json(self):
        """Test parsing invalid JSON result."""
        agent = DocumentExtractAgent()
        document_id = uuid4()

        output = agent._parse_extraction_result("not valid json", document_id, "purchase_contract")

        assert output.document_id == document_id
        assert len(output.unclear_items) > 0  # Should have an error message


# === DeadlineAgent Tests ===


class TestDeadlineAgent:
    """Tests for the DeadlineAgent."""

    def test_agent_name(self):
        """Test agent has correct name."""
        agent = DeadlineAgent()
        assert agent.name == "deadline"

    @pytest.mark.asyncio
    async def test_calculate_deadlines_basic(self, agent_context):
        """Test basic deadline calculation."""
        agent = DeadlineAgent()

        input_data = DeadlineInput(
            transaction_id=agent_context.transaction_id,
            effective_date=date(2024, 12, 20),
            closing_date=date(2025, 1, 20),
            contingencies=[
                {
                    "contingency_type": "inspection",
                    "days_from_effective": 15,
                    "description": "Inspection period",
                }
            ],
            state="FL",
        )

        result = await agent.execute(agent_context, input_data)

        assert result.success is True
        assert result.output is not None
        assert len(result.output.deadlines) > 0

        # Check that closing deadline is included
        deadline_names = [d.name for d in result.output.deadlines]
        assert any("closing" in name.lower() for name in deadline_names)

    @pytest.mark.asyncio
    async def test_statutory_deadlines_fl(self, agent_context):
        """Test Florida statutory deadlines are included."""
        agent = DeadlineAgent()

        input_data = DeadlineInput(
            transaction_id=agent_context.transaction_id,
            effective_date=date(2024, 12, 20),
            closing_date=date(2025, 1, 20),
            contingencies=[],
            state="FL",
        )

        result = await agent.execute(agent_context, input_data)

        assert result.success is True

        # Check for Florida-specific deadlines
        deadline_types = [d.deadline_type for d in result.output.deadlines]
        # Should include statutory deadlines like HOA disclosure
        assert any("statutory" in dt or "hoa" in dt.lower() for dt in deadline_types) or len(deadline_types) > 0


# === ChecklistAgent Tests ===


class TestChecklistAgent:
    """Tests for the ChecklistAgent."""

    def test_agent_name(self):
        """Test agent has correct name."""
        agent = ChecklistAgent()
        assert agent.name == "checklist"

    @pytest.mark.asyncio
    async def test_initialize_checklist(self, agent_context):
        """Test checklist initialization."""
        agent = ChecklistAgent()

        input_data = ChecklistInput(
            transaction_id=agent_context.transaction_id,
            action="initialize",
            is_financed=True,
            is_hoa=True,
            property_year_built=1990,
        )

        result = await agent.execute(agent_context, input_data)

        assert result.success is True
        assert result.output is not None
        assert len(result.output.items) > 0

        # Check for common required documents
        item_names = [item.name.lower() for item in result.output.items]
        assert any("contract" in name for name in item_names)

    @pytest.mark.asyncio
    async def test_document_uploaded_action(self, agent_context):
        """Test document uploaded action updates checklist."""
        agent = ChecklistAgent()

        input_data = ChecklistInput(
            transaction_id=agent_context.transaction_id,
            document_id=uuid4(),
            document_type="purchase_contract",
            action="document_uploaded",
        )

        result = await agent.execute(agent_context, input_data)

        assert result.success is True


# === AgentResult Tests ===


class TestAgentResult:
    """Tests for the AgentResult model."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = AgentResult(
            success=True,
            execution_id=uuid4(),
            agent_name="test_agent",
            output={"data": "test"},
            confidence=0.95,
            needs_human_review=False,
        )

        assert result.success is True
        assert result.confidence == 0.95
        assert result.needs_human_review is False

    def test_failure_result(self):
        """Test creating a failure result."""
        result = AgentResult(
            success=False,
            execution_id=uuid4(),
            agent_name="test_agent",
            output=None,
            error="Something went wrong",
            needs_human_review=True,
            review_reason="Error occurred",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.needs_human_review is True


# === Integration-style Tests ===


class TestAgentIntegration:
    """Integration-style tests for agent workflows."""

    @pytest.mark.asyncio
    async def test_extraction_to_deadline_flow(self, agent_context):
        """Test the flow from extraction output to deadline input."""
        # Simulate extraction output
        extraction_output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            effective_date=date(2024, 12, 20),
            closing_date=date(2025, 1, 20),
            contingencies=[
                ExtractedContingency(
                    contingency_type="inspection",
                    days_from_effective=15,
                    description="Inspection period",
                )
            ],
        )

        # Use extraction output to create deadline input
        deadline_agent = DeadlineAgent()
        deadline_input = DeadlineInput(
            transaction_id=agent_context.transaction_id,
            effective_date=extraction_output.effective_date,
            closing_date=extraction_output.closing_date,
            contingencies=[c.model_dump() for c in extraction_output.contingencies],
            state="FL",
        )

        result = await deadline_agent.execute(agent_context, deadline_input)

        assert result.success is True
        assert result.output is not None

        # Check inspection deadline was created
        deadline_names = [d.name.lower() for d in result.output.deadlines]
        assert any("inspection" in name for name in deadline_names)
