"""Document extraction agent implementation."""

import json
import re
from datetime import date, datetime
from io import BytesIO
from typing import Any
from uuid import UUID

import httpx
from anthropic import AsyncAnthropic, APIError, APITimeoutError
from pydantic import BaseModel
from pypdf import PdfReader

from packages.core.config import settings
from packages.core.exceptions import AIServiceError
from packages.core.services.storage import get_storage_service
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
    deadline_date: date | None = None
    days_from_effective: int | None = None
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


EXTRACTION_PROMPT = """You are a document extraction assistant for Florida real estate transactions.
Your job is to extract factual information from documents - you do NOT interpret contracts or provide legal advice.

IMPORTANT COMPLIANCE NOTES:
- Only extract factual information that is explicitly stated in the document
- Do NOT make assumptions or interpretations about contract terms
- If information is unclear, ambiguous, or missing, flag it for human review
- Do NOT provide any legal advice or recommendations

Extract the following information if present:

1. PROPERTY ADDRESS
   - Street address, unit number if applicable
   - City, State, ZIP code
   - County if mentioned

2. FINANCIAL TERMS
   - Purchase price
   - Earnest money deposit amount
   - Additional deposits if mentioned

3. PARTIES (for each party found):
   - Role (buyer, seller, buyer_agent, seller_agent, lender, title_company, etc.)
   - Full legal name
   - Email address
   - Phone number
   - Company/brokerage name
   - License number for agents

4. KEY DATES
   - Effective date (when contract becomes binding)
   - Closing date
   - Any contingency deadlines

5. CONTINGENCIES
   - Type (inspection, financing, appraisal, sale contingency, etc.)
   - Deadline date or days from effective date
   - Whether waived

6. DOCUMENT COMPLETENESS
   - List any missing signatures or initials
   - Note any blank required fields

7. UNCLEAR ITEMS
   - Any information that is ambiguous or hard to read
   - Handwritten notes that are unclear
   - Custom terms that may need review

Return your response as a JSON object with this structure:
{
  "document_type_detected": "purchase_contract",
  "property_address": {"street": "", "unit": null, "city": "", "state": "FL", "zip_code": "", "county": null},
  "purchase_price": 350000.00,
  "earnest_money": 10000.00,
  "parties": [
    {"role": "buyer", "name": "", "email": null, "phone": null, "company": null}
  ],
  "effective_date": "2024-12-20",
  "closing_date": "2025-01-20",
  "dates": [
    {"date_type": "inspection_deadline", "value": "2024-12-30", "source_text": "within 10 days", "confidence": 0.9}
  ],
  "contingencies": [
    {"contingency_type": "inspection", "deadline_date": "2024-12-30", "days_from_effective": 10, "description": "Buyer inspection period", "waived": false}
  ],
  "missing_signatures": [],
  "unclear_items": [],
  "additional_data": {}
}

Document Type: {document_type}
Filename: {filename}

---
DOCUMENT CONTENT:
{document_content}
---

Return ONLY the JSON object, no other text."""


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
    version = "0.2.0"

    def __init__(self) -> None:
        super().__init__()
        self.client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=httpx.Timeout(settings.anthropic_timeout_seconds),
        )
        self.storage = get_storage_service()

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
        self.logger.info(
            "extraction_started",
            document_id=str(input_data.document_id),
            document_type=input_data.document_type,
        )

        try:
            # 1. Fetch document from S3
            document_bytes = await self.storage.download_file(input_data.storage_path)

            # 2. Extract text from document
            document_text = await self._extract_text(document_bytes, input_data.filename)

            if not document_text.strip():
                return (
                    DocumentExtractOutput(
                        document_id=input_data.document_id,
                        document_type_detected=input_data.document_type,
                        unclear_items=["Could not extract text from document"],
                    ),
                    0.0,
                    True,
                    "Document appears to be empty or unreadable",
                )

            # 3. Call Claude API for extraction
            extraction_result = await self._call_claude(
                document_text,
                input_data.document_type,
                input_data.filename,
            )

            # 4. Parse the response
            output = self._parse_extraction_result(
                extraction_result,
                input_data.document_id,
                input_data.document_type,
            )

            # 5. Calculate confidence
            confidence = self._calculate_confidence(output)

            # 6. Determine if human review needed
            needs_review = (
                confidence < settings.extraction_confidence_threshold
                or len(output.unclear_items) > 0
                or len(output.missing_signatures) > 0
            )

            review_reason = None
            if needs_review:
                reasons = []
                if confidence < settings.extraction_confidence_threshold:
                    reasons.append(f"Low confidence: {confidence:.0%}")
                if output.unclear_items:
                    reasons.append(f"{len(output.unclear_items)} unclear items")
                if output.missing_signatures:
                    reasons.append(f"{len(output.missing_signatures)} missing signatures")
                review_reason = "; ".join(reasons)

            self.logger.info(
                "extraction_completed",
                document_id=str(input_data.document_id),
                confidence=confidence,
                needs_review=needs_review,
                parties_found=len(output.parties),
                dates_found=len(output.dates),
            )

            return (output, confidence, needs_review, review_reason)

        except Exception as e:
            self.logger.error(
                "extraction_failed",
                document_id=str(input_data.document_id),
                error=str(e),
            )

            return (
                DocumentExtractOutput(
                    document_id=input_data.document_id,
                    document_type_detected=input_data.document_type,
                    unclear_items=[f"Extraction failed: {str(e)}"],
                ),
                0.0,
                True,
                f"Extraction failed: {str(e)}",
            )

    async def _extract_text(self, content: bytes, filename: str) -> str:
        """Extract text content from document."""
        filename_lower = filename.lower()

        if filename_lower.endswith(".pdf"):
            return self._extract_pdf_text(content)
        elif filename_lower.endswith((".jpg", ".jpeg", ".png", ".tiff")):
            # For images, we'll use Claude's vision capabilities
            return f"[IMAGE: {filename}]"
        else:
            # Try to decode as text
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="ignore")

    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF using pypdf."""
        try:
            reader = PdfReader(BytesIO(content))
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            self.logger.warning("pdf_extraction_failed", error=str(e))
            return ""

    async def _call_claude(
        self,
        document_content: str,
        document_type: str,
        filename: str,
    ) -> str:
        """Call Claude API for extraction using async client."""
        # Truncate very long documents to stay within context limits
        max_content_length = 100000  # ~25k tokens
        if len(document_content) > max_content_length:
            document_content = document_content[:max_content_length] + "\n\n[DOCUMENT TRUNCATED]"

        prompt = EXTRACTION_PROMPT.format(
            document_type=document_type,
            filename=filename,
            document_content=document_content,
        )

        try:
            message = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Validate response structure
            if not message.content:
                self.logger.error("claude_empty_response")
                raise AIServiceError(message="AI returned empty response")

            # Find text content block
            text_content = None
            for block in message.content:
                if hasattr(block, "text"):
                    text_content = block.text
                    break

            if not text_content:
                self.logger.error(
                    "claude_no_text_content",
                    content_types=[type(b).__name__ for b in message.content],
                )
                raise AIServiceError(message="AI response did not contain text content")

            return text_content

        except APITimeoutError as e:
            self.logger.error("claude_timeout", error=str(e))
            raise AIServiceError(message="AI extraction timed out. Please try again.")
        except APIError as e:
            self.logger.error("claude_api_error", error=str(e), status_code=getattr(e, 'status_code', None))
            raise AIServiceError(message=f"AI service error: {getattr(e, 'message', str(e))}")

    def _parse_extraction_result(
        self,
        result: str,
        document_id: UUID,
        document_type: str,
    ) -> DocumentExtractOutput:
        """Parse Claude's response into structured output."""
        try:
            # Try to extract JSON from the response
            # Handle cases where Claude might add extra text
            json_match = re.search(r"\{[\s\S]*\}", result)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")

            # Parse dates
            dates = []
            for d in data.get("dates", []):
                try:
                    dates.append(
                        ExtractedDate(
                            date_type=d["date_type"],
                            value=self._parse_date(d["value"]),
                            source_text=d.get("source_text", ""),
                            confidence=d.get("confidence", 0.8),
                        )
                    )
                except (KeyError, ValueError):
                    continue

            # Parse contingencies
            contingencies = []
            for c in data.get("contingencies", []):
                try:
                    contingencies.append(
                        ExtractedContingency(
                            contingency_type=c["contingency_type"],
                            deadline_date=self._parse_date(c.get("deadline_date"))
                            if c.get("deadline_date")
                            else None,
                            days_from_effective=c.get("days_from_effective"),
                            description=c.get("description", ""),
                            waived=c.get("waived", False),
                        )
                    )
                except (KeyError, ValueError):
                    continue

            # Parse parties
            parties = []
            for p in data.get("parties", []):
                try:
                    parties.append(
                        ExtractedParty(
                            role=p["role"],
                            name=p["name"],
                            email=p.get("email"),
                            phone=p.get("phone"),
                            company=p.get("company"),
                        )
                    )
                except (KeyError, ValueError):
                    continue

            return DocumentExtractOutput(
                document_id=document_id,
                document_type_detected=data.get("document_type_detected", document_type),
                property_address=data.get("property_address"),
                purchase_price=data.get("purchase_price"),
                earnest_money=data.get("earnest_money"),
                parties=parties,
                dates=dates,
                effective_date=self._parse_date(data.get("effective_date"))
                if data.get("effective_date")
                else None,
                closing_date=self._parse_date(data.get("closing_date"))
                if data.get("closing_date")
                else None,
                contingencies=contingencies,
                additional_data=data.get("additional_data", {}),
                missing_signatures=data.get("missing_signatures", []),
                unclear_items=data.get("unclear_items", []),
            )

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning("parse_failed", error=str(e))
            return DocumentExtractOutput(
                document_id=document_id,
                document_type_detected=document_type,
                unclear_items=[f"Failed to parse extraction result: {str(e)}"],
            )

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse a date string into a date object."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _calculate_confidence(self, output: DocumentExtractOutput) -> float:
        """Calculate overall extraction confidence."""
        scores = []

        # Check for key fields
        if output.property_address:
            scores.append(1.0)
        else:
            scores.append(0.0)

        if output.purchase_price:
            scores.append(1.0)
        else:
            scores.append(0.3)

        if output.effective_date:
            scores.append(1.0)
        else:
            scores.append(0.3)

        if output.closing_date:
            scores.append(1.0)
        else:
            scores.append(0.5)

        if len(output.parties) >= 2:
            scores.append(1.0)
        elif len(output.parties) == 1:
            scores.append(0.5)
        else:
            scores.append(0.2)

        # Penalty for unclear items
        if output.unclear_items:
            penalty = min(len(output.unclear_items) * 0.1, 0.3)
            scores.append(1.0 - penalty)
        else:
            scores.append(1.0)

        # Penalty for missing signatures
        if output.missing_signatures:
            penalty = min(len(output.missing_signatures) * 0.15, 0.4)
            scores.append(1.0 - penalty)
        else:
            scores.append(1.0)

        return sum(scores) / len(scores) if scores else 0.0
