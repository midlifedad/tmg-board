# TMG Board Management Interface - Backend Spec

**Status**: READY FOR APPROVAL - Spec aligned with frontend
**Author**: Drew (Backend)
**Collaborator**: Beth (Frontend)
**Updated**: 2026-01-23

## Overview

Backend API for TMG Board Management Interface at tmgboard.themany.com. Provides authentication, document management, meeting coordination, and decision tracking for The Many Group board members.

## Tech Stack (Aligned with themany-forecasting)

- **Runtime**: Python 3.10+
- **Framework**: FastAPI 0.115+
- **Server**: Uvicorn
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0+ with Alembic migrations
- **Validation**: Pydantic 2.5+
- **Auth**: Google OAuth2 + Header-based (X-User-Email)
- **File Storage**: S3 or Google Cloud Storage
- **External APIs**: DocuSign eSignature (JWT Grant)

**Why FastAPI?** Consistency with themany-forecasting codebase, proven patterns we can reuse, and team familiarity.

---

## 1. Authentication & Authorization

### Google OAuth Flow

Following themany-forecasting pattern with NextAuth on frontend:

```
Frontend (NextAuth)           Backend (FastAPI)
       │                            │
       │  1. Google Sign-in         │
       ├───────────────────────────>│
       │                            │
       │  2. Verify with Google     │
       │     + Check whitelist      │
       │<───────────────────────────┤
       │                            │
       │  3. Get user from DB       │
       ├───────────────────────────>│
       │                            │
       │  4. JWT with userId,       │
       │     role, isAdmin          │
       │<───────────────────────────┤
       │                            │
       │  5. API calls with         │
       │     X-User-Email header    │
       ├───────────────────────────>│
```

### Board Member Whitelist

Board members are pre-registered in the database. On login:
1. Verify Google OAuth token
2. Extract email from ID token
3. Check email exists in `board_members` table
4. Return 401 if not a board member

```python
# Whitelist check
member = db.query(BoardMember).filter(BoardMember.email == email).first()
if not member:
    raise HTTPException(401, "Not a board member")
```

### Authorization Levels (Three-Tier RBAC)

| Level | Role | Permissions |
|-------|------|-------------|
| **Admin** | Board Admin | Full access, manage members, delete anything |
| **Chair** | Board Chair | Schedule meetings, manage agenda, upload docs |
| **Member** | Board Member | View documents, vote, sign, submit ideas |

### Auth Dependencies (FastAPI pattern from themany-forecasting)

```python
# backend/app/api/auth.py

async def get_current_user(
    x_user_email: str = Header(None),
    db: Session = Depends(get_db)
) -> Optional[BoardMember]:
    """Returns user or None (optional auth)"""
    if not x_user_email:
        return None
    return db.query(BoardMember).filter(BoardMember.email == x_user_email).first()

async def require_member(user: BoardMember = Depends(get_current_user)) -> BoardMember:
    """Enforces authentication (401 if missing)"""
    if not user:
        raise HTTPException(401, "Authentication required")
    return user

async def require_chair(user: BoardMember = Depends(require_member)) -> BoardMember:
    """Enforces Chair or Admin role (403 if not)"""
    if user.role not in ["chair", "admin"]:
        raise HTTPException(403, "Chair or Admin access required")
    return user

async def require_admin(user: BoardMember = Depends(require_member)) -> BoardMember:
    """Enforces Admin role (403 if not)"""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user
```

### Auth Endpoints

```
POST /api/auth/google          # Verify Google token, check whitelist
GET  /api/auth/user/{email}    # Get user details for frontend session
POST /api/auth/logout          # Invalidate session (frontend handles)
```

---

## 2. DocuSign Integration

### Authentication: JWT Grant Flow

Best for server-to-server integration. No user interaction after initial admin consent.

```python
# backend/app/services/docusign.py

class DocuSignService:
    def __init__(self):
        self.api_client = docusign.ApiClient()
        self.api_client.set_base_path(settings.DOCUSIGN_BASE_URL)

    async def get_access_token(self) -> str:
        """JWT Grant - regenerate when expired"""
        return await self.api_client.request_jwt_user_token(
            client_id=settings.DOCUSIGN_INTEGRATION_KEY,
            user_id=settings.DOCUSIGN_USER_ID,
            scopes=["signature", "impersonation"],
            private_key=settings.DOCUSIGN_PRIVATE_KEY,
            expires_in=3600
        )
```

### Envelope Operations

```python
async def send_for_signature(
    self,
    document: Document,
    signers: list[BoardMember],
    return_url: str
) -> str:
    """Create and send envelope, return envelope_id"""
    envelope = {
        "emailSubject": f"Board Document: {document.title}",
        "documents": [{
            "documentBase64": base64.b64encode(document.content).decode(),
            "name": document.filename,
            "documentId": "1"
        }],
        "recipients": {
            "signers": [
                {
                    "email": signer.email,
                    "name": signer.name,
                    "recipientId": str(i + 1),
                    "routingOrder": str(i + 1),
                    "clientUserId": str(signer.id),  # For embedded signing
                    "tabs": {"signHereTabs": [...]}
                }
                for i, signer in enumerate(signers)
            ]
        },
        "eventNotification": {
            "url": f"{settings.BASE_URL}/api/docusign/webhook",
            "requireAcknowledgment": True,
            "envelopeEvents": [
                {"envelopeEventStatusCode": "completed"},
                {"envelopeEventStatusCode": "declined"},
                {"envelopeEventStatusCode": "voided"}
            ]
        },
        "status": "sent"
    }
    return envelope_id

async def get_signing_url(self, envelope_id: str, signer: BoardMember) -> str:
    """Generate redirect URL for embedded signing"""

async def download_signed_document(self, envelope_id: str) -> bytes:
    """Download combined PDF with Certificate of Completion"""
```

### Webhook Handler

```python
@router.post("/api/docusign/webhook")
async def docusign_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    # Verify HMAC signature
    signature = request.headers.get("X-DocuSign-Signature-1")
    payload = await request.body()

    if not verify_hmac(payload, signature, settings.DOCUSIGN_HMAC_KEY):
        raise HTTPException(401, "Invalid signature")

    data = await request.json()
    envelope_id = data["data"]["envelopeId"]
    status = data["data"]["envelopeSummary"]["status"]

    # Update document status
    doc = db.query(Document).filter(Document.docusign_envelope_id == envelope_id).first()
    doc.signing_status = status

    if status == "completed":
        # Download and store signed PDF
        signed_pdf = await docusign_service.download_signed_document(envelope_id)
        doc.signed_file_path = await storage.save(signed_pdf, f"signed/{doc.id}.pdf")

    db.commit()
    return {"status": "ok"}
```

### Document Endpoints

```
GET    /api/documents                    # List documents (filter by type, status)
GET    /api/documents/{id}               # Get document details
POST   /api/documents                    # Upload new document (Chair+)
DELETE /api/documents/{id}               # Soft delete (Admin only)
POST   /api/documents/{id}/restore       # Restore deleted (Admin only)

# DocuSign operations
POST   /api/documents/{id}/send-for-signature  # Send to DocuSign
GET    /api/documents/{id}/signing-url         # Get embedded signing URL
GET    /api/documents/{id}/signing-status      # Check current status
GET    /api/documents/{id}/download            # Download signed PDF
```

---

## 3. Meeting Management

### Endpoints

```
GET    /api/meetings                     # List meetings
GET    /api/meetings/{id}                # Get meeting with agenda
POST   /api/meetings                     # Schedule meeting (Chair+)
PATCH  /api/meetings/{id}                # Update meeting (Chair+)
DELETE /api/meetings/{id}                # Cancel meeting (Chair+)

# Agenda
GET    /api/meetings/{id}/agenda         # Get agenda items
POST   /api/meetings/{id}/agenda         # Add agenda item (Chair+)
PATCH  /api/meetings/{id}/agenda/{item}  # Update item (Chair+)
DELETE /api/meetings/{id}/agenda/{item}  # Remove item (Chair+)
POST   /api/meetings/{id}/agenda/reorder # Reorder items (Chair+)

# Attendance
POST   /api/meetings/{id}/attendance     # Record attendance
GET    /api/meetings/{id}/attendance     # Get attendance record
```

---

## 4. Decision & Vote Tracking

### Vote Types

- **Standard Vote**: Yes/No/Abstain with quorum requirements
- **Consent Resolution**: Written consent without meeting
- **Resolution**: Formal board resolution (requires DocuSign)

### Endpoints

```
GET    /api/decisions                    # List decisions
GET    /api/decisions/{id}               # Get decision with votes
POST   /api/decisions                    # Create decision (Chair+)
PATCH  /api/decisions/{id}               # Update decision (Chair+)

# Voting
POST   /api/decisions/{id}/vote          # Cast vote (Member)
GET    /api/decisions/{id}/results       # Get voting results
POST   /api/decisions/{id}/close         # Close voting (Chair+)

# Resolution workflow
POST   /api/decisions/{id}/create-resolution  # Generate resolution doc
POST   /api/decisions/{id}/send-for-signature # Send resolution to DocuSign
```

---

## 5. Idea Backlog

### Endpoints

```
GET    /api/ideas                        # List ideas
GET    /api/ideas/{id}                   # Get idea with comments
POST   /api/ideas                        # Submit idea (Member)
PATCH  /api/ideas/{id}                   # Update idea (Owner or Chair+)
DELETE /api/ideas/{id}                   # Soft delete (Admin only)

# Comments
GET    /api/ideas/{id}/comments          # Get comments
POST   /api/ideas/{id}/comments          # Add comment (Member)
DELETE /api/ideas/{id}/comments/{cid}    # Delete comment (Owner or Admin)

# Workflow
POST   /api/ideas/{id}/promote           # Promote to decision (Chair+)
```

---

## 6. Database Schema

### Core Tables

```sql
-- Board members (pre-registered whitelist)
CREATE TABLE board_members (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',  -- admin/chair/member
    google_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);

-- Documents
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- resolution/minutes/consent/financial/legal
    description TEXT,
    file_path TEXT NOT NULL,
    uploaded_by_id INTEGER REFERENCES board_members(id),

    -- DocuSign integration
    docusign_envelope_id VARCHAR(255),
    signing_status VARCHAR(50),  -- null/sent/delivered/completed/declined/voided
    signed_file_path TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);

-- Meetings
CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    scheduled_date TIMESTAMP NOT NULL,
    location VARCHAR(255),  -- Room name or "Virtual"
    meeting_link TEXT,      -- Zoom/Meet URL
    status VARCHAR(20) DEFAULT 'scheduled',  -- scheduled/in_progress/completed/cancelled

    created_by_id INTEGER REFERENCES board_members(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);

-- Agenda items
CREATE TABLE agenda_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INTEGER,
    presenter_id INTEGER REFERENCES board_members(id),
    order_index INTEGER NOT NULL,

    -- Link to related decision
    decision_id INTEGER REFERENCES decisions(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance
CREATE TABLE meeting_attendance (
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES board_members(id),
    status VARCHAR(20) NOT NULL,  -- present/absent/excused
    joined_at TIMESTAMP,
    left_at TIMESTAMP,
    PRIMARY KEY (meeting_id, member_id)
);

-- Decisions
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(20) NOT NULL,  -- vote/consent/resolution
    status VARCHAR(20) DEFAULT 'draft',  -- draft/open/closed

    meeting_id INTEGER REFERENCES meetings(id),  -- null for async votes
    deadline TIMESTAMP,

    -- For resolutions
    resolution_number VARCHAR(50),
    document_id INTEGER REFERENCES documents(id),

    created_by_id INTEGER REFERENCES board_members(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);

-- Votes
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id) ON DELETE CASCADE,
    member_id INTEGER REFERENCES board_members(id),
    vote VARCHAR(10) NOT NULL,  -- yes/no/abstain
    cast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (decision_id, member_id)
);

-- Ideas
CREATE TABLE ideas (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'new',  -- new/under_review/approved/rejected/promoted

    submitted_by_id INTEGER REFERENCES board_members(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- If promoted to decision
    promoted_to_decision_id INTEGER REFERENCES decisions(id),

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);

-- Comments (for ideas)
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    idea_id INTEGER REFERENCES ideas(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES board_members(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP,
    deleted_by_id INTEGER REFERENCES board_members(id)
);
```

### Audit Tables

```sql
-- Document access log (who viewed what)
CREATE TABLE document_access_log (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    member_id INTEGER REFERENCES board_members(id),
    action VARCHAR(20) NOT NULL,  -- view/download/sign
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- General audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- document/meeting/decision/idea
    entity_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,  -- create/update/delete/restore
    changed_by_id INTEGER REFERENCES board_members(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changes JSONB  -- Before/after values
);
```

---

## 7. API Structure (FastAPI)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routers, CORS
│   ├── config.py            # Settings via pydantic-settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth dependencies & endpoints
│   │   ├── documents.py     # Document endpoints
│   │   ├── meetings.py      # Meeting endpoints
│   │   ├── decisions.py     # Decision/vote endpoints
│   │   ├── ideas.py         # Idea endpoints
│   │   └── webhooks.py      # DocuSign webhooks
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── member.py        # BoardMember model
│   │   ├── document.py      # Document model
│   │   ├── meeting.py       # Meeting, AgendaItem, Attendance
│   │   ├── decision.py      # Decision, Vote models
│   │   └── idea.py          # Idea, Comment models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── member.py        # Pydantic schemas for members
│   │   ├── document.py      # Document schemas
│   │   ├── meeting.py       # Meeting schemas
│   │   ├── decision.py      # Decision schemas
│   │   └── idea.py          # Idea schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── docusign.py      # DocuSign API wrapper
│   │   └── storage.py       # File storage (S3/GCS)
│   │
│   └── db/
│       ├── __init__.py
│       ├── session.py       # SQLAlchemy session
│       └── seed.py          # Initial data seeding
│
├── migrations/              # Alembic migrations
├── tests/
│   ├── integration/
│   ├── unit/
│   └── conftest.py
│
├── requirements.txt
└── Dockerfile
```

---

## 8. Security Considerations

1. **Authentication**: Google OAuth2 only - no password storage
2. **Authorization**: Role-based access control on all endpoints
3. **Audit Trail**: Log all document access, votes, and admin actions
4. **Data Encryption**: TLS in transit, encrypted at rest
5. **DocuSign Webhooks**: HMAC verification on all callbacks
6. **Soft Deletes**: Never hard delete - preserve audit trail
7. **Input Validation**: Pydantic schemas on all inputs

---

## 9. Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/tmg_board

# Google OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# DocuSign
DOCUSIGN_INTEGRATION_KEY=xxx
DOCUSIGN_USER_ID=xxx
DOCUSIGN_ACCOUNT_ID=xxx
DOCUSIGN_BASE_URL=https://demo.docusign.net/restapi
DOCUSIGN_PRIVATE_KEY_PATH=./keys/docusign_private.pem
DOCUSIGN_HMAC_KEY=xxx

# Storage
STORAGE_TYPE=s3  # or gcs
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
S3_BUCKET=tmg-board-documents

# App
BASE_URL=https://tmgboard.themany.com
DEBUG=false
```

---

## 10. Agreed Technical Decisions

Based on sync with Beth:

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Frontend Framework** | Next.js 16+ (App Router) | Matches themany-forecasting |
| **Real-time Updates** | Polling (30-60s) | Simpler for MVP, small user base |
| **Document Viewer** | Client-side PDF.js | Keeps backend simple |
| **Email Notifications** | Backend handles queuing | Frontend just calls API |
| **Calendar** | "Add to Calendar" button | Generate gcal URL, no API needed |
| **File Uploads** | S3 presigned URLs | Direct upload, keeps files off API |
| **Offline** | Skip for MVP | Board members have connectivity |
| **Meeting Recordings** | Link only (no embed) | Keeps it simple |
| **Document Annotations** | Skip for MVP | Future enhancement |
| **Mobile** | PWA/responsive web | Native app if needed later |
| **Audit Log UI** | Yes, admin-only | Expose /api/admin/audit endpoint |

---

## 11. Next Steps

- [x] Research Google Auth patterns
- [x] Research DocuSign API integration
- [x] Review themany-forecasting patterns
- [ ] Sync with Beth on frontend requirements
- [ ] Finalize open questions
- [ ] Get spec approval before coding

---

*Spec updated with research findings. Ready for Beth collaboration.*
