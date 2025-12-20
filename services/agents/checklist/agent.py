"""Checklist agent implementation for auto-updating transaction checklists."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from packages.compliance.florida import (
    FL_RESIDENTIAL_PURCHASE_CHECKLIST,
    ChecklistRequirement,
    FloridaComplianceEngine,
)
from packages.core.models import ChecklistItemStatus, DocumentType
from services.agents.base import AgentContext, AgentEvent, BaseAgent, emit_event


# === Input/Output Models ===


class ChecklistInput(BaseModel):
    """Input for checklist update."""

    transaction_id: UUID
    document_id: UUID | None = None
    document_type: str | None = None
    action: str  # "initialize", "document_uploaded", "document_verified", "manual_update"
    property_year_built: int | None = None
    is_hoa: bool = False
    is_financed: bool = True
    item_updates: dict[str, str] | None = None  # item_id -> new status


class ChecklistItemResult(BaseModel):
    """A single checklist item result."""

    id: str
    name: str
    description: str | None = None
    category: str
    required: bool
    status: str
    document_id: str | None = None
    due_date: str | None = None
    auto_updated: bool = False


class ChecklistOutput(BaseModel):
    """Output from checklist processing."""

    transaction_id: UUID
    checklist_id: UUID
    template_id: str
    items: list[ChecklistItemResult]
    completion_percentage: float
    items_updated: list[str] = []
    missing_required: list[str] = []


# === Document Type to Checklist Item Mapping ===

DOCUMENT_TO_CHECKLIST_MAPPING: dict[str, list[str]] = {
    "purchase_contract": ["fl_contract_executed"],
    "earnest_money": ["fl_earnest_money_receipt"],
    "seller_disclosure": ["fl_seller_disclosure"],
    "lead_paint": ["fl_lead_paint"],
    "hoa_disclosure": ["fl_hoa_disclosure"],
    "property_tax": ["fl_property_tax_disclosure"],
    "radon_disclosure": ["fl_radon_disclosure"],
    "energy_disclosure": ["fl_energy_disclosure"],
    "pre_approval": ["fl_preapproval"],
    "proof_of_funds": ["fl_preapproval"],
    "loan_commitment": ["fl_loan_commitment"],
    "inspection_report": ["fl_home_inspection"],
    "termite_inspection": ["fl_termite_inspection"],
    "appraisal": ["fl_appraisal"],
    "survey": ["fl_survey"],
    "title_commitment": ["fl_title_commitment"],
    "title_search": ["fl_title_search"],
    "closing_disclosure": ["fl_closing_disclosure"],
    "deed": ["fl_deed"],
}


class ChecklistAgent(BaseAgent[ChecklistInput, ChecklistOutput]):
    """
    Agent for managing transaction checklists.

    Handles:
    - Initializing checklists based on FL compliance requirements
    - Auto-updating checklist items when documents are uploaded
    - Tracking completion status
    - Flagging missing required documents

    Compliance Notes:
    - Uses Florida-specific checklist templates
    - Applies conditional requirements based on property characteristics
    - Does NOT make compliance determinations - only tracks status
    """

    name = "checklist"
    version = "0.1.0"

    async def process(
        self,
        context: AgentContext,
        input_data: ChecklistInput,
    ) -> tuple[ChecklistOutput, float | None, bool, str | None]:
        """
        Process checklist updates.

        Returns:
            tuple: (output, confidence, needs_review, review_reason)
        """
        self.logger.info(
            "checklist_processing",
            transaction_id=str(input_data.transaction_id),
            action=input_data.action,
        )

        if input_data.action == "initialize":
            return await self._initialize_checklist(context, input_data)
        elif input_data.action == "document_uploaded":
            return await self._handle_document_upload(context, input_data)
        elif input_data.action == "document_verified":
            return await self._handle_document_verified(context, input_data)
        elif input_data.action == "manual_update":
            return await self._handle_manual_update(context, input_data)
        else:
            return (
                ChecklistOutput(
                    transaction_id=input_data.transaction_id,
                    checklist_id=uuid4(),
                    template_id="FL_RESIDENTIAL_PURCHASE",
                    items=[],
                    completion_percentage=0.0,
                ),
                0.5,
                True,
                f"Unknown action: {input_data.action}",
            )

    async def _initialize_checklist(
        self,
        context: AgentContext,
        input_data: ChecklistInput,
    ) -> tuple[ChecklistOutput, float | None, bool, str | None]:
        """Initialize a new checklist for a transaction."""
        # Get applicable requirements based on property characteristics
        requirements = FloridaComplianceEngine.get_residential_purchase_checklist(
            property_year_built=input_data.property_year_built,
            is_hoa=input_data.is_hoa,
            is_financed=input_data.is_financed,
        )

        checklist_id = uuid4()
        items = []

        for req in requirements:
            items.append(
                ChecklistItemResult(
                    id=req.id,
                    name=req.name,
                    description=req.description,
                    category=req.category.value,
                    required=req.required,
                    status=ChecklistItemStatus.NOT_STARTED.value,
                    document_id=None,
                    due_date=None,
                    auto_updated=False,
                )
            )

        # Calculate initial stats
        missing_required = [item.id for item in items if item.required]

        output = ChecklistOutput(
            transaction_id=input_data.transaction_id,
            checklist_id=checklist_id,
            template_id="FL_RESIDENTIAL_PURCHASE",
            items=items,
            completion_percentage=0.0,
            items_updated=[],
            missing_required=missing_required,
        )

        await emit_event(
            AgentEvent(
                event_type="checklist.initialized",
                agent_name=self.name,
                execution_id=context.execution_id,
                transaction_id=input_data.transaction_id,
                timestamp=datetime.now(),
                payload={
                    "checklist_id": str(checklist_id),
                    "item_count": len(items),
                    "required_count": len(missing_required),
                },
            )
        )

        return (output, 1.0, False, None)

    async def _handle_document_upload(
        self,
        context: AgentContext,
        input_data: ChecklistInput,
    ) -> tuple[ChecklistOutput, float | None, bool, str | None]:
        """Update checklist when a document is uploaded."""
        if not input_data.document_type or not input_data.document_id:
            return (
                ChecklistOutput(
                    transaction_id=input_data.transaction_id,
                    checklist_id=uuid4(),
                    template_id="FL_RESIDENTIAL_PURCHASE",
                    items=[],
                    completion_percentage=0.0,
                ),
                0.5,
                True,
                "Missing document_type or document_id",
            )

        # Find matching checklist items
        matching_items = DOCUMENT_TO_CHECKLIST_MAPPING.get(
            input_data.document_type.lower(), []
        )

        if not matching_items:
            self.logger.info(
                "no_checklist_match",
                document_type=input_data.document_type,
            )
            return (
                ChecklistOutput(
                    transaction_id=input_data.transaction_id,
                    checklist_id=uuid4(),
                    template_id="FL_RESIDENTIAL_PURCHASE",
                    items=[],
                    completion_percentage=0.0,
                    items_updated=[],
                ),
                1.0,
                False,
                None,
            )

        # Build update result
        updated_items = []
        for item_id in matching_items:
            updated_items.append(
                ChecklistItemResult(
                    id=item_id,
                    name=self._get_item_name(item_id),
                    description=None,
                    category="",
                    required=True,
                    status=ChecklistItemStatus.PENDING_REVIEW.value,
                    document_id=str(input_data.document_id),
                    auto_updated=True,
                )
            )

        output = ChecklistOutput(
            transaction_id=input_data.transaction_id,
            checklist_id=uuid4(),
            template_id="FL_RESIDENTIAL_PURCHASE",
            items=updated_items,
            completion_percentage=0.0,  # Would need full checklist to calculate
            items_updated=matching_items,
        )

        await emit_event(
            AgentEvent(
                event_type="checklist.items_updated",
                agent_name=self.name,
                execution_id=context.execution_id,
                transaction_id=input_data.transaction_id,
                timestamp=datetime.now(),
                payload={
                    "document_id": str(input_data.document_id),
                    "items_updated": matching_items,
                    "new_status": ChecklistItemStatus.PENDING_REVIEW.value,
                },
            )
        )

        return (output, 0.95, False, None)

    async def _handle_document_verified(
        self,
        context: AgentContext,
        input_data: ChecklistInput,
    ) -> tuple[ChecklistOutput, float | None, bool, str | None]:
        """Update checklist when a document is verified."""
        if not input_data.document_type or not input_data.document_id:
            return (
                ChecklistOutput(
                    transaction_id=input_data.transaction_id,
                    checklist_id=uuid4(),
                    template_id="FL_RESIDENTIAL_PURCHASE",
                    items=[],
                    completion_percentage=0.0,
                ),
                0.5,
                True,
                "Missing document_type or document_id",
            )

        matching_items = DOCUMENT_TO_CHECKLIST_MAPPING.get(
            input_data.document_type.lower(), []
        )

        updated_items = []
        for item_id in matching_items:
            updated_items.append(
                ChecklistItemResult(
                    id=item_id,
                    name=self._get_item_name(item_id),
                    description=None,
                    category="",
                    required=True,
                    status=ChecklistItemStatus.COMPLETED.value,
                    document_id=str(input_data.document_id),
                    auto_updated=True,
                )
            )

        output = ChecklistOutput(
            transaction_id=input_data.transaction_id,
            checklist_id=uuid4(),
            template_id="FL_RESIDENTIAL_PURCHASE",
            items=updated_items,
            completion_percentage=0.0,
            items_updated=matching_items,
        )

        await emit_event(
            AgentEvent(
                event_type="checklist.items_completed",
                agent_name=self.name,
                execution_id=context.execution_id,
                transaction_id=input_data.transaction_id,
                timestamp=datetime.now(),
                payload={
                    "document_id": str(input_data.document_id),
                    "items_completed": matching_items,
                },
            )
        )

        return (output, 1.0, False, None)

    async def _handle_manual_update(
        self,
        context: AgentContext,
        input_data: ChecklistInput,
    ) -> tuple[ChecklistOutput, float | None, bool, str | None]:
        """Handle manual checklist updates."""
        if not input_data.item_updates:
            return (
                ChecklistOutput(
                    transaction_id=input_data.transaction_id,
                    checklist_id=uuid4(),
                    template_id="FL_RESIDENTIAL_PURCHASE",
                    items=[],
                    completion_percentage=0.0,
                ),
                0.5,
                True,
                "No item_updates provided",
            )

        updated_items = []
        for item_id, new_status in input_data.item_updates.items():
            updated_items.append(
                ChecklistItemResult(
                    id=item_id,
                    name=self._get_item_name(item_id),
                    description=None,
                    category="",
                    required=True,
                    status=new_status,
                    auto_updated=False,
                )
            )

        output = ChecklistOutput(
            transaction_id=input_data.transaction_id,
            checklist_id=uuid4(),
            template_id="FL_RESIDENTIAL_PURCHASE",
            items=updated_items,
            completion_percentage=0.0,
            items_updated=list(input_data.item_updates.keys()),
        )

        return (output, 1.0, False, None)

    def _get_item_name(self, item_id: str) -> str:
        """Get the name for a checklist item by ID."""
        for req in FL_RESIDENTIAL_PURCHASE_CHECKLIST:
            if req.id == item_id:
                return req.name
        return item_id
