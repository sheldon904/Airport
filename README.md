# Airport - AI Transaction Coordinator

An AI-powered transaction coordination platform for real estate professionals.

## Overview

Airport automates the administrative burden of real estate transaction coordination, handling document processing, deadline tracking, and communication drafting while maintaining human oversight for compliance decisions.

## Project Structure

```
airport/
├── services/
│   ├── api/              # FastAPI gateway service
│   ├── agents/           # AI agent containers
│   │   ├── document_extract/
│   │   ├── deadline/
│   │   ├── checklist/
│   │   ├── communication/
│   │   └── orchestrator/
│   └── worker/           # Background job processor
├── packages/
│   ├── core/             # Shared business logic
│   ├── db/               # Database models and migrations
│   └── compliance/       # State-specific compliance rules
├── web/                  # Next.js frontend
├── infrastructure/       # Terraform/K8s configs
└── docs/                 # Documentation
```

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Start local development
docker-compose up -d

# Run migrations
alembic upgrade head

# Start API server
uvicorn services.api.main:app --reload
```

## Documentation

- [MVP Plan](docs/MVP_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Compliance Guide](docs/COMPLIANCE.md)

## License

Proprietary - All rights reserved
