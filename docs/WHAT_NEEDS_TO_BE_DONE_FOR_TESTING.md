# What Needs to Be Done for Testing

**Document Date:** December 31, 2024
**Purpose:** Complete step-by-step guide to set up and run the Airport system for testing

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Infrastructure Setup (Docker)](#3-infrastructure-setup-docker)
4. [Database Setup](#4-database-setup)
5. [MinIO (S3) Setup](#5-minio-s3-setup)
6. [Backend API Setup](#6-backend-api-setup)
7. [Frontend Setup](#7-frontend-setup)
8. [Running Tests](#8-running-tests)
9. [End-to-End Testing](#9-end-to-end-testing)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 18+ | Frontend runtime |
| **Docker** | 24+ | Container runtime |
| **Docker Compose** | 2.20+ | Container orchestration |
| **Git** | 2.40+ | Version control |

### Verify Installation

```bash
# Check all prerequisites
python3 --version      # Should be 3.11+
node --version         # Should be 18+
npm --version          # Should be 9+
docker --version       # Should be 24+
docker compose version # Should be 2.20+
```

### Required Accounts/API Keys

| Service | Required For | How to Get |
|---------|--------------|------------|
| **Anthropic API Key** | AI document extraction | https://console.anthropic.com |

---

## 2. Environment Setup

### Step 2.1: Clone Repository

```bash
git clone https://github.com/sheldon904/Airport.git
cd Airport
```

### Step 2.2: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env
```

### Step 2.3: Configure Environment Variables

Edit `.env` and set the following values:

```bash
# === REQUIRED CONFIGURATION ===

# Anthropic API Key (REQUIRED for document extraction)
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# Secret Key (change this for security)
SECRET_KEY=your-secure-random-string-at-least-32-chars

# === OPTIONAL - These defaults work for local development ===

# Database (Docker will create this)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/airport

# Redis (Docker will create this)
REDIS_URL=redis://localhost:6379/0

# MinIO Storage (Docker will create this)
STORAGE_BUCKET=airport-documents
STORAGE_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1

# Development settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### Generate a Secure Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output and set it as `SECRET_KEY` in `.env`.

---

## 3. Infrastructure Setup (Docker)

### Step 3.1: Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, and MinIO
docker compose up -d postgres redis minio
```

### Step 3.2: Verify Services Are Running

```bash
# Check all containers are healthy
docker compose ps

# Expected output:
# NAME                STATUS              PORTS
# airport-postgres-1  Up (healthy)        0.0.0.0:5432->5432/tcp
# airport-redis-1     Up (healthy)        0.0.0.0:6379->6379/tcp
# airport-minio-1     Up (healthy)        0.0.0.0:9000-9001->9000-9001/tcp
```

### Step 3.3: Verify Connectivity

```bash
# Test PostgreSQL
docker compose exec postgres pg_isready -U postgres
# Should output: /var/run/postgresql:5432 - accepting connections

# Test Redis
docker compose exec redis redis-cli ping
# Should output: PONG

# Test MinIO
curl http://localhost:9000/minio/health/live
# Should output: OK or empty (healthy)
```

---

## 4. Database Setup

### Step 4.1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

**Note:** If you get an error about the `license` field in `pyproject.toml`:
```bash
# Edit pyproject.toml and change line 11 from:
license = "Proprietary"
# To:
license = { text = "Proprietary" }
```

### Step 4.2: Run Database Migrations

```bash
# Apply all migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20241220_001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 20241220_001 -> 20241229_002, audit soft delete
INFO  [alembic.runtime.migration] Running upgrade 20241229_002 -> 20241230_003, vision alignment
```

### Step 4.3: Verify Database Schema

```bash
# Connect to database and list tables
docker compose exec postgres psql -U postgres -d airport -c "\dt"

# Expected tables:
#  Schema |       Name        | Type  |  Owner
# --------+-------------------+-------+----------
#  public | alembic_version   | table | postgres
#  public | audit_logs        | table | postgres
#  public | checklists        | table | postgres
#  public | communication_log | table | postgres
#  public | contacts          | table | postgres
#  public | deadlines         | table | postgres
#  public | documents         | table | postgres
#  public | organizations     | table | postgres
#  public | transactions      | table | postgres
#  public | users             | table | postgres
```

---

## 5. MinIO (S3) Setup

### Step 5.1: Access MinIO Console

Open browser: http://localhost:9001

Login credentials:
- **Username:** `minioadmin`
- **Password:** `minioadmin`

### Step 5.2: Create Document Bucket

**Option A: Via MinIO Console (GUI)**
1. Click "Buckets" in left sidebar
2. Click "Create Bucket"
3. Enter bucket name: `airport-documents`
4. Click "Create Bucket"

**Option B: Via Command Line**
```bash
# Install MinIO client (mc)
# macOS: brew install minio/stable/mc
# Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc

# Configure MinIO alias
mc alias set local http://localhost:9000 minioadmin minioadmin

# Create bucket
mc mb local/airport-documents

# Verify bucket exists
mc ls local/
```

---

## 6. Backend API Setup

### Step 6.1: Start the API Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the API server
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 6.2: Verify API is Running

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","environment":"development","version":"0.1.0"}
```

### Step 6.3: Access API Documentation

Open browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 7. Frontend Setup

### Step 7.1: Install Node Dependencies

```bash
cd web
npm install
```

### Step 7.2: Configure Frontend Environment

Create `web/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 7.3: Start Development Server

```bash
npm run dev
```

Expected output:
```
   ▲ Next.js 14.0.4
   - Local:        http://localhost:3000
   - Environments: .env.local

 ✓ Ready in 2.5s
```

### Step 7.4: Verify Frontend

Open browser: http://localhost:3000

You should see the Airport login/registration page.

---

## 8. Running Tests

### Step 8.1: Run Unit Tests

```bash
# From project root (not web directory)
cd /path/to/Airport
source venv/bin/activate

# Run all unit tests
pytest tests/unit/ -v

# Expected output:
# tests/unit/test_bug_fixes.py::test_... PASSED
# tests/unit/test_business_days.py::test_... PASSED
# ... (47+ tests should pass)
```

### Step 8.2: Run Specific Test Files

```bash
# Business day calculator tests
pytest tests/unit/test_business_days.py -v

# Bug fix verification tests
pytest tests/unit/test_bug_fixes.py tests/unit/test_bug_fixes_round2.py tests/unit/test_bug_fixes_round3.py -v

# Service tests
pytest tests/unit/test_privacy_service.py -v
pytest tests/unit/test_priority_service.py -v
pytest tests/unit/test_forms_service.py -v
```

### Step 8.3: Run Tests with Coverage

```bash
pytest tests/unit/ --cov=packages --cov=services --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Step 8.4: Run Integration Tests

**Note:** Integration tests require all infrastructure running.

```bash
# Ensure PostgreSQL, Redis, MinIO are running
docker compose up -d postgres redis minio

# Run integration tests
pytest tests/integration/ -v
```

---

## 9. End-to-End Testing

### Step 9.1: Full System Verification

This checklist verifies the entire system works end-to-end.

#### Prerequisites Check
```bash
# 1. Infrastructure running
docker compose ps  # All services "Up (healthy)"

# 2. API running
curl http://localhost:8000/health  # Returns healthy

# 3. Frontend running
curl http://localhost:3000  # Returns HTML
```

#### Manual E2E Test Flow

**Test 1: User Registration**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "full_name": "Test User",
    "organization_name": "Test Brokerage"
  }'

# Expected: 201 Created with user object
```

**Test 2: User Login**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'

# Expected: 200 OK with access_token and refresh_token
# Save the access_token for subsequent requests
export TOKEN="your-access-token-here"
```

**Test 3: Create Transaction**
```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "property_address": {
      "street": "123 Main Street",
      "city": "Tampa",
      "state": "FL",
      "zip_code": "33601"
    },
    "transaction_type": "purchase",
    "purchase_price": 450000,
    "closing_date": "2025-02-15"
  }'

# Expected: 201 Created with transaction object
# Save the transaction ID
export TX_ID="transaction-id-here"
```

**Test 4: Get Dashboard**
```bash
curl http://localhost:8000/api/v1/transactions/dashboard \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with dashboard data including the transaction
```

**Test 5: Upload Document**
```bash
# Create a test PDF or use any PDF file
curl -X POST "http://localhost:8000/api/v1/documents?transaction_id=$TX_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/test-contract.pdf"

# Expected: 201 Created with document object
# Note: AI extraction requires valid ANTHROPIC_API_KEY
```

**Test 6: View Deadlines**
```bash
curl "http://localhost:8000/api/v1/deadlines?transaction_id=$TX_ID" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with list of deadlines
```

**Test 7: View Checklist**
```bash
curl "http://localhost:8000/api/v1/transactions/$TX_ID/checklist" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with FL-specific checklist items
```

### Step 9.2: Automated E2E Tests (Recommended)

Install Playwright for E2E testing:

```bash
cd web
npm install -D @playwright/test
npx playwright install
```

Create `web/e2e/basic.spec.ts`:
```typescript
import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await expect(page).toHaveTitle(/Airport/);
});

test('registration flow', async ({ page }) => {
  await page.goto('http://localhost:3000/register');
  await page.fill('input[name="email"]', 'e2e@test.com');
  await page.fill('input[name="password"]', 'SecurePassword123!');
  await page.fill('input[name="full_name"]', 'E2E Test');
  await page.fill('input[name="organization_name"]', 'E2E Brokerage');
  await page.click('button[type="submit"]');
  // Verify redirect to dashboard
  await expect(page).toHaveURL(/dashboard/);
});
```

Run E2E tests:
```bash
npx playwright test
```

---

## 10. Troubleshooting

### Common Issues

#### Issue: "Connection refused" to PostgreSQL
```bash
# Check if container is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Restart container
docker compose restart postgres

# Wait for healthy status
docker compose ps --filter "status=running"
```

#### Issue: "alembic upgrade head" fails
```bash
# Check database connection
docker compose exec postgres pg_isready -U postgres

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d postgres redis minio
alembic upgrade head
```

#### Issue: API import errors
```bash
# Verify all routers can be imported
python3 -c "from services.api.main import app; print('OK')"

# Check specific router
python3 -c "from services.api.routers.contacts import router; print('OK')"

# If syntax error, check the specific file
python3 -m py_compile services/api/routers/contacts.py
```

#### Issue: MinIO bucket not found
```bash
# Check if bucket exists
mc ls local/

# Create bucket manually
mc mb local/airport-documents

# Verify
mc ls local/airport-documents
```

#### Issue: Anthropic API errors
```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Test API key validity
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

#### Issue: Frontend can't connect to API
```bash
# Check CORS settings in .env
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Restart API
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload

# Check frontend env
cat web/.env.local
# Should contain: NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Issue: Tests fail with "module not found"
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall in development mode
pip install -e ".[dev]"

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## Quick Start Checklist

For a fresh setup, run these commands in order:

```bash
# 1. Clone and enter directory
git clone https://github.com/sheldon904/Airport.git && cd Airport

# 2. Create and configure environment
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY and SECRET_KEY

# 3. Start infrastructure
docker compose up -d postgres redis minio

# 4. Wait for services to be healthy (30 seconds)
sleep 30 && docker compose ps

# 5. Set up Python environment
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 6. Run database migrations
alembic upgrade head

# 7. Create MinIO bucket
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/airport-documents

# 8. Start API server (in background or new terminal)
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload &

# 9. Verify API is working
curl http://localhost:8000/health

# 10. Set up and start frontend (new terminal)
cd web && npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev &

# 11. Run tests
cd .. && pytest tests/unit/ -v

# 12. Open browser
open http://localhost:3000
```

---

## Service Ports Reference

| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5432 | `postgresql://localhost:5432/airport` |
| Redis | 6379 | `redis://localhost:6379` |
| MinIO API | 9000 | `http://localhost:9000` |
| MinIO Console | 9001 | `http://localhost:9001` |
| Backend API | 8000 | `http://localhost:8000` |
| API Docs | 8000 | `http://localhost:8000/docs` |
| Frontend | 3000 | `http://localhost:3000` |

---

## Test Categories Reference

| Test Directory | Purpose | Requirements |
|----------------|---------|--------------|
| `tests/unit/` | Unit tests (no external deps) | Python + packages |
| `tests/integration/` | Integration tests | Full infrastructure |
| `tests/` (root) | API/router tests | API + database |
| `web/e2e/` | E2E browser tests | Full system running |

---

*This document should be updated whenever infrastructure or dependencies change.*
