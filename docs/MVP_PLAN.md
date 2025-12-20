# AI Transaction Coordinator MVP Plan

## Executive Summary

This document outlines the MVP plan for an AI-powered Transaction Coordinator (TC) platform targeting the Florida residential real estate market. The system uses containerized AI agents that spin up on-demand to handle administrative transaction tasks, designed from day one as a multi-tenant SaaS platform.

**Target Market**: Florida real estate agents and small teams ($300-500/transaction pain point)
**MVP Timeline Focus**: Core automation of 65-75% routine administrative work
**Architecture**: Container-orchestrated AI agents with human-in-the-loop checkpoints

---

## Phase 1: MVP Core (Launch Target)

### 1.1 Core Capabilities

| Feature | Description | Automation Level |
|---------|-------------|------------------|
| **Document Intake** | Upload contracts, disclosures, amendments | Full |
| **Data Extraction** | Parse dates, parties, contingencies, deadlines | Full |
| **Deadline Calendar** | Auto-generate compliance timeline from contract | Full |
| **Checklist Management** | FL-specific document requirements tracking | Full |
| **Status Communications** | Draft templated updates for all parties | AI-assisted |
| **Document Completeness** | Flag missing signatures, initials, disclosures | Full |
| **Human Review Queue** | Escalation system for judgment calls | Manual trigger |

### 1.2 Explicit Non-Goals (MVP)

- Contract interpretation or legal advice
- Negotiation assistance
- Custom clause drafting
- Multi-state support (Florida only)
- Commercial transactions
- Direct MLS integration

### 1.3 Florida Compliance Boundaries

**Permitted (Automate)**:
- Fill out forms and listings
- Follow up on loan commitments post-negotiation
- Assemble documents for closing
- Type/populate contract forms for licensee approval
- Schedule appointments
- Deliver documents
- Deadline tracking and reminders

**Prohibited (Never Automate)**:
- Negotiating any transaction aspect
- Discussing/advising on contract terms
- Answering subjective property questions
- Making compliance determinations without human review

---

## Phase 2: Architecture Overview

### 2.1 Container-Based Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                   (Auth, Rate Limiting, Routing)                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     Agent Orchestrator                           │
│              (Kubernetes / AWS ECS / Cloud Run)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Doc Extract  │ │  Deadline    │ │ Communication│             │
│  │    Agent     │ │   Agent      │ │    Agent     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Checklist   │ │  Review      │ │  Notification│             │
│  │    Agent     │ │   Agent      │ │    Agent     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     Shared Services                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Document    │ │  Transaction │ │   State      │             │
│  │   Store      │ │    State     │ │  Compliance  │             │
│  │   (S3)       │ │  (Postgres)  │ │   Engine     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent Design Principles

1. **Stateless Containers**: Each agent is a stateless container that can be scaled horizontally
2. **Event-Driven**: Agents respond to events (document uploaded, deadline approaching)
3. **Isolated Execution**: Each transaction gets isolated agent instances
4. **Human Checkpoints**: Agents pause and queue for review at defined decision points
5. **Audit Trail**: Every agent action is logged for compliance

### 2.3 Agent Types

| Agent | Trigger | Function | Output |
|-------|---------|----------|--------|
| **DocumentExtractAgent** | Document upload | Parse contract data using LLM | Structured transaction data |
| **DeadlineAgent** | Extraction complete | Calculate FL-compliant timelines | Calendar entries + reminders |
| **ChecklistAgent** | Transaction created | Track required documents | Completion status |
| **CommunicationAgent** | Status change / scheduled | Draft status updates | Email drafts for review |
| **ReviewAgent** | Flag raised | Queue items for human review | Review dashboard items |
| **NotificationAgent** | Various events | Send approved communications | Delivery confirmations |

---

## Phase 3: Technical Stack

### 3.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Container Runtime** | Docker | Industry standard, portable |
| **Orchestration** | Kubernetes (GKE/EKS) or Cloud Run | Auto-scaling, cost efficiency for bursty workloads |
| **API Layer** | FastAPI (Python) | Async, OpenAPI docs, Python ML ecosystem |
| **Agent Framework** | LangGraph or custom | Stateful agent workflows with checkpoints |
| **LLM Provider** | Claude API (Anthropic) | Strong document understanding |
| **Database** | PostgreSQL | Relational data, JSONB for flexibility |
| **Document Store** | S3-compatible | Cost-effective blob storage |
| **Queue/Events** | Redis Streams or SQS | Event-driven agent triggering |
| **Auth** | Auth0 or Clerk | Multi-tenant SaaS auth |
| **Frontend** | Next.js | React ecosystem, SSR |

### 3.2 Multi-Tenant SaaS Design

```
Tenant Isolation Strategy:
├── Database: Row-level security with tenant_id
├── Storage: Tenant-prefixed S3 paths
├── Agents: Tenant context passed in execution
├── Billing: Per-transaction metering
└── API: JWT with tenant claims
```

---

## Phase 4: Data Model (Core Entities)

### 4.1 Primary Entities

```
Organization (Brokerage/Team)
├── id, name, license_number, state
├── subscription_tier, billing_info
└── settings, compliance_config

User (Agent/Broker/Admin)
├── id, org_id, email, role
├── notification_preferences
└── permissions

Transaction
├── id, org_id, status, type
├── property_address, price
├── parties[] (buyer, seller, agents, lender, title)
├── created_at, target_close_date
└── current_phase

Document
├── id, transaction_id, type, filename
├── storage_path, upload_date
├── extraction_status, extracted_data (JSONB)
└── review_status

Deadline
├── id, transaction_id, type
├── date, source_document_id
├── reminder_schedule, status
└── completed_at, completed_by

Checklist
├── id, transaction_id, template_id
├── items[] (requirement, status, document_id)
└── completion_percentage

Communication
├── id, transaction_id, type
├── draft_content, final_content
├── recipients[], status
├── reviewed_by, sent_at

AuditLog
├── id, transaction_id, user_id
├── action, agent_type, details
└── timestamp
```

---

## Phase 5: MVP User Flows

### 5.1 Primary User Journey

```
1. Agent signs up → Organization created
2. Agent starts new transaction → Transaction shell created
3. Agent uploads executed contract → DocumentExtractAgent triggered
   ├── LLM extracts: parties, dates, contingencies, price
   ├── DeadlineAgent calculates timeline
   ├── ChecklistAgent initializes FL requirements
   └── Data queued for human verification
4. Agent reviews extracted data → Confirms or corrects
5. System monitors deadlines → Sends reminders
6. Agent uploads additional docs → Checklist updated
7. CommunicationAgent drafts updates → Agent reviews/sends
8. Transaction closes → Archived with full audit trail
```

### 5.2 Human-in-the-Loop Checkpoints

| Checkpoint | Trigger | Required Action |
|------------|---------|-----------------|
| Data Verification | Post-extraction | Confirm extracted dates/parties |
| Low Confidence Flag | LLM uncertainty > threshold | Manual review of flagged items |
| Communication Approval | Draft ready | Review and send/edit |
| Compliance Decision | Ambiguous requirement | Human determination |
| Exception Handling | Deadline conflict/issue | Manual resolution |

---

## Phase 6: MVP Pricing Model

### 6.1 Proposed Tiers

| Tier | Price | Transactions/mo | Features |
|------|-------|-----------------|----------|
| **Starter** | $49/mo | Up to 3 | Core extraction, deadlines, checklists |
| **Professional** | $149/mo | Up to 15 | + Communication drafting, integrations |
| **Team** | $349/mo | Up to 40 | + Multi-user, custom checklists |
| **Enterprise** | Custom | Unlimited | + API access, white-label, SLA |

### 6.2 Unit Economics Target

- **Cost per transaction**: $5-15 (LLM API + compute)
- **Target margin**: 70%+ at Professional tier
- **Break-even**: ~50 paying customers

---

## Phase 7: Integration Roadmap

### 7.1 MVP (Manual/Basic)
- Document upload (drag-and-drop, email forwarding)
- Calendar export (ICS)
- Email sending (SMTP)

### 7.2 Phase 2 Integrations
- DocuSign / dotloop (e-signature status)
- Google Calendar / Outlook sync
- Major Florida MLSs (property data)

### 7.3 Phase 3 Integrations
- Lone Wolf TransactionDesk
- SkySlope
- Title company portals
- Lender status APIs

---

## Phase 8: Compliance & Legal Structure

### 8.1 Required Legal Components

1. **Terms of Service**: Explicitly disclaim legal advice
2. **User Acknowledgment**: Periodic re-acknowledgment that:
   - Not a replacement for licensed TC services
   - User responsible for all compliance decisions
   - AI-generated content requires human review
3. **E&O Insurance**: TC-specific coverage (CRES Insurance)
4. **Cyber Liability**: Data breach and wire fraud coverage
5. **Broker Supervision Clause**: Product works under broker oversight

### 8.2 Audit Trail Requirements

Every action logged with:
- Timestamp
- Actor (user or agent type)
- Action taken
- Input data
- Output data
- Human review status

---

## Phase 9: Go-to-Market Strategy

### 9.1 Launch Market: Tampa Bay / Florida

**Why Florida First**:
- No TC licensing requirement for admin tasks
- High transaction volume
- Established TC service pricing ($350-400/transaction)
- Regulatory clarity from FREC

### 9.2 Initial Customer Acquisition

1. **Direct Outreach**: Individual agents closing 15-30 deals/year
2. **Real Estate Associations**: Tampa Bay REALTORS, Florida Realtors
3. **Content Marketing**: "How to save 15 hours per transaction"
4. **Referral Program**: Free month per referral

### 9.3 Success Metrics

| Metric | MVP Target |
|--------|------------|
| Active Organizations | 50 |
| Transactions Processed | 200/month |
| Time Saved per Transaction | 10+ hours |
| User NPS | 40+ |
| Churn Rate | <5% monthly |

---

## Phase 10: Risk Mitigation

### 10.1 Technical Risks

| Risk | Mitigation |
|------|------------|
| LLM hallucination | Confidence scoring, mandatory human review |
| Extraction errors | Structured output validation, user correction UI |
| Scalability | Container auto-scaling, queue-based processing |
| Data loss | Multi-region backup, point-in-time recovery |

### 10.2 Regulatory Risks

| Risk | Mitigation |
|------|------------|
| UPL claims | Strict functional limits, no legal interpretation |
| Unlicensed activity | Admin-only features, broker supervision model |
| Future regulation | Modular compliance engine, legal monitoring |
| Liability | E&O insurance, extensive disclaimers, audit trails |

### 10.3 Market Risks

| Risk | Mitigation |
|------|------------|
| Slow adoption | Start with pain point (deadline tracking) |
| TC pushback | Position as "assistant" not "replacement" |
| Platform competition | Deep workflow integration, switching costs |

---

## Appendix A: Florida-Specific Compliance Rules

### Required Disclosures (Track in Checklist)
- Lead-based paint disclosure (pre-1978 homes)
- Property tax disclosure
- HOA disclosure
- Radon gas disclosure
- Energy efficiency disclosure
- Coastal construction control line (if applicable)

### Standard Contingency Periods
- Inspection: 10-15 days typical
- Financing: 21-30 days typical
- Appraisal: Tied to financing
- Title: 5 days to cure defects

### Key FREC References
- § 475.01(1)(a): Definition of licensed activities
- § 475.25(1)(h): Broker liability for unlicensed assistants
- FREC Unlicensed Assistants Guidelines

---

## Appendix B: MVP Development Milestones

### Milestone 1: Foundation (Weeks 1-4)
- [ ] Project scaffolding and CI/CD
- [ ] Database schema and migrations
- [ ] Auth system with multi-tenancy
- [ ] Basic API structure
- [ ] Document upload and storage

### Milestone 2: Core Agents (Weeks 5-8)
- [ ] DocumentExtractAgent with Claude API
- [ ] DeadlineAgent with FL rules
- [ ] ChecklistAgent with FL requirements
- [ ] Agent orchestration framework
- [ ] Human review queue

### Milestone 3: User Experience (Weeks 9-12)
- [ ] Transaction dashboard
- [ ] Document viewer with extraction overlay
- [ ] Deadline calendar view
- [ ] Checklist management UI
- [ ] Notification system

### Milestone 4: Polish & Launch (Weeks 13-16)
- [ ] CommunicationAgent for drafting
- [ ] Email integration (send/receive)
- [ ] Mobile-responsive design
- [ ] Onboarding flow
- [ ] Beta testing with 5-10 agents
- [ ] Production deployment

---

## Next Steps

1. **Validate assumptions** with 5-10 Florida agents (user interviews)
2. **Finalize tech stack** decisions
3. **Set up development environment** and CI/CD
4. **Begin Milestone 1** implementation
5. **Engage legal counsel** for ToS and compliance review
