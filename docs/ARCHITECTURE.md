# Airport System Architecture

## Overview

Airport is built as a modern, scalable SaaS platform using a layered architecture with AI agents for intelligent document processing and compliance automation.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Next.js 14 Frontend                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │Dashboard │  │Transact- │  │Documents │  │Settings  │            │   │
│  │  │   Page   │  │  ions    │  │ Viewer   │  │  Pages   │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                         │                                            │   │
│  │                   React Query + API Client                           │   │
│  └─────────────────────────┼───────────────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │ HTTPS/REST
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                         API LAYER                                            │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  ┌─────────────────────────┴───────────────────────────────────────────┐   │
│  │                      FastAPI Gateway                                 │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │  Auth   │ │Transact-│ │Documents│ │Deadlines│ │  Audit  │       │   │
│  │  │ Router  │ │  ions   │ │ Router  │ │ Router  │ │ Router  │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  │                                                                      │   │
│  │  Rate Limiting │ CORS │ JWT Auth │ Request Validation               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                       SERVICE LAYER                                          │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  ┌──────────────────────────┴──────────────────────────────────────────┐   │
│  │                     Business Services                                │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ Auth    │ │Transact-│ │Document │ │Deadline │ │  Audit  │       │   │
│  │  │ Service │ │  ion    │ │ Service │ │ Service │ │ Service │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│  ┌──────────────────────────┴──────────────────────────────────────────┐   │
│  │                        AI Agent System                               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │  Document   │ │  Deadline   │ │  Checklist  │ │Communication│   │   │
│  │  │  Extract    │ │   Agent     │ │   Agent     │ │   Agent     │   │   │
│  │  │   Agent     │ │             │ │             │ │             │   │   │
│  │  └──────┬──────┘ └──────┬──────┘ └─────────────┘ └─────────────┘   │   │
│  │         │               │                                           │   │
│  │         │         ┌─────┴─────┐                                    │   │
│  │         └─────────┤Orchestrat-│                                    │   │
│  │                   │    or     │                                    │   │
│  │                   └───────────┘                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                         DATA LAYER                                           │
├─────────────────────────────┼───────────────────────────────────────────────┤
│  ┌──────────────┐  ┌───────┴──────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │    Redis     │  │  S3 Storage  │  │  Claude API  │   │
│  │   Database   │  │    Queue     │  │  (Documents) │  │  (Anthropic) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Details

### Client Layer (Next.js 14)

The frontend is built with Next.js 14 using the App Router pattern.

**Key Components:**
- `app/` - Page components using file-based routing
- `components/` - Reusable React components
- `hooks/` - React Query hooks for data fetching
- `lib/` - API client and utilities

**State Management:**
- React Query for server state
- React Context for auth state
- Local state for UI interactions

### API Layer (FastAPI)

RESTful API built with FastAPI providing:

**Routers:**
| Router | Path | Purpose |
|--------|------|---------|
| auth | `/api/v1/auth` | Authentication & registration |
| transactions | `/api/v1/transactions` | Transaction CRUD |
| documents | `/api/v1/documents` | Document management |
| deadlines | `/api/v1/deadlines` | Deadline tracking |
| reports | `/api/v1/reports` | Compliance reports |
| audit | `/api/v1/audit` | Audit log access |

**Middleware:**
- Rate limiting (token bucket)
- CORS handling
- JWT authentication
- Request validation (Pydantic)

### Service Layer

**Business Services:**
- `AuthService` - JWT token management, password hashing
- `TransactionService` - Transaction lifecycle management
- `DocumentService` - Upload, processing, extraction
- `DeadlineService` - Deadline CRUD and notifications
- `AuditService` - Compliance logging

**AI Agent System:**
- `DocumentExtractAgent` - PDF/image → structured data using Claude
- `DeadlineAgent` - FL statutory deadline calculations
- `ChecklistAgent` - Document requirement tracking
- `CommunicationAgent` - Email draft generation
- `NotificationAgent` - Reminder delivery
- `Orchestrator` - Agent coordination and sequencing

### Data Layer

**PostgreSQL Database:**
- Multi-tenant with row-level isolation
- JSONB for flexible document storage
- Soft delete for compliance retention

**Key Tables:**
| Table | Purpose |
|-------|---------|
| organizations | Brokerage/team accounts |
| users | User accounts with roles |
| transactions | Real estate transactions |
| documents | Uploaded document metadata |
| deadlines | Calculated deadlines |
| audit_logs | Compliance audit trail |

**Redis:**
- Background job queue
- Session caching
- Rate limit tracking

**S3 Storage:**
- Document file storage
- Tenant-prefixed paths
- Presigned URLs for access

## Data Flow Examples

### Document Upload Flow

```
1. User uploads document via frontend
2. API receives multipart upload
3. File stored in S3 with tenant prefix
4. Document record created in PostgreSQL
5. Job queued in Redis for processing
6. Worker picks up job
7. DocumentExtractAgent processes:
   - Downloads from S3
   - Extracts text (PDF) or uses Vision API (images)
   - Calls Claude API for structured extraction
   - Saves extracted data to document record
8. DeadlineAgent triggered:
   - Reads extracted dates
   - Calculates FL statutory deadlines
   - Creates deadline records
9. User notified of completion
```

### Deadline Check Flow (Scheduled)

```
1. Scheduler runs every 15 minutes
2. Queries deadlines due within reminder window
3. For each deadline needing reminder:
   - NotificationAgent generates message
   - Email queued for delivery
   - Audit log entry created
4. Overdue deadlines flagged for review
```

## Security Architecture

### Authentication
- JWT access tokens (1 hour expiry)
- Refresh tokens (7 day expiry)
- Password hashing with bcrypt

### Authorization
- Role-based access control (agent, admin, broker)
- Organization-scoped data access
- Resource-level permissions

### Data Protection
- TLS 1.3 for all connections
- Encryption at rest (database, S3)
- Presigned URLs for document access (15 min expiry)

### Audit Trail
- All actions logged with user context
- Immutable audit records (SET NULL on transaction delete)
- Export capability for compliance

## Scalability Design

### Horizontal Scaling
- Stateless API servers behind load balancer
- Database connection pooling
- Redis cluster for queue distribution

### Performance Optimizations
- Query caching with Redis
- Pagination for list endpoints
- Async processing for document extraction

### Multi-Tenancy
- Organization ID on all tenant data
- Database indexes for efficient filtering
- S3 path prefixing for isolation

## Deployment Architecture

### Development
```
docker-compose up
├── postgres:14
├── redis:7
├── api (uvicorn --reload)
└── web (npm run dev)
```

### Production
```
Docker Swarm / Kubernetes
├── PostgreSQL (managed: RDS/Cloud SQL)
├── Redis (managed: ElastiCache/Memorystore)
├── API containers (auto-scaling)
├── Worker containers (auto-scaling)
├── Scheduler container (single instance)
└── Web (Vercel / static hosting)
```

## Monitoring & Observability

### Logging
- Structured logging with structlog
- Request/response tracing
- Agent execution logging

### Metrics (Planned)
- API latency and error rates
- Document processing times
- Deadline compliance rates

### Alerting (Planned)
- Failed document extractions
- Overdue deadlines
- System errors
