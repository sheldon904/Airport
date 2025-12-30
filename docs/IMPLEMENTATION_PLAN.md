# Implementation Plan: Vision Alignment

## Guiding Principles

1. **Extend, don't rebuild** - Add to existing services and models
2. **JSONB for flexibility** - Use existing pattern of JSONB columns over new tables
3. **FL forms are templated** - Store form definitions as JSON, not complex schema
4. **Minimal migration risk** - Additive changes only, no breaking changes

---

## Phase 1: PII Protection & Document Privacy (Week 1-2)

### 1.1 PII Redaction Service

**Add to existing services:**

```
packages/core/services/privacy.py    # NEW FILE
```

**Implementation approach:**
- Regex-based detection for SSN, phone, email patterns
- Store redacted version alongside original in `extracted_data`
- Add `redacted_extracted_data` JSONB field to documents table

**Database change (single migration):**
```sql
ALTER TABLE documents ADD COLUMN redacted_data JSONB;
ALTER TABLE documents ADD COLUMN pii_detected JSONB DEFAULT '[]';
```

**Service pattern (follows existing DocumentService):**
```python
class PrivacyService:
    PII_PATTERNS = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    }

    def redact_extracted_data(self, data: dict) -> tuple[dict, list[str]]:
        """Returns (redacted_data, list_of_pii_fields_found)"""

    def get_safe_data(self, document_id: UUID, user_role: str) -> dict:
        """Returns full or redacted data based on role"""
```

**Integration point:** Call from `DocumentService.record_extraction_result()`

---

### 1.2 Document Access Control

**Extend existing DocumentModel (no new table):**

```sql
ALTER TABLE documents ADD COLUMN access_level VARCHAR(50) DEFAULT 'organization';
ALTER TABLE documents ADD COLUMN is_confidential BOOLEAN DEFAULT FALSE;
```

**Access levels:**
- `organization` - All org members can view (default, current behavior)
- `transaction_parties` - Only users assigned to transaction
- `restricted` - Admin/broker only

**Extend DocumentService:**
```python
async def get_document(self, document_id, organization_id, user_id, user_role):
    # Existing logic +
    if document.is_confidential and user_role not in ('admin', 'broker'):
        raise AuthorizationError("Document is confidential")
    if document.access_level == 'restricted':
        # Check user is transaction party
```

**Auto-classify on upload:**
```python
CONFIDENTIAL_TYPES = ['addendum', 'amendment', 'counteroffer']

def _should_be_confidential(self, document_type: str) -> bool:
    return document_type.lower() in CONFIDENTIAL_TYPES
```

---

## Phase 2: Form Population (Week 2-3)

### 2.1 Form Template Storage

**Key insight:** FL forms (FAR/BAR) are standardized. Store as JSON field mappings.

**New file structure:**
```
packages/forms/
├── __init__.py
├── templates.py      # Form definitions as Python dicts
├── populate.py       # Population logic
└── pdf_generator.py  # PDF output using reportlab or pypdf
```

**Form template format (no database needed - code-defined like FL_STATUTORY_DEADLINES):**
```python
FL_FORM_TEMPLATES = {
    "far_bar_as_is_2024": {
        "name": "FAR/BAR As-Is Contract",
        "version": "2024",
        "source_pdf": "templates/far_bar_as_is_2024.pdf",
        "field_mappings": {
            # PDF field name -> extraction path
            "BuyerName1": "parties[?role=='buyer'].name | [0]",
            "SellerName1": "parties[?role=='seller'].name | [0]",
            "PropertyAddress": "property_address.street",
            "PropertyCity": "property_address.city",
            "PurchasePrice": "purchase_price",
            "ClosingDate": "closing_date",
            "EffectiveDate": "effective_date",
            "EarnestMoney": "earnest_money",
            # ... 50+ fields mapped
        }
    },
    "addendum_inspection": {
        "name": "Inspection Period Addendum",
        "field_mappings": { ... }
    },
    "disclosure_seller": {
        "name": "Seller's Property Disclosure",
        "field_mappings": { ... }
    }
}
```

### 2.2 Population Service

```python
# packages/forms/populate.py

class FormPopulationService:
    def populate_form(
        self,
        template_id: str,
        transaction_data: dict,
        extracted_data: dict,
    ) -> bytes:
        """
        Populate a form template with transaction/extraction data.
        Returns PDF bytes.
        """
        template = FL_FORM_TEMPLATES[template_id]

        # Merge data sources
        combined = {**transaction_data, **extracted_data}

        # Map fields
        field_values = {}
        for pdf_field, data_path in template["field_mappings"].items():
            field_values[pdf_field] = self._extract_value(combined, data_path)

        # Generate PDF
        return self._fill_pdf(template["source_pdf"], field_values)

    def _fill_pdf(self, template_path: str, values: dict) -> bytes:
        """Use pypdf to fill PDF form fields"""
```

### 2.3 API Endpoint

**Add to existing documents router:**
```python
# services/api/routers/documents.py

@router.post("/populate/{template_id}")
async def populate_form(
    template_id: str,
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a populated form from transaction data"""
    # Get transaction + extracted data
    # Call FormPopulationService
    # Return PDF or save as new document
```

---

## Phase 3: Communication Tracking (Week 3-4)

### 3.1 Communication Log

**Single new table (unavoidable for proper tracking):**

```sql
CREATE TABLE communication_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id),

    -- Message details
    direction VARCHAR(10) NOT NULL,  -- 'outbound', 'inbound'
    channel VARCHAR(20) DEFAULT 'email',
    subject VARCHAR(500),
    body_preview VARCHAR(500),

    -- Participants
    sender VARCHAR(255),
    recipients JSONB DEFAULT '[]',

    -- Categorization
    topic VARCHAR(100),  -- 'earnest_money', 'inspection', 'closing', 'general'

    -- Status
    status VARCHAR(50) DEFAULT 'sent',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_comm_log_tx ON communication_log(transaction_id);
CREATE INDEX ix_comm_log_topic ON communication_log(topic);
```

### 3.2 Auto-Categorization

**Extend CommunicationAgent:**
```python
TOPIC_KEYWORDS = {
    'earnest_money': ['deposit', 'earnest', 'escrow', 'receipt'],
    'inspection': ['inspection', 'inspector', 'repair', 'defect'],
    'financing': ['loan', 'lender', 'mortgage', 'approval', 'underwriting'],
    'closing': ['closing', 'settlement', 'title', 'deed', 'wire'],
    'appraisal': ['appraisal', 'appraiser', 'value'],
}

def categorize_communication(self, subject: str, body: str) -> str:
    text = f"{subject} {body}".lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return topic
    return 'general'
```

### 3.3 "Where are we with..." Query

**Add to transactions router:**
```python
@router.get("/{transaction_id}/communications")
async def get_transaction_communications(
    transaction_id: UUID,
    topic: str | None = None,  # Filter by topic
):
    """Get communication history for a transaction"""

@router.get("/{transaction_id}/communications/summary")
async def get_communication_summary(transaction_id: UUID):
    """
    Returns: {
        'earnest_money': {'last_sent': '2024-12-20', 'count': 3, 'status': 'awaiting_response'},
        'inspection': {'last_sent': '2024-12-22', 'count': 5, 'status': 'complete'},
        ...
    }
    """
```

---

## Phase 4: Priority Dashboard (Week 4-5)

### 4.1 Transaction Health Scoring

**Extend TransactionModel (no new table):**
```sql
ALTER TABLE transactions ADD COLUMN priority_score INTEGER DEFAULT 50;
ALTER TABLE transactions ADD COLUMN health_status VARCHAR(20) DEFAULT 'on_track';
```

**Health calculation service:**
```python
# packages/core/services/priority.py

class PriorityService:
    def calculate_health(self, transaction_id: UUID) -> tuple[int, str]:
        """
        Returns (score 0-100, status).

        Factors:
        - Days to closing (closer = higher priority)
        - Overdue deadlines (each adds 20 points)
        - Documents pending review (each adds 10 points)
        - Missing required documents (each adds 15 points)
        - Unanswered communications > 48h (adds 10 points)
        """
        score = 50  # baseline

        # Days to closing
        if days_to_close <= 3:
            score += 30
        elif days_to_close <= 7:
            score += 20
        elif days_to_close <= 14:
            score += 10

        # Overdue deadlines
        score += overdue_count * 20

        # Pending reviews
        score += pending_review_count * 10

        # Determine status
        if score >= 80:
            status = 'critical'
        elif score >= 60:
            status = 'attention'
        else:
            status = 'on_track'

        return min(score, 100), status
```

### 4.2 Dashboard Enhancement

**Extend existing dashboard endpoint:**
```python
# packages/core/services/transaction.py

async def get_dashboard_summary(self, organization_id: UUID) -> dict:
    # Existing fields +
    return {
        ...existing...,
        "needs_attention": [
            # Transactions with health_status != 'on_track'
            {"id": "...", "address": "...", "issues": ["2 overdue deadlines", "deposit receipt pending"]}
        ],
        "by_priority": {
            "critical": 2,
            "attention": 5,
            "on_track": 12
        }
    }
```

**Frontend: Add to dashboard page:**
```tsx
{/* Priority Section - Add above recent transactions */}
<div className="rounded-lg bg-red-50 border-l-4 border-red-500 p-4 mb-6">
  <h3>Needs Immediate Attention ({needsAttention.length})</h3>
  {needsAttention.map(tx => (
    <div key={tx.id} className="flex justify-between">
      <span>{tx.address}</span>
      <span className="text-red-600">{tx.issues.join(', ')}</span>
    </div>
  ))}
</div>
```

---

## Phase 5: External Party Portal (Week 5-6)

### 5.1 Portal Access Tokens

**Extend parties JSONB (no new table):**

Currently parties are stored as:
```json
{"role": "seller", "name": "John Doe", "email": "john@example.com"}
```

Extend to:
```json
{
  "role": "seller",
  "name": "John Doe",
  "email": "john@example.com",
  "portal_token": "abc123...",
  "portal_token_expires": "2025-02-01",
  "portal_last_accessed": "2025-01-15"
}
```

**Token service:**
```python
# packages/core/services/portal.py

class PortalService:
    def generate_portal_token(self, transaction_id: UUID, party_email: str) -> str:
        """Generate secure token for external party access"""
        payload = {
            "tx": str(transaction_id),
            "email": party_email,
            "exp": datetime.now() + timedelta(days=30)
        }
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    def get_portal_data(self, token: str) -> dict:
        """Get transaction data visible to external party"""
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

        # Get transaction with filtered data
        return {
            "property_address": tx.property_address,
            "status": tx.status,
            "closing_date": tx.closing_date,
            "deadlines": [...],  # Relevant deadlines only
            "documents": [...],  # Documents shared with this party (redacted)
            "timeline": [...]    # Key milestones
        }
```

### 5.2 Portal API Routes

**New router (minimal):**
```python
# services/api/routers/portal.py

router = APIRouter()

@router.get("/p/{token}")
async def get_portal_view(token: str):
    """Public endpoint - no auth required, token validates access"""
    return await portal_service.get_portal_data(token)

@router.get("/p/{token}/documents/{doc_id}")
async def get_portal_document(token: str, doc_id: UUID):
    """Download document (redacted version)"""
```

### 5.3 Portal Frontend

**Minimal new pages:**
```
web/app/p/[token]/
├── page.tsx           # Transaction overview
├── documents/page.tsx # Shared documents
└── layout.tsx         # Simple layout (no sidebar)
```

**Notification on status change:**
```python
# Extend existing NotificationAgent
async def notify_portal_parties(self, transaction_id: UUID, status_change: str):
    """Send email to all parties with portal links when status changes"""
```

---

## Phase 6: Lightweight CRM (Week 6-7)

### 6.1 Contact Deduplication

**Single new table:**
```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255),
    phone VARCHAR(20),
    full_name VARCHAR(255),
    contact_type VARCHAR(50),  -- 'buyer', 'seller', 'agent', 'lender', etc.

    -- Aggregated from transactions
    transaction_count INTEGER DEFAULT 0,
    last_transaction_id UUID,
    last_transaction_date DATE,

    -- Metadata
    notes TEXT,
    tags JSONB DEFAULT '[]',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(organization_id, email)
);
```

### 6.2 Auto-Create from Extraction

**Extend document extraction workflow:**
```python
# After extraction completes, upsert contacts
async def sync_parties_to_contacts(self, transaction_id: UUID, parties: list[dict]):
    for party in parties:
        if party.get('email'):
            await self.contact_repo.upsert(
                organization_id=org_id,
                email=party['email'],
                full_name=party['name'],
                contact_type=party['role'],
                last_transaction_id=transaction_id,
            )
```

### 6.3 Contact History View

**Add to transactions router:**
```python
@router.get("/contacts/{email}/history")
async def get_contact_history(email: str):
    """Get all transactions involving this contact"""
    return {
        "contact": {...},
        "transactions": [
            {"id": "...", "role": "buyer", "status": "closed", "date": "2024-06-15"},
            {"id": "...", "role": "buyer", "status": "active", "date": "2024-12-01"},
        ]
    }
```

---

## Database Migration Summary

**Single migration file covering all phases:**

```python
# alembic/versions/20241230_003_vision_alignment.py

def upgrade():
    # Phase 1: Privacy
    op.add_column('documents', sa.Column('redacted_data', JSONB))
    op.add_column('documents', sa.Column('pii_detected', JSONB, server_default='[]'))
    op.add_column('documents', sa.Column('access_level', sa.String(50), server_default='organization'))
    op.add_column('documents', sa.Column('is_confidential', sa.Boolean, server_default='false'))

    # Phase 4: Priority
    op.add_column('transactions', sa.Column('priority_score', sa.Integer, server_default='50'))
    op.add_column('transactions', sa.Column('health_status', sa.String(20), server_default='on_track'))

    # Phase 3: Communication Log (new table)
    op.create_table('communication_log', ...)

    # Phase 6: Contacts (new table)
    op.create_table('contacts', ...)
```

**Total new tables: 2** (communication_log, contacts)
**Total column additions: 6** (to existing tables)

---

## File Changes Summary

### New Files (12 files)
```
packages/core/services/privacy.py       # PII redaction
packages/core/services/portal.py        # Portal token management
packages/core/services/priority.py      # Health scoring
packages/forms/__init__.py
packages/forms/templates.py             # FL form definitions
packages/forms/populate.py              # Form population logic
packages/forms/pdf_generator.py         # PDF filling
services/api/routers/portal.py          # Portal endpoints
web/app/p/[token]/page.tsx             # Portal view
web/app/p/[token]/documents/page.tsx   # Portal documents
web/app/p/[token]/layout.tsx           # Portal layout
```

### Modified Files (8 files)
```
packages/db/models.py                   # Add columns
packages/core/services/__init__.py      # Export new services
packages/core/services/document.py      # Add privacy integration
services/api/main.py                    # Register portal router
services/api/routers/documents.py       # Add populate endpoint
services/api/routers/transactions.py    # Add communications endpoint
services/agents/communication/agent.py  # Add logging integration
web/app/dashboard/page.tsx              # Add priority section
```

---

## Implementation Order

| Week | Phase | Deliverable | Risk |
|------|-------|-------------|------|
| 1 | Privacy | PII redaction working, confidential docs flagged | Low |
| 2 | Forms | FAR/BAR As-Is form populates from extraction | Medium |
| 3 | Forms | 5 core FL forms templated and populatable | Medium |
| 4 | Comms | All outbound communications logged, topic tagged | Low |
| 5 | Priority | Dashboard shows health scores, "needs attention" | Low |
| 6 | Portal | External parties can view transaction status | Medium |
| 7 | CRM | Contacts auto-created, history viewable | Low |

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Extracted SSN/phone/email automatically redacted
- [ ] Addendums/amendments marked confidential by default
- [ ] Non-admin users cannot view confidential docs

### Phase 2 Complete When:
- [ ] FAR/BAR As-Is contract generates with 90%+ fields populated
- [ ] At least 5 FL standard forms templated
- [ ] Generated PDFs downloadable from transaction view

### Phase 3 Complete When:
- [ ] Every outbound email logged with topic
- [ ] "Where are we with deposit?" answerable via API
- [ ] Communication timeline visible in transaction detail

### Phase 4 Complete When:
- [ ] Dashboard shows red/yellow/green health indicators
- [ ] "Needs Attention" section at top of dashboard
- [ ] Transactions sortable by priority

### Phase 5 Complete When:
- [ ] Seller can view transaction via portal link
- [ ] Title company receives status updates automatically
- [ ] Portal shows timeline and shared documents

### Phase 6 Complete When:
- [ ] Contacts auto-created from extraction
- [ ] Repeat clients show transaction history
- [ ] Contact searchable across transactions
