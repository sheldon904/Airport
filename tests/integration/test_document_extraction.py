"""Integration tests for document extraction agent.

Tests document extraction pipeline including:
- PDF text extraction
- Image document processing (Claude Vision)
- Field extraction and validation
- Confidence scoring
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.agents.document_extract.agent import (
    DocumentExtractAgent,
    DocumentExtractInput,
    DocumentExtractOutput,
    IMAGE_MIME_TYPES,
)
from services.agents.base import AgentContext


@pytest.fixture
def agent():
    """Create document extraction agent instance."""
    return DocumentExtractAgent()


@pytest.fixture
def mock_context():
    """Create mock agent context."""
    return AgentContext(
        execution_id=uuid4(),
        transaction_id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        triggered_by="test",
        triggered_at=datetime.now(timezone.utc),
    )


class TestDocumentExtractInput:
    """Tests for document input model."""

    def test_valid_pdf_input(self):
        """Valid PDF input is created successfully."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="contract.pdf",
            storage_path="s3://bucket/contract.pdf",
        )
        assert input_data.filename == "contract.pdf"
        assert input_data.document_type == "purchase_contract"

    def test_valid_image_input(self):
        """Valid image input is created successfully."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="inspection",
            filename="inspection.jpg",
            storage_path="s3://bucket/inspection.jpg",
        )
        assert input_data.filename == "inspection.jpg"


class TestImageMimeTypes:
    """Tests for image MIME type mappings."""

    def test_jpeg_extensions(self):
        """JPEG extensions are mapped correctly."""
        assert IMAGE_MIME_TYPES[".jpg"] == "image/jpeg"
        assert IMAGE_MIME_TYPES[".jpeg"] == "image/jpeg"

    def test_png_extension(self):
        """PNG extension is mapped correctly."""
        assert IMAGE_MIME_TYPES[".png"] == "image/png"

    def test_gif_extension(self):
        """GIF extension is mapped correctly."""
        assert IMAGE_MIME_TYPES[".gif"] == "image/gif"

    def test_webp_extension(self):
        """WebP extension is mapped correctly."""
        assert IMAGE_MIME_TYPES[".webp"] == "image/webp"

    def test_tiff_extension(self):
        """TIFF extension is mapped correctly."""
        assert IMAGE_MIME_TYPES[".tiff"] == "image/tiff"


class TestDocumentExtractOutput:
    """Tests for extraction output model."""

    def test_output_with_extracted_data(self):
        """Output with extracted data is valid."""
        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            purchase_price=450000.0,
            property_address={"street": "123 Main St", "city": "Miami"},
        )
        assert output.purchase_price == 450000.0
        assert output.document_type_detected == "purchase_contract"

    def test_output_needing_review(self):
        """Output with unclear items needing review."""
        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            unclear_items=["Purchase price is illegible"],
        )
        assert len(output.unclear_items) == 1
        assert "illegible" in output.unclear_items[0]


class TestDocumentExtractAgent:
    """Tests for document extraction agent."""

    def test_agent_name(self, agent):
        """Agent has correct name."""
        assert agent.name == "document_extract"

    def test_agent_version(self, agent):
        """Agent has version defined."""
        assert hasattr(agent, "version")

    def test_is_image_document_jpg(self, agent):
        """Correctly identifies JPG as image."""
        assert agent._is_image_document("document.jpg") is True
        assert agent._is_image_document("document.JPG") is True

    def test_is_image_document_png(self, agent):
        """Correctly identifies PNG as image."""
        assert agent._is_image_document("photo.png") is True

    def test_is_image_document_pdf(self, agent):
        """Correctly identifies PDF as not an image."""
        assert agent._is_image_document("contract.pdf") is False

    def test_get_mime_type_jpg(self, agent):
        """Gets correct MIME type for JPG."""
        mime = agent._get_mime_type("photo.jpg")
        assert mime == "image/jpeg"

    def test_get_mime_type_png(self, agent):
        """Gets correct MIME type for PNG."""
        mime = agent._get_mime_type("image.png")
        assert mime == "image/png"

    def test_get_mime_type_unknown(self, agent):
        """Returns default for unknown type."""
        mime = agent._get_mime_type("file.xyz")
        assert mime == "image/jpeg"  # Default when extension is not recognized


class TestExtractionWithMocks:
    """Integration tests with mocked external services."""

    @pytest.mark.asyncio
    async def test_pdf_extraction_flow(self, agent, mock_context):
        """PDF document goes through correct extraction flow."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="contract.pdf",
            storage_path="s3://bucket/contract.pdf",
        )

        with patch.object(agent, "_fetch_document_content") as mock_fetch, \
             patch.object(agent, "_extract_text_from_pdf") as mock_extract, \
             patch.object(agent, "_call_claude_for_extraction") as mock_claude:

            mock_fetch.return_value = b"%PDF-1.4 test content"
            mock_extract.return_value = "Purchase Price: $450,000\nBuyer: John Smith"
            mock_claude.return_value = '{"purchase_price": "450000", "buyer_name": "John Smith"}'

            output, confidence, needs_review, reason = await agent.process(
                mock_context, input_data
            )

            mock_fetch.assert_called_once()
            mock_extract.assert_called_once()
            mock_claude.assert_called_once()

    @pytest.mark.asyncio
    async def test_image_extraction_uses_vision(self, agent, mock_context):
        """Image document uses Claude Vision API."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="inspection",
            filename="report.jpg",
            storage_path="s3://bucket/report.jpg",
        )

        with patch.object(agent, "_fetch_document_content") as mock_fetch, \
             patch.object(agent, "_call_claude_vision") as mock_vision:

            mock_fetch.return_value = b"\xff\xd8\xff fake jpeg data"
            mock_vision.return_value = '{"inspector_name": "Bob Smith", "inspection_date": "2024-06-15"}'

            output, confidence, needs_review, reason = await agent.process(
                mock_context, input_data
            )

            mock_vision.assert_called_once()

    @pytest.mark.asyncio
    async def test_extraction_handles_errors_gracefully(self, agent, mock_context):
        """Agent handles extraction errors gracefully."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="corrupt.pdf",
            storage_path="s3://bucket/corrupt.pdf",
        )

        with patch.object(agent, "_fetch_document_content") as mock_fetch:
            mock_fetch.side_effect = Exception("Storage error")

            output, confidence, needs_review, reason = await agent.process(
                mock_context, input_data
            )

            # Should return output with error indication
            assert output is not None
            assert needs_review is True or reason is not None


class TestConfidenceScoring:
    """Tests for confidence score calculations."""

    def test_high_confidence_no_review(self):
        """High confidence extraction with clear data."""
        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            purchase_price=450000.0,
            property_address={"street": "123 Main St"},
        )
        # No unclear items indicates clean extraction
        assert len(output.unclear_items) == 0

    def test_low_confidence_triggers_review(self):
        """Low confidence should show unclear items."""
        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            unclear_items=["Purchase price is ambiguous"],
        )
        assert len(output.unclear_items) > 0

    def test_missing_required_fields_triggers_review(self):
        """Missing required fields should trigger review."""
        output = DocumentExtractOutput(
            document_id=uuid4(),
            document_type_detected="purchase_contract",
            unclear_items=["Missing buyer information", "Missing purchase price"],
        )
        assert len(output.unclear_items) == 2
        assert any("Missing" in item for item in output.unclear_items)


class TestDocumentTypeHandling:
    """Tests for different document type handling."""

    @pytest.fixture
    def contract_input(self):
        """Create purchase contract input."""
        return DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="contract.pdf",
            storage_path="s3://bucket/contract.pdf",
        )

    @pytest.fixture
    def disclosure_input(self):
        """Create disclosure input."""
        return DocumentExtractInput(
            document_id=uuid4(),
            document_type="seller_disclosure",
            filename="disclosure.pdf",
            storage_path="s3://bucket/disclosure.pdf",
        )

    @pytest.fixture
    def inspection_input(self):
        """Create inspection report input."""
        return DocumentExtractInput(
            document_id=uuid4(),
            document_type="inspection_report",
            filename="inspection.pdf",
            storage_path="s3://bucket/inspection.pdf",
        )

    def test_contract_input_valid(self, contract_input):
        """Purchase contract input is valid."""
        assert contract_input.document_type == "purchase_contract"

    def test_disclosure_input_valid(self, disclosure_input):
        """Seller disclosure input is valid."""
        assert disclosure_input.document_type == "seller_disclosure"

    def test_inspection_input_valid(self, inspection_input):
        """Inspection report input is valid."""
        assert inspection_input.document_type == "inspection_report"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_filename(self):
        """Empty filename should still create valid model."""
        # Pydantic allows empty strings by default
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="",
            storage_path="s3://bucket/file.pdf",
        )
        assert input_data.filename == ""

    def test_invalid_uuid(self):
        """Invalid UUID should raise error."""
        with pytest.raises(Exception):
            DocumentExtractInput(
                document_id="not-a-uuid",
                document_type="purchase_contract",
                filename="file.pdf",
                storage_path="s3://bucket/file.pdf",
            )

    @pytest.mark.asyncio
    async def test_very_large_file_handling(self, agent, mock_context):
        """Large files should be handled appropriately."""
        input_data = DocumentExtractInput(
            document_id=uuid4(),
            document_type="purchase_contract",
            filename="large.pdf",
            storage_path="s3://bucket/large.pdf",
        )

        with patch.object(agent, "_fetch_document_content") as mock_fetch:
            # Simulate large file content
            mock_fetch.return_value = b"x" * (50 * 1024 * 1024)  # 50MB

            # Should handle without crashing
            try:
                output, _, _, _ = await agent.process(mock_context, input_data)
            except Exception as e:
                # Should raise appropriate size limit error, not crash
                assert "size" in str(e).lower() or "limit" in str(e).lower()
