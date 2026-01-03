# Airport Platform - Local Development Setup Documentation

**Date:** January 2, 2026
**Status:** Alpha Testing Ready

---

## Overview

This document details the complete local development environment setup for the Airport platform - an AI-powered Florida real estate transaction coordination system.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Airport Platform                          │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 14)          │  Backend (FastAPI)            │
│  - React 18 + TypeScript        │  - Python 3.11 + async        │
│  - TailwindCSS                  │  - SQLAlchemy 2.0             │
│  - React Query                  │  - Pydantic v2                │
│  - Port: 3000                   │  - Port: 8000                 │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure (Docker)                     │
│  - PostgreSQL 15 (port 5432)                                    │
│  - Redis 7 (port 6379)                                          │
│  - MinIO S3 (ports 9000, 9001)                                  │
└─────────────────────────────────────────────────────────────────┘
```

## What Was Configured

### 1. Environment Configuration (`.env`)

Created with the following settings:

```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...  # Claude API for AI agents

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/airport

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage (MinIO)
STORAGE_ENDPOINT=localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET=airport-documents
STORAGE_SECURE=false

# Security
SECRET_KEY=<generated-secret>
JWT_SECRET_KEY=<generated-secret>

# Rate Limiting (relaxed for testing)
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60
```

### 2. Code Fixes Applied

#### a. `pyproject.toml` - Build Configuration
- Changed license format from string to table: `license = {text = "Proprietary"}`
- Added hatch build targets for wheel packaging

#### b. `alembic/versions/20241230_003_vision_alignment.py` - Migration Chain
- Fixed `down_revision` from `'20241229_002'` to `'002_audit_soft_delete'`

#### c. `packages/core/services/audit.py` - Timezone Fix (Line 132)
- Changed `datetime.now(timezone.utc)` to `datetime.utcnow()`
- PostgreSQL TIMESTAMP WITHOUT TIME ZONE doesn't accept timezone-aware datetimes

#### d. `packages/db/repositories/user.py` - Timezone Fix (Line 41)
- Changed `datetime.now(timezone.utc)` to `datetime.utcnow()`

#### e. `packages/db/session.py` - Critical Commit Bug Fix
- **Problem:** Session changes weren't being committed because `flush()` clears `session.new`, making the conditional commit check always fail
- **Solution:** Always commit (for read-only operations, commit is essentially a no-op)

```python
# Before (broken):
if session.new or session.dirty or session.deleted:
    await session.commit()

# After (fixed):
await session.commit()  # Always commit
```

#### f. `web/lib/api.ts` - API Endpoint Trailing Slash Fix
- **Problem:** FastAPI redirects `/transactions` to `/transactions/` (307), losing auth header
- **Solution:** Added trailing slashes to transaction endpoints

```typescript
// Fixed endpoints:
'/api/v1/transactions/'   // was '/api/v1/transactions'
```

### 3. Dependencies Installed

#### Python (in venv):
- `email-validator` - Email validation for Pydantic
- `python-magic-bin` - File type detection (Windows)
- `bcrypt==4.2.1` - Downgraded from 5.0 for passlib compatibility
- `reportlab` - PDF generation
- `minio` - S3-compatible storage client

#### Node.js (in web/):
- All dependencies via `npm install`

### 4. Database Migrations

Successfully ran all migrations:
```
001_initial_schema
002_audit_soft_delete
20241230_003_vision_alignment
```

### 5. MinIO Storage

- Created bucket: `airport-documents`
- Console available at: http://localhost:9001
- Credentials: minioadmin/minioadmin

---

## Test Data Seeded

### Scripts Created

1. **`scripts/seed_data.py`** - Database seeding script
2. **`scripts/generate_sample_docs.py`** - Realistic PDF document generator
3. **`scripts/upload_sample_docs.py`** - Document upload to transactions

### Data Created

| Entity | Count | Details |
|--------|-------|---------|
| Organizations | 3 | FL brokerages (Sunshine State Realty, Palm Coast, Atlantic Coast) |
| Users | 8 | Agents, admins, brokers (password: `TestPassword123`) |
| Contacts | 36 | Buyers, sellers, lenders, title companies, inspectors |
| Transactions | 11 | Active FL real estate deals |
| Deadlines | 75 | Florida statutory deadlines (F.S. 689.25, F.S. 718.503, TRID) |
| Communications | 45 | Emails, calls, notes |
| Checklists | 9 | Standard and compliance checklists |
| Documents | 18 | Uploaded to 3 transactions |

### Sample Transactions

| Property | County | Price | Status |
|----------|--------|-------|--------|
| 1842 Brickell Ave, Miami | Miami-Dade | $875,000 | Under Contract |
| 3456 Coconut Grove Dr, Miami | Miami-Dade | $1,250,000 | Under Contract |
| 789 Ocean Drive, Miami Beach | Miami-Dade | $2,100,000 | Pending |
| 401 E Jackson St, Tampa | Hillsborough | $485,000 | Under Contract |
| + 7 more transactions | Various | Various | Various |

### Realistic PDF Documents Generated (30 total)

Located in: `sample_documents/`

| Document Type | Description | Legal Basis |
|---------------|-------------|-------------|
| FAR/BAR AS-IS Contract | Full purchase agreement | Florida Realtors/Florida Bar standard |
| Closing Disclosure | TRID-compliant 5-page form | CFPB TILA-RESPA |
| Lead Paint Disclosure | Pre-1978 homes | 42 U.S.C. 4852d |
| Seller's Disclosure | Property condition | F.S. 689.25 |
| HOA/Condo Disclosure | Association requirements | F.S. 718.503, F.S. 720.401 |
| Home Inspection Report | Professional inspection | FL Admin Code 61-30 |
| Title Commitment | Title insurance commitment | Standard FL format |

### Test User Accounts

| Email | Password | Role | Organization |
|-------|----------|------|--------------|
| admin@sunshinestaterealty.com | TestPassword123 | admin | Sunshine State Realty |
| maria.rodriguez@sunshinestaterealty.com | TestPassword123 | agent | Sunshine State Realty |
| james.chen@palmcoastrealestate.com | TestPassword123 | agent | Palm Coast Real Estate |
| newadmin@test.com | TestPassword123 | admin | Sunshine State Realty* |

*Moved from "New Test Brokerage" to access seeded data

---

## How to Start the System

### Prerequisites
- Docker Desktop running
- Python 3.11+
- Node.js 18+

### 1. Start Infrastructure (Docker)
```bash
docker-compose up -d postgres redis minio
```

### 2. Start Backend
```bash
cd C:\Users\sheld\Documents\GitHub\Airport
.\venv\Scripts\activate
uvicorn services.api.main:app --reload --port 8000
```

### 3. Start Frontend
```bash
cd C:\Users\sheld\Documents\GitHub\Airport\web
npm run dev
```

### 4. Access the Application
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **MinIO Console:** http://localhost:9001

---

## AI Agents Overview

The system includes 6 AI agents powered by Claude:

| Agent | Purpose | Trigger |
|-------|---------|---------|
| DocumentExtractAgent | Extract data from uploaded documents | Document upload |
| DeadlineAgent | Analyze and create Florida statutory deadlines | Contract dates |
| ChecklistAgent | Generate transaction checklists | Transaction creation |
| CommunicationAgent | Draft professional communications | User request |
| NotificationAgent | Send deadline reminders | Scheduled/deadline approach |
| OrchestratorAgent | Coordinate multi-agent workflows | Complex tasks |

---

## Known Issues / Limitations

1. **AI Extraction Not Auto-Triggered:** Documents are uploaded with status "uploaded" but require manual trigger or worker service to process
2. **bcrypt Version:** Must use 4.2.1 (not 5.x) for passlib compatibility
3. **Timezone:** PostgreSQL TIMESTAMP WITHOUT TIME ZONE requires naive UTC datetimes

---

## File Locations

```
C:\Users\sheld\Documents\GitHub\Airport\
├── .env                          # Environment configuration
├── venv/                         # Python virtual environment
├── sample_documents/             # Generated PDF documents (30 files)
├── scripts/
│   ├── seed_data.py             # Database seeding
│   ├── generate_sample_docs.py  # PDF generation
│   └── upload_sample_docs.py    # Document upload
├── packages/                     # Core business logic
├── services/
│   └── api/                     # FastAPI backend
└── web/                         # Next.js frontend
```

---

## Next Steps for Testing

1. **Login:** http://localhost:3000 with `newadmin@test.com` / `TestPassword123`
2. **View Transactions:** Navigate to Transactions tab
3. **View Documents:** Click on a transaction → Documents tab
4. **Test AI Extraction:** Manually trigger via API or start worker service
5. **Test Deadlines:** Check the Deadlines tab for statutory deadlines

---

## Shutdown Commands

```bash
# Stop Docker containers
docker-compose down

# Or stop all Airport-related processes
# Frontend: Ctrl+C in terminal
# Backend: Ctrl+C in terminal
```

---

*Document generated as part of Airport Platform local setup - January 2026*
