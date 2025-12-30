"""Forms router - Florida real estate form population endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.session import get_db
from packages.forms import (
    FL_FORM_TEMPLATES,
    FormPopulationService,
    get_form_service,
    get_template,
    get_templates_by_category,
    FormCategory,
)
from packages.forms.disclosures import (
    get_required_disclosures,
    get_disclosure_checklist,
)
# REM-003: Use standard CurrentUserDep for consistent auth handling
from services.api.dependencies import CurrentUserDep, DbSessionDep
from packages.core.services import TransactionService


router = APIRouter()


class FormListResponse(BaseModel):
    """Response containing list of available forms."""

    forms: list[dict[str, Any]]
    total: int


class PopulateFormRequest(BaseModel):
    """Request to populate a form with transaction data."""

    transaction_id: UUID
    include_extracted_data: bool = True


class PopulateFormResponse(BaseModel):
    """Response with populated form data."""

    template_id: str
    template_name: str
    form_number: str
    populated_fields: dict[str, Any]
    missing_required: list[str]
    is_complete: bool
    populated_at: str


class DisclosureChecklistResponse(BaseModel):
    """Response with disclosure requirements checklist."""

    transaction_id: str
    disclosures: list[dict[str, Any]]
    total_required: int


@router.get("/templates", response_model=FormListResponse)
async def list_form_templates(
    category: str | None = None,
    current_user: CurrentUserDep = None,  # REM-003: Use typed CurrentUserDep
) -> FormListResponse:
    """
    List available Florida form templates.

    Optionally filter by category: contract, rider, addendum, disclosure, closing, financial
    """
    if category:
        try:
            cat = FormCategory(category)
            templates = get_templates_by_category(cat)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    else:
        templates = list(FL_FORM_TEMPLATES.values())

    forms = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category.value,
            "form_number": t.form_number,
            "version": t.version,
            "pages": t.pages,
            "field_count": len(t.fields),
            "required_for": t.required_for,
        }
        for t in templates
    ]

    return FormListResponse(forms=forms, total=len(forms))


@router.get("/templates/{template_id}")
async def get_form_template(
    template_id: str,
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> dict[str, Any]:
    """
    Get detailed form template including all field definitions.
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category.value,
        "form_number": template.form_number,
        "version": template.version,
        "pages": template.pages,
        "source": template.source,
        "required_for": template.required_for,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "type": f.field_type.value,
                "required": f.required,
                "default": f.default,
            }
            for f in template.fields
        ],
    }


@router.post("/populate/{template_id}", response_model=PopulateFormResponse)
async def populate_form(
    template_id: str,
    request: PopulateFormRequest,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> PopulateFormResponse:
    """
    Populate a form template with transaction data.

    Returns populated field values and identifies any missing required fields.
    """
    # Get transaction
    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        request.transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute, not dict key
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Build transaction data for form population
    transaction_data = {
        "property_address": transaction.property_address,
        "purchase_price": float(transaction.purchase_price) if transaction.purchase_price else None,
        "year_built": transaction.year_built,
        "effective_date": transaction.effective_date,
        "closing_date": transaction.closing_date,
        "parties": transaction.parties or [],
        "is_hoa": transaction.is_hoa,
        "is_condo": transaction.is_condo,
        "is_financed": transaction.is_financed,
    }

    # Get extracted data from documents if requested
    extracted_data = {}
    if request.include_extracted_data and transaction.documents:
        for doc in transaction.documents:
            if doc.extracted_data and doc.status in ["extracted", "verified"]:
                extracted_data.update(doc.extracted_data)

    # Populate form
    form_service = get_form_service()
    try:
        result = form_service.populate_form(
            template_id,
            transaction_data,
            extracted_data,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PopulateFormResponse(**result)


@router.get("/required/{transaction_id}")
async def get_required_forms(
    transaction_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> dict[str, Any]:
    """
    Get list of required forms for a transaction based on its characteristics.
    """
    # Get transaction
    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    from packages.forms.templates import get_required_templates

    required = get_required_templates(
        is_residential=True,
        year_built=transaction.year_built,
        is_hoa=transaction.is_hoa,
        is_condo=transaction.is_condo,
    )

    return {
        "transaction_id": str(transaction_id),
        "required_forms": [
            {
                "id": t.id,
                "name": t.name,
                "form_number": t.form_number,
                "category": t.category.value,
            }
            for t in required
        ],
        "total": len(required),
    }


@router.get("/disclosures/{transaction_id}", response_model=DisclosureChecklistResponse)
async def get_disclosure_requirements(
    transaction_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> DisclosureChecklistResponse:
    """
    Get required disclosure checklist for a transaction.
    """
    # Get transaction
    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Build transaction data for disclosure check
    transaction_data = {
        "year_built": transaction.year_built,
        "is_hoa": transaction.is_hoa,
        "is_condo": transaction.is_condo,
    }

    checklist = get_disclosure_checklist(transaction_data)

    return DisclosureChecklistResponse(
        transaction_id=str(transaction_id),
        disclosures=checklist,
        total_required=len(checklist),
    )


@router.post("/populate-all/{transaction_id}")
async def populate_all_required_forms(
    transaction_id: UUID,
    db: DbSessionDep,  # REM-003: Use typed dependency
    current_user: CurrentUserDep,  # REM-003: Use typed CurrentUserDep
) -> dict[str, Any]:
    """
    Populate all required forms for a transaction.

    Returns population results for each required form.
    """
    # Get transaction
    tx_service = TransactionService(db)
    transaction = await tx_service.get_transaction(
        transaction_id,
        current_user.organization_id,  # REM-003: Access as attribute
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Build transaction data
    transaction_data = {
        "property_address": transaction.property_address,
        "purchase_price": float(transaction.purchase_price) if transaction.purchase_price else None,
        "year_built": transaction.year_built,
        "effective_date": transaction.effective_date,
        "closing_date": transaction.closing_date,
        "parties": transaction.parties or [],
        "is_hoa": transaction.is_hoa,
        "is_condo": transaction.is_condo,
        "is_financed": transaction.is_financed,
    }

    # Get extracted data
    extracted_data = {}
    if transaction.documents:
        for doc in transaction.documents:
            if doc.extracted_data and doc.status in ["extracted", "verified"]:
                extracted_data.update(doc.extracted_data)

    # Populate all required forms
    form_service = get_form_service()
    results = form_service.populate_all_required_forms(transaction_data, extracted_data)

    complete_count = sum(1 for r in results if r.get("is_complete", False))

    return {
        "transaction_id": str(transaction_id),
        "forms": results,
        "total": len(results),
        "complete": complete_count,
        "incomplete": len(results) - complete_count,
    }
