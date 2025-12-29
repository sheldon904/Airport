# Vision Alignment Analysis: Airport TC Platform

## Executive Summary

This document provides a comprehensive analysis of the Airport Transaction Coordinator platform against the original client vision captured during discovery interviews. The analysis identifies alignment strengths, gaps, and recommends specific modifications to better serve the core use case: **making real estate transaction coordination cheaper than Transactly, smarter than Dotloop, while protecting sensitive information and keeping TCs on top of critical deadlines.**

---

## Original Vision Requirements (Interview Notes)

| # | Requirement | Category |
|---|-------------|----------|
| 1 | CRM integration | Integration |
| 2 | Cheaper than Transactly, smarter than Dotloop | Competitive Positioning |
| 3 | Personal information and PII is a concern - redaction of names/addresses | Privacy & Security |
| 4 | Addendums/riders/disclosures need to be kept private | Document Privacy |
| 5 | Addendums/riders/disclosures written by attorneys - just populating values (no legalese generation) | Document Population |
| 6 | Fully executed contract + FE addendum/riders become keeper of those docs | Document Repository |
| 7 | Socialize dates, terms to seller, copy listing agent, title insurance company | External Party Communication |
| 8 | Title insurance company deals with transfer throughout process; several checkpoints | Title Company Coordination |
| 9 | TC tracks deadlines (inspection period, loan appreciation dates, closing, etc.) | Deadline Tracking |
| 10 | Key dates approaching, deadlines extracted from documents | Deadline Extraction |
| 11 | Bad communication tracking - "where are we with the receipt for the deposit" | Communication Tracking |
| 12 | Dashboards showing what you need to be on top of | Priority Dashboard |
| 13 | Adapting with pulse or work in terms of priority levels | Priority Management |

---

## Alignment Analysis

### FULLY ALIGNED (Core Strengths)

#### 1. Deadline Tracking (Requirement #9) - **EXCELLENT**

**Current State:**
- Comprehensive `DeadlineAgent` with 15+ Florida statutory deadlines
- TRID-compliant business day calculator with federal holiday awareness
- Reminder scheduling with configurable days (7, 3, 1 day alerts)
- Deadline status tracking (upcoming, due_soon, overdue, completed, waived)
- Scheduler service running hourly checks with 5-minute reminder intervals

**Evidence:**
```python
# packages/compliance/florida.py
FL_STATUTORY_DEADLINES = {
    "seller_disclosure": 3,      # F.S. 689.25
    "radon_disclosure": 0,       # F.S. 404.056
    "hoa_disclosure": 3,         # F.S. 720.401
    "inspection_period": 15,     # FAR/BAR standard
    "financing_deadline": 30,    # FAR/BAR standard
    "closing_disclosure": -3,    # 12 CFR 1026.19(f)
    # ... 15+ more statutory deadlines
}
```

**Assessment:** This is the strongest alignment with the vision. The system excels at the core TC pain point of deadline tracking.

---

#### 2. Deadline Extraction from Documents (Requirement #10) - **STRONG**

**Current State:**
- `DocumentExtractAgent` parses PDFs and images using Claude API
- Extracts: effective date, closing date, contingency deadlines
- Calculates relative deadlines (e.g., "inspection within 10 days")
- Human review queue for low-confidence extractions

**Evidence:**
```python
# services/agents/document_extract/agent.py
class ExtractedContingency(BaseModel):
    contingency_type: str
    deadline_date: date | None
    days_from_effective: int | None
    description: str
    waived: bool = False
```

**Assessment:** Strong foundation. The extraction agent properly identifies dates and calculates deadlines from contract language.

---

#### 3. Document Repository (Requirement #6) - **STRONG**

**Current State:**
- S3-compatible storage with tenant isolation
- Document types include: `ADDENDUM`, `AMENDMENT`, `CLOSING_DISCLOSURE`, etc.
- Soft delete for compliance retention (5 years per F.S. 475.5015)
- Comprehensive audit logging for document actions
- Document status workflow: uploaded → processing → extracted → verified

**Assessment:** Good foundation for "keeper of docs" role. Documents are properly stored, versioned, and retained for compliance.

---

#### 4. Dashboard Overview (Requirement #12) - **ADEQUATE**

**Current State:**
- Dashboard shows: active transactions, pending deadlines, documents needing review
- Transaction list with status indicators
- Upcoming deadline widget (7-day lookahead)
- Review queue alert banner

**Gaps Identified:**
- No priority-based sorting or "pulse" view
- No "hot spots" or items needing immediate attention
- Missing deposit/earnest money tracking visibility

---

### PARTIALLY ALIGNED (Needs Enhancement)

#### 5. External Party Communication (Requirement #7) - **PARTIAL**

**Current State:**
- `CommunicationAgent` drafts templated emails
- Party roles defined: buyer, seller, buyer_agent, seller_agent, lender, title_company
- Templates include closing updates, deadline reminders, status updates
- All communications require human review before sending

**Gaps:**
- No mechanism for external parties to **receive** updates without TC intervention
- No portal for sellers/buyers to view their transaction status
- No ability to "copy" parties on communications automatically
- No tracking of what communications have been sent to whom

**Evidence of Limitation:**
```python
# Communication templates list recipients but don't auto-send to external parties
recipients=["buyer", "seller", "buyer_agent", "seller_agent", "lender", "title_company"]
```

---

#### 6. Title Company Coordination (Requirement #8) - **PARTIAL**

**Current State:**
- `title_company` is a valid party role
- Title-related deadlines tracked (title commitment, title examination)
- Documents can be categorized as `TITLE_COMMITMENT`

**Gaps:**
- No dedicated title company portal or integration
- No checkpoint tracking specific to title company milestones
- No ability for title company to update transaction status directly
- No "wire fraud" protection workflows

---

#### 7. Priority Management (Requirement #13) - **PARTIAL**

**Current State:**
- Notification priority levels: LOW, NORMAL, HIGH, URGENT, CRITICAL
- Job queue has priority field for background processing
- Deadlines have status (overdue is implicitly high priority)

**Gaps:**
- Transactions themselves have no priority/urgency field
- Dashboard doesn't sort by urgency or "pulse"
- No "fire" indicators for transactions with multiple issues
- No configurable priority rules (e.g., "first-time homebuyer = high priority")

---

### NOT IMPLEMENTED (Major Gaps)

#### 8. CRM Integration (Requirement #1) - **MISSING**

**Current State:**
- No CRM functionality
- Parties stored as JSONB within transactions
- No contact history across transactions
- No lead/prospect tracking

**Impact:** Users must maintain separate CRM, creating data duplication and workflow friction.

---

#### 9. PII Redaction (Requirement #3) - **MISSING**

**Current State:**
- No PII detection or redaction capabilities
- Names, addresses, SSNs stored in plain text in extracted_data
- No audit trail specifically for PII access
- No role-based data masking

**Evidence of Vulnerability:**
```python
# Extracted party data contains PII without protection
class ExtractedParty(BaseModel):
    role: str
    name: str          # PII: Full name
    email: str | None  # PII: Email
    phone: str | None  # PII: Phone number
```

**Impact:** Significant compliance risk for CCPA, potential liability for data breaches.

---

#### 10. Document Privacy for Addendums/Riders/Disclosures (Requirement #4) - **MISSING**

**Current State:**
- All documents have same access level within organization
- No document-level access controls
- No "confidential" document classification
- No attorney-client privilege indicators

**Impact:** Sensitive negotiation documents visible to all organization members.

---

#### 11. Template/Form Population (Requirement #5) - **MISSING**

**Current State:**
- System extracts data FROM documents
- No ability to populate data INTO templates
- No form library for addendums/riders
- No integration with form providers (ZipForms, dotloop forms)

**This is a significant gap.** The vision explicitly states attorneys write the documents and the system should "just populate values." Currently, there's no form population workflow.

---

#### 12. Communication Tracking (Requirement #11) - **MISSING**

**Current State:**
- Communications drafted but not tracked after approval
- No "conversation thread" per transaction
- No ability to answer "where are we with the deposit receipt?"
- No inbound communication parsing (email-to-transaction)

**Impact:** TCs cannot use the system as single source of truth for communication history.

---

### Competitive Positioning Analysis (Requirement #2)

**"Cheaper than Transactly, smarter than Dotloop"**

| Feature | Transactly | Dotloop | Airport TC |
|---------|-----------|---------|------------|
| **Pricing Model** | $250-400/transaction | $29+/mo subscription | $49-349/mo tiers |
| **AI Extraction** | Manual entry | Basic | Claude-powered |
| **Deadline Tracking** | Basic | Basic | TRID-compliant, auto-calculated |
| **Form Population** | Yes | Yes | **MISSING** |
| **E-signature** | Integrated | Core feature | **MISSING** |
| **CRM** | No | No | **MISSING** |
| **External Portals** | Yes | Yes | **MISSING** |
| **Compliance Focus** | General | General | FL-specific (advantage) |

**Assessment:** Airport TC is "smarter" in AI extraction and compliance automation, but lacks the form population and e-signature workflows that are table stakes for competitors.

---

## Recommended Modifications

### Priority 1: Critical Gaps (Address Immediately)

#### 1.1 Form Population Engine

**What to Build:**
```
packages/forms/
├── engine.py           # Form population engine
├── templates/          # Standard FL forms (FAR/BAR)
│   ├── far_bar_as_is.json
│   ├── addendum_inspection.json
│   └── disclosure_seller.json
├── fields.py           # Field mapping definitions
└── integration/
    └── zipforms.py     # ZipForms API integration
```

**Key Features:**
- Extract data from documents → populate blank forms
- Map extracted parties, dates, addresses to form fields
- Generate PDFs with populated values
- Mark populated forms as "draft - review required"

**Integration Points:**
- ZipForms integration for form library access
- dotloop/SkySlope for form submission

---

#### 1.2 PII Redaction Service

**What to Build:**
```
packages/privacy/
├── pii_detector.py     # Detect PII in text/documents
├── redactor.py         # Redact/mask PII
├── access_log.py       # PII access audit trail
└── config.py           # PII policies
```

**Key Features:**
- Detect SSN, phone, email, addresses using regex + NER
- Store redacted versions for external sharing
- Role-based access: full data vs redacted
- PII access logging for compliance

**Database Changes:**
```sql
ALTER TABLE documents ADD COLUMN has_pii BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN pii_fields JSONB;
ALTER TABLE documents ADD COLUMN redacted_storage_path VARCHAR(500);
```

---

#### 1.3 Document Access Control

**What to Build:**

**Database Changes:**
```sql
CREATE TABLE document_access_rules (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    access_level VARCHAR(50), -- 'organization', 'transaction_parties', 'restricted'
    allowed_roles VARCHAR[] DEFAULT ARRAY['admin', 'broker'],
    is_confidential BOOLEAN DEFAULT FALSE,
    requires_nda BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Key Features:**
- Mark addendums/riders as "confidential" or "restricted"
- Control which party roles can view specific documents
- Require acknowledgment before viewing sensitive documents
- Audit all document access

---

### Priority 2: Important Enhancements (Next Phase)

#### 2.1 CRM Integration

**Approach:** Lightweight contact management + external CRM sync

**What to Build:**
```
packages/crm/
├── contacts.py         # Contact model and service
├── sync/
│   ├── follow_up_boss.py
│   ├── hubspot.py
│   └── kvcore.py
└── history.py          # Interaction history
```

**Database Changes:**
```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    full_name VARCHAR(255),
    contact_type VARCHAR(50), -- 'buyer', 'seller', 'agent', 'lender', etc.
    source VARCHAR(100),      -- 'manual', 'extraction', 'crm_sync'
    external_crm_id VARCHAR(255),
    external_crm_type VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE contact_interactions (
    id UUID PRIMARY KEY,
    contact_id UUID REFERENCES contacts(id),
    transaction_id UUID REFERENCES transactions(id),
    interaction_type VARCHAR(50), -- 'email_sent', 'call', 'document_shared'
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Key Features:**
- Auto-create contacts from extracted party data
- Link contacts across multiple transactions
- Sync with popular real estate CRMs (Follow Up Boss, KvCORE)
- Track all interactions for "where are we with..." queries

---

#### 2.2 Communication Thread Tracking

**What to Build:**
```
packages/core/services/communication_log.py
```

**Database Changes:**
```sql
CREATE TABLE communication_log (
    id UUID PRIMARY KEY,
    transaction_id UUID REFERENCES transactions(id),
    direction VARCHAR(10), -- 'inbound', 'outbound'
    channel VARCHAR(50),   -- 'email', 'sms', 'portal'
    sender_email VARCHAR(255),
    recipient_emails VARCHAR[],
    subject VARCHAR(500),
    body_preview VARCHAR(1000),
    full_body TEXT,
    attachments JSONB DEFAULT '[]',
    related_to VARCHAR(100), -- 'earnest_money', 'inspection', 'closing'
    status VARCHAR(50),
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_comm_log_transaction ON communication_log(transaction_id);
CREATE INDEX ix_comm_log_related ON communication_log(related_to);
```

**Key Features:**
- Log all outbound communications
- Parse inbound emails (via email forwarding address)
- Tag communications by topic ("earnest money", "inspection", etc.)
- Enable queries: "Show me all communications about the deposit"
- Generate communication timeline per transaction

---

#### 2.3 External Party Portal

**What to Build:**
```
web/app/portal/
├── [token]/
│   ├── page.tsx        # Portal landing
│   ├── documents/page.tsx
│   ├── timeline/page.tsx
│   └── updates/page.tsx
└── components/
    └── PortalLayout.tsx
```

**API Additions:**
```python
# services/api/routers/portal.py
@router.get("/portal/{access_token}")
async def get_portal_data(access_token: str):
    """Get transaction data for external party portal."""

@router.get("/portal/{access_token}/documents")
async def get_portal_documents(access_token: str):
    """Get documents visible to external party (with redaction applied)."""
```

**Key Features:**
- Generate secure, time-limited access tokens for external parties
- Show transaction timeline (dates, milestones, status)
- Display documents shared with that party (redacted as appropriate)
- Allow document upload from portal
- Send automatic notifications when status changes
- "Socialize dates, terms to seller, copy listing agent, title insurance company"

---

#### 2.4 Priority/Pulse Dashboard Enhancement

**What to Build:**

**Database Changes:**
```sql
ALTER TABLE transactions ADD COLUMN priority VARCHAR(50) DEFAULT 'normal';
ALTER TABLE transactions ADD COLUMN priority_score INTEGER DEFAULT 50;
ALTER TABLE transactions ADD COLUMN health_status VARCHAR(50) DEFAULT 'on_track';
```

**API Changes:**
```python
# packages/core/services/priority.py
class PriorityService:
    async def calculate_transaction_priority(self, tx_id: UUID) -> int:
        """
        Calculate priority score (0-100) based on:
        - Days to closing
        - Number of overdue deadlines
        - Documents pending review
        - Missing required documents
        - Unanswered communications
        """

    async def get_pulse_dashboard(self, org_id: UUID) -> list:
        """
        Return transactions sorted by urgency with "heat" indicators:
        - RED: Multiple overdue items or closing < 3 days
        - YELLOW: Overdue items or closing < 7 days
        - GREEN: All on track
        """
```

**Frontend Changes:**
- Add priority filter/sort to transaction list
- Add "pulse" indicator (red/yellow/green circles)
- Add "needs attention" section at top of dashboard
- Show count badges: "3 overdue deadlines", "2 pending reviews"

---

### Priority 3: Competitive Parity Features (Future)

#### 3.1 E-Signature Integration

**Integrations to Add:**
- DocuSign API
- dotloop native
- Authentisign
- SkySlope Forms

**Workflow:**
1. Generate populated form from extraction
2. Send for e-signature via preferred provider
3. Track signature status
4. Auto-import signed document back to transaction
5. Update checklist automatically

---

#### 3.2 Title Company Integration

**What to Build:**
```
packages/integrations/title/
├── base.py             # Abstract title company interface
├── softpro.py          # SoftPro integration
├── ramquest.py         # RamQuest integration
└── endpoints.py        # Webhook receivers
```

**Key Features:**
- Receive title commitment status updates
- Track title clearance milestones
- Wire fraud prevention workflows
- Closing disclosure reconciliation

---

## Implementation Roadmap

### Phase 1: Privacy & Security (Weeks 1-3)
1. PII detection and redaction service
2. Document access control system
3. Role-based data masking
4. PII access audit logging

### Phase 2: Form Population (Weeks 4-6)
1. Form template engine
2. ZipForms integration
3. Populated form generation
4. Form submission workflow

### Phase 3: Communication Enhancement (Weeks 7-9)
1. Communication log database
2. Email parsing (inbound)
3. Communication timeline view
4. "Related to" tagging

### Phase 4: External Portals (Weeks 10-12)
1. Secure portal token system
2. External party portal frontend
3. Document sharing with redaction
4. Status notification automation

### Phase 5: CRM & Priority (Weeks 13-16)
1. Contact database and service
2. Priority scoring algorithm
3. Pulse dashboard view
4. CRM sync integrations

---

## Success Metrics

### User Adoption
| Metric | Current | Target |
|--------|---------|--------|
| Form population usage | 0% | 80% of transactions |
| Portal invitations sent | 0 | 5+ per transaction |
| Communication tracking | N/A | 100% logged |
| PII redaction applied | 0% | 100% external shares |

### Competitive Position
| Metric | Current | Target |
|--------|---------|--------|
| Feature parity with Transactly | ~60% | 90% |
| Feature parity with dotloop | ~50% | 85% |
| "Smarter" AI features | Strong | Maintain lead |
| Price competitiveness | $49-349/mo | Maintain advantage |

---

## Conclusion

The Airport TC platform has an **excellent foundation** in AI-powered deadline extraction and compliance tracking - areas where it genuinely exceeds competitors. However, the system lacks several **table-stakes features** that the original vision identified:

1. **Form population** - Critical for "just populating values" workflow
2. **PII protection** - Essential for compliance and trust
3. **External party portals** - Required for "socializing" information
4. **Communication tracking** - Key to answering "where are we with..."

The recommended modifications transform Airport TC from an internal deadline tracker into a **complete transaction coordination platform** that fulfills the original vision of being "cheaper than Transactly, smarter than Dotloop" while addressing the privacy concerns expressed in the discovery interviews.

Priority should be given to:
1. PII redaction (compliance risk mitigation)
2. Form population (competitive parity)
3. Communication tracking (core TC workflow)
4. External portals (differentiation opportunity)

With these additions, Airport TC would deliver on its promise of automating 65-75% of routine TC work while providing the intelligence and privacy controls that modern real estate professionals require.
