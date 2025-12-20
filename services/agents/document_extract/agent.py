"""Document extraction agent implementation."""

from datetime import date
from typing import Any
from uuid import UUID

from anthropic import Anthropic
from pydantic import BaseModel

from packages.core.config import settings
from services.agents.base import AgentContext, BaseAgent


# === Input/Output Models ===


class DocumentExtractInput(BaseModel):
    """Input for document extraction."""

    document_id: UUID
    document_type: str
    storage_path: str
    filename: str


class ExtractedParty(BaseModel):
    """Extracted party information."""

    role: str
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class ExtractedDate(BaseModel):
    """Extracted date with context."""

    date_type: str
    value: date
    source_text: str
    confidence: float


class ExtractedContingency(BaseModel):
    """Extracted contingency information."""

    contingency_type: str
    deadline_date: date | None
    days_from_effective: int | None
    description: str
    waived: bool = False


class DocumentExtractOutput(BaseModel):
    """Output from document extraction."""

    document_id: UUID
    document_type_detected: str

    # Property
    property_address: dict[str, str] | None = None
    purchase_price: float | None = None
    earnest_money: float | None = None

    # Parties
    parties: list[ExtractedParty] = []

    # Dates
    dates: list[ExtractedDate] = []
    effective_date: date | None = None
    closing_date: date | None = None

    # Contingencies
    contingencies: list[ExtractedContingency] = []

    # Other extracted data
    additional_data: dict[str, Any] = {}

    # Flags for review
    missing_signatures: list[str] = []
    unclear_items: list[str] = []


# === Agent Implementation ===


class DocumentExtractAgent(BaseAgent[DocumentExtractInput, DocumentExtractOutput]):
    """
    Agent for extracting structured data from real estate documents.

    Uses Claude API to parse contracts, disclosures, and other documents,
    extracting parties, dates, contingencies, and other key information.

    Compliance Notes:
    - Only extracts factual information from documents
    - Does NOT interpret contract terms or provide legal advice
    - Flags ambiguous items for human review
    """

    name = "document_extract"
    version = "0.1.0"

    EXTRACTION_PROMPT = """You are a document extraction assistant for real estate transactions.
Your job is to extract factual information from documents - you do NOT interpret contracts or provide legal advice.

Extract the following information if present:
1. Property address (street, city, state, zip)
2. Purchase price and earnest money amounts
3. All parties and their roles (buyer, seller, agents, lender, title company)
4. Key dates (effective date, closing date, contingency deadlines)
5. Contingencies and their terms
6. Missing signatures or initials
7. Any items that are unclear or may need human review

Format your response as structured JSON matching the expected schema.
If information is unclear or missing, note it in the unclear_items field.
Do NOT make assumptions - if you can't confidently extract something, flag it for review.

Document Type: {document_type}
Filename: {filename}

Document content:
{document_content}
"""

    def __init__(self) -> None:
        super().__init__()
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    async def process(
        self,
        context: AgentContext,
        input_data: DocumentExtractInput,
    ) -> tuple[DocumentExtractOutput, float | None, bool, str | None]:
        """
        Extract structured data from a document.

        Returns:
            tuple: (extracted_data, confidence, needs_review, review_reason)
        """
        # TODO: Implement full extraction logic
        # 1. Fetch document from S3
        # 2. Convert to text (PDF extraction, OCR if needed)
        # 3. Call Claude API with extraction prompt
        # 4. Parse response into structured output
        # 5. Calculate confidence based on extraction quality
        # 6. Determine if human review needed

        # Placeholder implementation
        self.logger.info(
            "extraction_started",
            document_id=str(input_data.document_id),
            document_type=input_data.document_type,
        )

        # This would be replaced with actual LLM call
        output = DocumentExtractOutput(
            document_id=input_data.document_id,
            document_type_detected=input_data.document_type,
            unclear_items=["Extraction not yet implemented"],
        )

        # Flag for review since this is placeholder
        return (output, None, True, "Extraction not yet implemented")

    async def _fetch_document(self, storage_path: str) -> bytes:
        """Fetch document content from S3."""
        # TODO: Implement S3 fetch
        raise NotImplementedError("S3 fetch not yet implemented")

    async def _extract_text(self, content: bytes, filename: str) -> str:
        """Extract text content from document."""
        # TODO: Implement PDF/image text extraction
        raise NotImplementedError("Text extraction not yet implemented")

    async def _call_claude(self, document_content: str, document_type: str, filename: str) -> str:
        """Call Claude API for extraction."""
        prompt = self.EXTRACTION_PROMPT.format(
            document_type=document_type,
            filename=filename,
            document_content=document_content,
        )

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text
