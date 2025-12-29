# Airport - AI Transaction Coordinator

An AI-powered transaction coordination platform for Florida real estate professionals. Airport automates 65-75% of routine administrative work, saving agents 10+ hours per transaction while maintaining full compliance with Florida regulations.

## What It Does

- **Document Intelligence**: Upload contracts and disclosures - AI extracts dates, parties, contingencies, and deadlines automatically
- **Compliance Automation**: Tracks 15+ Florida statutory deadlines (F.S. 689.25, F.S. 718.503, TRID requirements)
- **Smart Reminders**: Never miss a deadline with business-day-aware calculations and federal holiday handling
- **Party Management**: Track all transaction parties (buyers, sellers, agents, lenders, title companies)
- **Communication Drafting**: AI-generated status updates ready for your review
- **Audit Trail**: Complete compliance record for every action

## Current Status: MVP Complete

| Feature | Status |
|---------|--------|
| Document Upload & Extraction | ✅ Complete |
| PDF & Image Processing (Claude Vision) | ✅ Complete |
| Florida Statutory Deadlines | ✅ Complete (15+ statutes) |
| TRID Business Day Calculator | ✅ Complete |
| Transaction Dashboard | ✅ Complete |
| Party Management | ✅ Complete |
| Document Viewer | ✅ Complete |
| Settings & Profile | ✅ Complete |
| Audit Logging | ✅ Complete |
| Unit Test Suite | ✅ 47 tests passing |

## Project Structure

```
airport/
├── services/
│   ├── api/                    # FastAPI REST API
│   │   ├── routers/            # Endpoint handlers
│   │   │   ├── auth.py         # Authentication
│   │   │   ├── transactions.py # Transaction CRUD
│   │   │   ├── documents.py    # Document management
│   │   │   ├── deadlines.py    # Deadline tracking
│   │   │   ├── reports.py      # Compliance reports
│   │   │   └── audit.py        # Audit log access
│   │   └── dependencies.py     # DI and auth
│   ├── agents/                 # AI Agent System
│   │   ├── base.py             # Base agent class
│   │   ├── document_extract/   # PDF/Image → structured data
│   │   ├── deadline/           # FL statute calculations
│   │   ├── checklist/          # Document requirements
│   │   ├── communication/      # Email drafting
│   │   ├── notification/       # Reminder system
│   │   └── orchestrator/       # Agent coordination
│   ├── scheduler/              # Cron-based deadline checks
│   └── worker/                 # Background job processor
├── packages/
│   ├── core/                   # Shared business logic
│   │   ├── services/           # Business services
│   │   │   ├── auth.py         # JWT authentication
│   │   │   ├── transaction.py  # Transaction logic
│   │   │   ├── document.py     # Document processing
│   │   │   ├── deadline.py     # Deadline management
│   │   │   └── audit.py        # Audit logging
│   │   └── templates/          # Email templates
│   ├── db/                     # Database layer
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── repositories/       # Data access layer
│   │   └── session.py          # Connection management
│   └── compliance/             # Regulatory compliance
│       ├── florida.py          # FL-specific rules
│       └── business_days.py    # TRID calculations
├── web/                        # Next.js 14 Frontend
│   ├── app/                    # App Router pages
│   │   ├── dashboard/          # Main dashboard
│   │   ├── transactions/       # Transaction management
│   │   ├── documents/          # Document viewer
│   │   ├── deadlines/          # Deadline calendar
│   │   ├── settings/           # User settings
│   │   └── auth/               # Login/Register
│   ├── components/             # React components
│   ├── hooks/                  # React Query hooks
│   └── lib/                    # Utilities & API client
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── alembic/                    # Database migrations
├── infrastructure/             # Deployment configs
└── docs/                       # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (for background jobs)

### Development Setup

```bash
# Clone and install Python dependencies
git clone <repository>
cd airport
pip install -e ".[dev]"

# Start infrastructure
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Start API server (terminal 1)
uvicorn services.api.main:app --reload --port 8000

# Start frontend (terminal 2)
cd web
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/airport
ANTHROPIC_API_KEY=your-claude-api-key
JWT_SECRET_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=packages --cov=services

# Run specific test file
pytest tests/unit/test_business_days.py -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User authentication |
| `/api/v1/transactions` | GET/POST | Transaction management |
| `/api/v1/transactions/{id}` | GET/PATCH/DELETE | Single transaction |
| `/api/v1/documents/upload/{tx_id}` | POST | Upload document |
| `/api/v1/documents/{id}/extracted` | GET | Get extracted data |
| `/api/v1/deadlines/upcoming` | GET | Upcoming deadlines |
| `/api/v1/audit` | GET | Audit log (admin) |
| `/api/v1/audit/export` | GET | Export audit CSV/JSON |

## Florida Compliance

Airport tracks these Florida statutory requirements:

- **F.S. 689.25** - Seller's Property Disclosure
- **F.S. 404.056** - Radon Gas Disclosure
- **F.S. 689.261** - Property Tax Disclosure
- **F.S. 553.996** - Energy Efficiency Disclosure
- **F.S. 718.503** - Condo Association Documents & Rescission
- **F.S. 720.401** - HOA Disclosure Documents
- **42 U.S.C. 4852d** - Lead-Based Paint (pre-1978)
- **12 CFR 1026.19** - TRID Loan Estimate & Closing Disclosure

## Documentation

- [MVP Plan](docs/MVP_PLAN.md) - Product roadmap
- [Architecture](docs/ARCHITECTURE.md) - Technical design
- [API Reference](docs/API.md) - Endpoint documentation
- [Compliance Guide](docs/COMPLIANCE.md) - Florida regulations

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI (Python 3.11) |
| Database | PostgreSQL + SQLAlchemy |
| AI/LLM | Claude API (Anthropic) |
| Frontend | Next.js 14 + React Query |
| Auth | JWT + bcrypt |
| Storage | S3-compatible |
| Queue | Redis |

## License

Proprietary - All rights reserved
