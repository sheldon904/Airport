# Airport API Reference

REST API documentation for the Airport Transaction Coordinator platform.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.airport.com/api/v1
```

## Authentication

All endpoints (except `/auth/login` and `/auth/register`) require a valid JWT access token.

Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### Token Lifecycle

| Token Type | Expiry | Purpose |
|------------|--------|---------|
| Access Token | 1 hour | API authentication |
| Refresh Token | 7 days | Obtain new access tokens |

---

## Authentication Endpoints

### Register Organization
`POST /auth/register`

Register a new organization with an admin user.

**Request Body:**
```json
{
  "organization_name": "ABC Realty",
  "admin_email": "admin@abcrealty.com",
  "admin_password": "SecurePass123!",
  "admin_name": "John Smith",
  "license_number": "SL12345",
  "state": "FL"
}
```

**Response:** `201 Created`
```json
{
  "organization": {
    "id": "uuid",
    "name": "ABC Realty",
    "state": "FL",
    "subscription_tier": "free"
  },
  "user": {
    "id": "uuid",
    "email": "admin@abcrealty.com",
    "full_name": "John Smith",
    "role": "admin",
    "organization_id": "uuid"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### Login
`POST /auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Refresh Token
`POST /auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:** `200 OK` - New token pair

### Get Current User
`GET /auth/me`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Smith",
  "role": "agent",
  "organization_id": "uuid"
}
```

### Change Password
`POST /auth/change-password`

**Request Body:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newSecurePass123!"
}
```

**Response:** `204 No Content`

### Create User (Admin Only)
`POST /auth/users`

**Request Body:**
```json
{
  "email": "agent@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Doe",
  "role": "agent",
  "phone": "555-123-4567",
  "license_number": "SL67890"
}
```

**Response:** `201 Created`

### Password Reset Flow

1. **Request Reset:** `POST /auth/forgot-password`
   ```json
   { "email": "user@example.com" }
   ```
   Response: `202 Accepted` (always succeeds to prevent enumeration)

2. **Validate Token:** `POST /auth/validate-reset-token`
   ```json
   { "token": "reset-token-from-email" }
   ```

3. **Reset Password:** `POST /auth/reset-password`
   ```json
   { "token": "reset-token", "new_password": "NewSecurePass123!" }
   ```

---

## Transaction Endpoints

### List Transactions
`GET /transactions`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |
| status | string | null | Filter by status |

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "status": "active",
      "transaction_type": "purchase",
      "property_address": {
        "street": "123 Main St",
        "city": "Miami",
        "state": "FL",
        "zip_code": "33101"
      },
      "purchase_price": 450000.00,
      "year_built": 2015,
      "effective_date": "2024-06-01",
      "closing_date": "2024-07-15",
      "parties": [...],
      "buyer_name": "Jane Buyer",
      "seller_name": "John Seller",
      "notes": null,
      "created_at": "2024-06-01T10:30:00Z",
      "updated_at": "2024-06-01T10:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20
}
```

### Get Dashboard Summary
`GET /transactions/dashboard`

**Response:** `200 OK`
```json
{
  "active_transactions": 12,
  "pending_review": 3,
  "closing_soon": 5,
  "closed_this_month": 8,
  "upcoming_closings": [...]
}
```

### Create Transaction
`POST /transactions`

**Request Body:**
```json
{
  "transaction_type": "purchase",
  "property_address": {
    "street": "123 Main St",
    "unit": null,
    "city": "Miami",
    "state": "FL",
    "zip_code": "33101",
    "county": "Miami-Dade"
  },
  "purchase_price": 450000.00,
  "year_built": 2015,
  "closing_date": "2024-07-15",
  "buyer_name": "Jane Buyer",
  "seller_name": "John Seller",
  "notes": "First-time buyer, financed"
}
```

**Transaction Types:** `purchase`, `sale`, `dual`, `lease`

**Response:** `201 Created`

### Get Transaction Details
`GET /transactions/{transaction_id}`

Returns full transaction details including documents, deadlines, and checklist.

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "status": "active",
  "transaction_type": "purchase",
  "property_address": {...},
  "purchase_price": 450000.00,
  "parties": [...],
  "documents_count": 8,
  "deadlines_count": 12,
  "checklist_completion": 65.5,
  "checklist_items": [
    {
      "id": "fl_contract_executed",
      "name": "Executed Purchase Contract",
      "description": "Fully signed contract",
      "category": "contract",
      "required": true,
      "status": "completed",
      "document_id": "uuid"
    }
  ],
  "upcoming_deadlines": [
    {
      "id": "uuid",
      "name": "Inspection Period Ends",
      "due_date": "2024-06-15",
      "status": "pending",
      "days_remaining": 5
    }
  ]
}
```

### Update Transaction
`PATCH /transactions/{transaction_id}`

**Request Body:**
```json
{
  "status": "pending_close",
  "purchase_price": 455000.00,
  "effective_date": "2024-06-03",
  "closing_date": "2024-07-20",
  "notes": "Price adjusted after inspection"
}
```

**Response:** `200 OK`

### Add Party
`POST /transactions/{transaction_id}/parties`

**Request Body:**
```json
{
  "party": {
    "role": "buyer_agent",
    "name": "Sarah Agent",
    "email": "sarah@realty.com",
    "phone": "555-987-6543",
    "company": "ABC Realty",
    "license_number": "SL99999"
  }
}
```

**Party Roles:** `buyer`, `seller`, `buyer_agent`, `seller_agent`, `lender`, `title_company`

### Remove Party
`DELETE /transactions/{transaction_id}/parties/{party_id}`

**Response:** `200 OK`

### Delete Transaction
`DELETE /transactions/{transaction_id}`

Only allowed for draft transactions.

**Response:** `204 No Content`

---

## Document Endpoints

### Upload Document
`POST /documents/upload/{transaction_id}`

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | File | Yes | PDF, JPEG, PNG, or TIFF |
| document_type | string | No | Type hint (auto-detected) |

**Allowed Content Types:**
- `application/pdf`
- `image/jpeg`
- `image/png`
- `image/tiff`

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "transaction_id": "uuid",
  "document_type": "contract",
  "filename": "purchase_contract.pdf",
  "content_type": "application/pdf",
  "file_size": 245678,
  "status": "uploaded",
  "extraction_status": "uploaded",
  "extraction_confidence": null,
  "needs_review": false,
  "uploaded_at": "2024-06-01T10:30:00Z",
  "flags": []
}
```

### Get Upload URL (Direct Upload)
`POST /documents/upload-url/{transaction_id}`

For large files, get a presigned URL for direct upload.

**Query Parameters:**
- `filename`: string (required)
- `content_type`: string (default: application/pdf)

**Response:** `200 OK`
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "storage_path": "orgs/{org_id}/...",
  "expires_in": 3600
}
```

### List Transaction Documents
`GET /documents/transaction/{transaction_id}`

**Query Parameters:**
- `document_type`: Filter by type
- `status`: Filter by status

**Response:** `200 OK` - Array of DocumentResponse

### Get Review Queue
`GET /documents/review-queue`

Get documents needing human review.

**Response:** `200 OK` - Array of DocumentResponse

### Get Document
`GET /documents/{document_id}`

**Response:** `200 OK`

### Download Document
`GET /documents/{document_id}/download`

**Response:** `200 OK`
```json
{
  "url": "https://s3.amazonaws.com/presigned...",
  "expires_in": 3600
}
```

### Get Extracted Data
`GET /documents/{document_id}/extracted`

**Response:** `200 OK`
```json
{
  "document_id": "uuid",
  "document_type": "contract",
  "extracted_data": {
    "effective_date": "2024-06-01",
    "closing_date": "2024-07-15",
    "purchase_price": 450000,
    "parties": [...],
    "property_address": {...},
    "contingencies": [...]
  },
  "confidence": 0.95,
  "needs_review_items": ["closing_date"]
}
```

### Verify Extracted Data
`POST /documents/{document_id}/verify`

Human-in-the-loop confirmation/correction.

**Request Body:**
```json
{
  "corrections": {
    "closing_date": "2024-07-20"
  }
}
```

**Response:** `200 OK`

### Reprocess Document
`POST /documents/{document_id}/reprocess`

Re-run AI extraction.

**Response:** `200 OK`

### Delete Document
`DELETE /documents/{document_id}`

**Response:** `204 No Content`

---

## Deadline Endpoints

### List Transaction Deadlines
`GET /deadlines/transaction/{transaction_id}`

**Query Parameters:**
- `include_completed`: boolean (default: false)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "transaction_id": "uuid",
    "deadline_type": "inspection_period",
    "name": "Inspection Period Ends",
    "title": "Inspection Period Ends",
    "description": "Last day for buyer inspection",
    "due_date": "2024-06-15",
    "status": "pending",
    "days_remaining": 5,
    "notes": null,
    "completed_at": null,
    "source_document_id": "uuid",
    "is_statutory": true,
    "statutory_reference": "F.S. 475.278"
  }
]
```

### List Upcoming Deadlines
`GET /deadlines/upcoming`

Cross-transaction view for dashboard.

**Query Parameters:**
- `days_ahead`: int (default: 7, max: 90)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "Inspection Period Ends",
    "title": "Inspection Period Ends",
    "due_date": "2024-06-15",
    "days_remaining": 5,
    "status": "pending",
    "deadline_type": "inspection_period",
    "transaction_id": "uuid",
    "property_address": "123 Main St, Miami",
    "is_statutory": true
  }
]
```

### List Overdue Deadlines
`GET /deadlines/overdue`

**Response:** `200 OK` - Array of DeadlineResponse

### Get Deadline
`GET /deadlines/{deadline_id}`

**Response:** `200 OK`

### Create Custom Deadline
`POST /deadlines`

**Request Body:**
```json
{
  "transaction_id": "uuid",
  "name": "Custom Inspection",
  "due_date": "2024-06-20",
  "deadline_type": "custom",
  "description": "Specialized roof inspection"
}
```

**Response:** `201 Created`

### Update Deadline
`PATCH /deadlines/{deadline_id}`

**Request Body:**
```json
{
  "due_date": "2024-06-22",
  "name": "Updated Name",
  "notes": "Extended by agreement"
}
```

### Complete Deadline
`POST /deadlines/{deadline_id}/complete`

**Request Body:**
```json
{
  "notes": "Inspection completed, no issues"
}
```

### Waive Deadline
`POST /deadlines/{deadline_id}/waive`

**Request Body:**
```json
{
  "reason": "Buyer waived inspection contingency"
}
```

### Extend Deadline
`POST /deadlines/{deadline_id}/extend`

**Request Body:**
```json
{
  "new_date": "2024-06-25",
  "reason": "Agreed extension with seller"
}
```

### Delete Custom Deadline
`DELETE /deadlines/{deadline_id}`

Only custom deadlines can be deleted.

**Response:** `204 No Content`

---

## Report Endpoints

### Generate Transaction Report
`POST /reports/transactions/{transaction_id}`

**Query Parameters:**
- `format`: `json` or `html` (default: json)

**Response:** `200 OK` - TransactionSummaryReport

### Download Transaction Report
`GET /reports/transactions/{transaction_id}/download`

**Response:** HTML file attachment

### Generate Organization Report
`GET /reports/organization`

Admin/broker only.

**Response:** `200 OK`
```json
{
  "report_id": "uuid",
  "generated_at": "2024-06-01T10:30:00Z",
  "organization_id": "uuid",
  "organization_name": "ABC Realty",
  "period_start": "2024-05-01",
  "period_end": "2024-06-01",
  "transactions": {
    "total": 25,
    "active": 12,
    "completed": 8,
    "cancelled": 2
  },
  "compliance_rate": 94.5,
  "overdue_deadlines": [...],
  "documents_needing_review": [...]
}
```

### Dashboard Metrics
`GET /reports/dashboard`

**Response:** `200 OK`
```json
{
  "active_transactions": 12,
  "pending_deadlines": 8,
  "documents_needing_review": 3,
  "completed_this_month": 5,
  "overdue_deadlines": 1,
  "upcoming_closings": [...]
}
```

---

## Audit Endpoints

### List Audit Logs (Admin Only)
`GET /audit`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| page | int | Page number |
| page_size | int | Items per page (max 100) |
| transaction_id | uuid | Filter by transaction |
| action | string | Filter by action type |
| agent_type | string | Filter by AI agent |
| resource_type | string | Filter by resource |
| start_date | date | Start date filter |
| end_date | date | End date filter |
| search | string | Search in action/details |

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "transaction_id": "uuid",
      "user_id": "uuid",
      "action": "document.uploaded",
      "agent_type": "document_extract",
      "resource_type": "document",
      "resource_id": "uuid",
      "details": {"filename": "contract.pdf"},
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2024-06-01T10:30:00Z",
      "property_address": "123 Main St, Miami"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

### Audit Summary (Admin Only)
`GET /audit/summary`

**Response:** `200 OK`
```json
{
  "total_logs": 1500,
  "actions_by_type": {
    "document.uploaded": 250,
    "deadline.created": 180,
    "transaction.updated": 120
  },
  "logs_by_agent": {
    "document_extract": 200,
    "deadline": 150
  },
  "logs_today": 45,
  "logs_this_week": 312
}
```

### Transaction Audit Trail
`GET /audit/transaction/{transaction_id}`

Complete audit trail for compliance review.

**Response:** `200 OK` - Array of AuditLogResponse

### Export Audit Logs (Admin Only)
`GET /audit/export`

**Query Parameters:**
- `format`: `csv` or `json` (default: csv)
- `transaction_id`: Filter by transaction
- `start_date`: Start date filter
- `end_date`: End date filter

**Response:** File download (CSV or JSON)

### Get Action Types
`GET /audit/actions`

**Response:** `200 OK` - Array of action strings

### Get Agent Types
`GET /audit/agents`

**Response:** `200 OK` - Array of agent type strings

---

## Health Check

### Health
`GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-06-01T10:30:00Z"
}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing the issue"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (success, no body) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 422 | Unprocessable Entity (invalid input) |
| 500 | Internal Server Error |

### Authentication Errors

```json
{
  "detail": "Could not validate credentials",
  "headers": {"WWW-Authenticate": "Bearer"}
}
```

---

## Rate Limiting

API requests are rate-limited per organization:

| Tier | Requests/Minute |
|------|-----------------|
| Free | 60 |
| Professional | 300 |
| Enterprise | 1000 |

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1622547200
```
