# Phase 03: Transcripts & Minutes Generator - Research

**Researched:** 2026-03-04
**Domain:** Meeting transcript management (CRUD, file upload) + AI-driven minutes generation
**Confidence:** HIGH

## Summary

Phase 03 adds transcript management to completed meetings and an AI-powered Minutes Generator agent that produces formatted minutes documents from those transcripts. The scope is well-bounded: a new `MeetingTranscript` model for storing transcript text, backend API endpoints for paste and file upload, a Transcript section on the meeting detail page, integration with the Phase 01 agent infrastructure for minutes generation, and a database migration that also removes the unused `recording_url` field from the Meeting model.

The transcript feature is a standard CRUD operation with file upload -- this project already has established patterns for both (meetings API, documents API with `UploadFile`). The Minutes Generator agent follows the same lightweight agent loop pattern from Phase 01, calling the board's own REST API tools to read the transcript and create a formatted minutes document. The generated minutes will be stored as an HTML Document in the existing documents system, linked to the meeting via a new `MeetingDocument` junction table.

**Primary recommendation:** Store transcript text directly in a `meeting_transcripts` table (one-per-meeting), use the existing document upload pattern for .txt file handling, create a `MeetingDocument` junction to link generated minutes documents to their source meeting, and configure the Minutes Generator as a built-in agent with tools for reading transcripts and creating documents.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRANS-01 | Chair/admin can paste transcript text for a completed meeting | MeetingTranscript model with Text column, POST endpoint with JSON body, Transcript section in meeting detail page |
| TRANS-02 | Chair/admin can upload a transcript file (.txt) for a meeting | Same MeetingTranscript model, separate upload endpoint using UploadFile/File pattern from documents API |
| TRANS-03 | Any board member can view a meeting's transcript | GET endpoint with require_member auth, read-only transcript display on meeting detail page |
| TRANS-04 | Minutes Generator agent can produce minutes document from a transcript | Built-in agent configuration seeded in DB, tools for get_meeting_transcript and create_minutes_document, generates HTML document linked via MeetingDocument |
| TRANS-05 | Recording URL field is removed from meetings model | Alembic migration drops recording_url column, remove from UpdateMeetingRequest schema, remove from frontend MeetingDetail interface and UI |
| BUILT-02 | Minutes Generator agent can create minutes document from meeting transcript | Same as TRANS-04 -- agent config, system prompt, and tool definitions |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.25 | MeetingTranscript model, MeetingDocument junction | Already in project, Mapped column style established |
| Alembic | >=1.13.1 | Migration: add transcript tables, drop recording_url | Already in project, manual revision pattern established (not autogenerate) |
| FastAPI | >=0.115.0 | Transcript API endpoints (CRUD + file upload) | Already in project |
| python-multipart | >=0.0.6 | File upload support for .txt transcripts | Already in project (used by documents API) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| LiteLLM | >=1.80.0 | Minutes Generator agent LLM calls | Phase 01 dependency; agent invocation for minutes generation |
| httpx | >=0.26.0 | Agent tools calling board REST API | Phase 01 pattern; tools call transcript and document endpoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Text column for transcript | File-only storage | Text column allows paste-to-save (TRANS-01) without file creation overhead. File upload (TRANS-02) reads file content into the same Text column. Simpler than managing files for plain text. |
| MeetingDocument junction table | Direct `meeting_id` FK on Document | Junction table is more flexible (multiple documents per meeting, multiple meetings per document). Also keeps the existing Document model clean -- no schema changes to documents table. |
| Storing minutes as HTML Document | Storing minutes as plain text field | HTML Document uses existing document infrastructure (versioning, PDF viewer, download). Minutes can have structured formatting. Reuses document types system. |

**Installation:**
No new dependencies. All required packages are already in `backend/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  models/
    meeting.py           # ADD: MeetingTranscript model, MeetingDocument model
    __init__.py           # ADD: MeetingTranscript, MeetingDocument to imports
  api/
    meetings.py           # MODIFY: Add transcript endpoints, remove recording_url
    transcripts.py        # NEW: Transcript API (paste, upload, view, delete)
  schemas/
    transcript.py         # NEW: Pydantic schemas for transcript endpoints
  tools/
    transcripts.py        # NEW: Agent tools for reading transcripts, creating minutes
  migrations/
    versions/
      005_add_transcripts.py  # NEW: Add meeting_transcripts, meeting_documents; drop recording_url

frontend/src/
  app/meetings/[id]/
    page.tsx              # MODIFY: Add Transcript section, remove Recording section
  components/
    transcript-section.tsx # NEW: Transcript paste/upload/view component
    minutes-generator.tsx  # NEW: "Generate Minutes" button + inline agent display
  lib/
    api.ts                # MODIFY: Add transcript API methods to meetingsApi
```

### Pattern 1: MeetingTranscript Model (One-Per-Meeting)
**What:** A dedicated table for storing transcript text with metadata. One transcript per meeting (unique constraint). Text stored as PostgreSQL TEXT column (unlimited length).
**When to use:** Every transcript operation.
**Example:**
```python
# Source: Follows existing Meeting model pattern in backend/app/models/meeting.py

class MeetingTranscript(Base):
    """Transcript text for a completed meeting."""
    __tablename__ = "meeting_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False, unique=True  # One transcript per meeting
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full transcript text
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "paste" or "upload"
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Only for uploads
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcript")
    created_by: Mapped["BoardMember"] = relationship("BoardMember")
```

### Pattern 2: MeetingDocument Junction Table
**What:** Links meetings to their associated documents (generated minutes, attached files). Many-to-many with metadata about the relationship.
**When to use:** When the Minutes Generator creates a document, or when users manually link documents to meetings.
**Example:**
```python
class MeetingDocument(Base):
    """Links documents to meetings (e.g., generated minutes)."""
    __tablename__ = "meeting_documents"

    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(30), nullable=False  # "minutes", "agenda", "attachment"
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="documents")
    document: Mapped["Document"] = relationship("Document")
    created_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember")
```

### Pattern 3: Transcript API Endpoints (follows meetings.py patterns)
**What:** CRUD endpoints for transcript management nested under meetings.
**When to use:** All transcript operations.
**Example:**
```python
# POST /api/meetings/{meeting_id}/transcript        — Paste transcript text
# POST /api/meetings/{meeting_id}/transcript/upload  — Upload .txt file
# GET  /api/meetings/{meeting_id}/transcript         — View transcript
# PUT  /api/meetings/{meeting_id}/transcript         — Replace transcript
# DELETE /api/meetings/{meeting_id}/transcript        — Remove transcript

@router.post("/{meeting_id}/transcript")
async def add_transcript(
    meeting_id: int,
    request: CreateTranscriptRequest,  # { content: str }
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
        Meeting.status == "completed",
    ).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found or not completed")

    existing = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if existing:
        raise HTTPException(400, "Transcript already exists. Use PUT to replace.")

    transcript = MeetingTranscript(
        meeting_id=meeting_id,
        content=request.content,
        source="paste",
        char_count=len(request.content),
        created_by_id=current_user.id,
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript
```

### Pattern 4: Minutes Generator Agent Configuration
**What:** Database-seeded agent config for the Minutes Generator built-in agent. Uses Phase 01 agent infrastructure.
**When to use:** Agent is invoked from the meeting detail page after a transcript is attached.
**Example:**
```python
# Seed data for the Minutes Generator agent (in migration or seed script)
agent_config = {
    "name": "Minutes Generator",
    "slug": "minutes-generator",
    "description": "Generates formatted board meeting minutes from a meeting transcript",
    "system_prompt": """You are a professional board meeting minutes generator.
Given a meeting transcript, produce structured meeting minutes in HTML format.

The minutes should include:
- Meeting title, date, time, and location
- Attendees present and absent
- Each agenda item discussed with key points
- Decisions made and action items
- Motions and votes (if any)
- Meeting adjournment time

Format the output as clean HTML suitable for a formal board document.
Use <h1> for the title, <h2> for sections, <ul>/<li> for lists, and <table> for attendance.""",
    "model": "anthropic/claude-sonnet-4-5-20250929",
    "max_iterations": 3,
    "temperature": 0.2,
    "allowed_tool_names": ["get_meeting_details", "get_meeting_transcript", "create_minutes_document"],
    "is_active": True,
}
```

### Pattern 5: Minutes Generator Tool Definitions
**What:** Tools that the Minutes Generator agent can call to read meeting data and create the minutes document.
**When to use:** During agent execution.
**Example:**
```python
# Tool: get_meeting_transcript
# Calls: GET /api/meetings/{meeting_id}/transcript
# Returns: transcript text + meeting metadata

# Tool: get_meeting_details
# Calls: GET /api/meetings/{meeting_id} + GET /api/meetings/{meeting_id}/agenda
# + GET /api/meetings/{meeting_id}/attendance
# Returns: meeting info, agenda items, attendance list

# Tool: create_minutes_document
# Calls: POST /api/documents/upload (multipart form with HTML file)
# + POST /api/meetings/{meeting_id}/documents (link doc to meeting)
# Returns: document ID and URL

# The agent flow:
# 1. Agent calls get_meeting_details to get meeting structure
# 2. Agent calls get_meeting_transcript to get the full transcript
# 3. Agent generates formatted HTML minutes from the transcript + meeting context
# 4. Agent calls create_minutes_document to save the HTML and link it to the meeting
```

### Anti-Patterns to Avoid
- **Storing transcripts as files on disk:** Transcripts are plain text. Database TEXT columns handle arbitrarily large text and are simpler to query, backup, and serve. Only use file storage for binary files (PDF, images).
- **Generating minutes without meeting context:** The agent needs meeting title, date, agenda items, and attendance -- not just the transcript. The tools must provide complete meeting context for proper minutes formatting.
- **Modifying the Document model for meeting links:** Don't add a `meeting_id` column to the documents table. Use a junction table (`meeting_documents`) to keep the relationship decoupled and support multiple documents per meeting.
- **Allowing transcript editing on non-completed meetings:** Transcripts are for completed meetings only. The API must enforce `meeting.status == "completed"`.
- **Making transcript a required field:** Not all completed meetings will have transcripts. The transcript is entirely optional.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File upload handling | Custom multipart parser | FastAPI `UploadFile` + `File(...)` | Already proven in documents API. Handles streaming, validation, content reading. |
| Text file encoding detection | Custom charset detection | `content.decode('utf-8')` with fallback to `'latin-1'` | Meeting transcripts are virtually always UTF-8 or ASCII. Complex encoding detection (chardet) is overkill. |
| Minutes document formatting | Custom HTML template engine | Let the LLM generate HTML directly | The agent's system prompt specifies HTML output. LLMs produce excellent structured HTML. No template engine needed. |
| Agent loop for minutes generation | Custom orchestration | Phase 01 agent runner (`run_agent` function) | The agent infrastructure handles LLM calls, tool execution, streaming, and error handling. Minutes Generator is just another agent config. |
| Transcript text sanitization | Custom XSS filtering | Store as-is, escape on render | Transcript is plain text displayed in a `<pre>` or `whitespace-pre-wrap` container. React auto-escapes text content. No HTML injection risk. |

**Key insight:** This phase is primarily a CRUD feature (transcript management) plus an agent configuration (Minutes Generator). Most of the complexity is already handled by existing patterns in the codebase.

## Common Pitfalls

### Pitfall 1: Large Transcript Text Hitting Request Size Limits
**What goes wrong:** Users paste or upload multi-hour meeting transcripts that can be 200KB+ of text. FastAPI/Starlette has a default request body limit.
**Why it happens:** Default max request body size may be 1MB, which is fine, but proxy layers (nginx, Railway) may have lower limits.
**How to avoid:** (1) Set explicit max content length in the API endpoint (e.g., 5MB for text, which covers even very long meetings). (2) Add frontend validation showing character count with a warning above 500,000 characters. (3) For file uploads, validate file size before reading into memory.
**Warning signs:** 413 errors on paste/upload, silent truncation.

### Pitfall 2: Token Limit Exceeded When Passing Transcript to LLM
**What goes wrong:** A long transcript exceeds the LLM's context window when combined with the system prompt and tool results.
**Why it happens:** Board meeting transcripts can be 50,000+ words. Even Claude's 200K context has limits when combined with other content.
**How to avoid:** (1) Calculate approximate token count before invoking the agent (roughly chars/4). (2) If the transcript is too long, truncate or chunk it with a warning. (3) Use a model with a large context window (Claude Sonnet 3.5 supports 200K tokens). (4) Consider summarizing very long transcripts in chunks first.
**Warning signs:** LLM API errors about context length, incomplete minutes generation.

### Pitfall 3: Migration Order When Removing recording_url
**What goes wrong:** Dropping the `recording_url` column while the application code still references it causes runtime errors during deployment.
**Why it happens:** Migration runs before the new code is deployed, or the old code is still running.
**How to avoid:** (1) Remove all code references to `recording_url` FIRST (model, schemas, API, frontend). (2) The migration drops the column. (3) Deploy code and migration together. Since Railway auto-deploys, ensure the migration and code changes are in the same deployment.
**Warning signs:** AttributeError on `meeting.recording_url`, 500 errors on meeting API.

### Pitfall 4: Forgetting to Update Both UpdateMeetingRequest and Frontend
**What goes wrong:** `recording_url` is removed from the backend model but still present in the frontend `meetingsApi.update()` or the `UpdateMeetingRequest` Pydantic schema.
**Why it happens:** The field exists in multiple places: backend model, backend schema, backend API handler, frontend API types, frontend detail page UI.
**How to avoid:** Systematic sweep of all occurrences. Grep for `recording_url` and `recording` across the entire codebase.
**Warning signs:** Frontend sending `recording_url` in PATCH requests that get silently ignored (Pydantic schema change) or cause errors.

### Pitfall 5: Minutes Document Not Linked Back to Meeting
**What goes wrong:** The agent creates a Document (via the documents API) but doesn't create the MeetingDocument junction record, so the meeting detail page doesn't show the generated minutes.
**Why it happens:** The `create_minutes_document` tool needs to do TWO things: create the document AND link it.
**How to avoid:** The tool should be a single operation that creates the Document record, writes the HTML file, creates the MeetingDocument junction record, and returns the document ID -- all in one transaction.
**Warning signs:** Generated minutes appear in the Documents page but not on the meeting detail page.

## Code Examples

### Transcript Paste Endpoint
```python
# Source: Follows pattern from backend/app/api/meetings.py

class CreateTranscriptRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=5_000_000)

@router.post("/{meeting_id}/transcript")
async def add_transcript(
    meeting_id: int,
    request: CreateTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Add a transcript to a completed meeting (paste). Chair/Admin only."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()

    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if meeting.status != "completed":
        raise HTTPException(400, "Transcripts can only be added to completed meetings")

    existing = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if existing:
        raise HTTPException(400, "Transcript already exists for this meeting")

    transcript = MeetingTranscript(
        meeting_id=meeting_id,
        content=request.content,
        source="paste",
        char_count=len(request.content),
        created_by_id=current_user.id,
    )
    db.add(transcript)

    db.add(AuditLog(
        entity_type="transcript",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="create",
        changed_by_id=current_user.id,
        changes={"source": "paste", "char_count": len(request.content)}
    ))

    db.commit()
    db.refresh(transcript)
    return transcript
```

### Transcript File Upload Endpoint
```python
# Source: Follows pattern from backend/app/api/documents.py upload_document()

@router.post("/{meeting_id}/transcript/upload")
async def upload_transcript(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Upload a .txt transcript file for a completed meeting. Chair/Admin only."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()

    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if meeting.status != "completed":
        raise HTTPException(400, "Transcripts can only be added to completed meetings")

    existing = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if existing:
        raise HTTPException(400, "Transcript already exists for this meeting")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.txt'):
        raise HTTPException(400, "Only .txt files are accepted")

    # Read and decode
    raw = await file.read()
    if len(raw) > 5_000_000:  # 5MB limit
        raise HTTPException(400, "File too large (max 5MB)")

    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        content = raw.decode('latin-1')

    transcript = MeetingTranscript(
        meeting_id=meeting_id,
        content=content,
        source="upload",
        original_filename=file.filename,
        char_count=len(content),
        created_by_id=current_user.id,
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript
```

### Frontend Transcript Section Component
```typescript
// Source: Follows patterns from frontend/src/app/meetings/[id]/page.tsx

// In the meeting detail page sidebar (replacing the Recording card):
// - If meeting is completed and no transcript: show paste/upload buttons (chair/admin)
// - If transcript exists: show collapsible transcript viewer
// - If transcript exists + chair/admin: show "Generate Minutes" button

interface TranscriptSectionProps {
  meetingId: string;
  meetingStatus: string;
  isChairOrAdmin: boolean;
  transcript: { content: string; source: string; char_count: number; created_at: string } | null;
  onTranscriptAdded: () => void;
}
```

### Frontend API Extension
```typescript
// Source: Follows pattern from frontend/src/lib/api.ts meetingsApi

// Add to meetingsApi object:
getTranscript: async (meetingId: string): Promise<Transcript | null> => {
  try {
    return await api.get(`/meetings/${meetingId}/transcript`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
},

addTranscript: async (meetingId: string, content: string): Promise<Transcript> => {
  return api.post(`/meetings/${meetingId}/transcript`, { content });
},

uploadTranscript: async (meetingId: string, file: File): Promise<Transcript> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/meetings/${meetingId}/transcript/upload`, {
    method: "POST",
    headers: { "X-User-Email": api["userEmail"] || "" },
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error.detail || "Failed to upload transcript");
  }
  return response.json();
},

deleteTranscript: async (meetingId: string): Promise<void> => {
  return api.delete(`/meetings/${meetingId}/transcript`);
},

replaceTranscript: async (meetingId: string, content: string): Promise<Transcript> => {
  return api.put(`/meetings/${meetingId}/transcript`, { content });
},
```

### Alembic Migration
```python
# Source: Follows pattern from backend/migrations/versions/004_add_timezone_support.py

"""Add transcript support, drop recording_url

Revision ID: 005_add_transcripts
Revises: 004_add_timezone_support
"""
from alembic import op
import sqlalchemy as sa

revision = '005_add_transcripts'
down_revision = '004_add_timezone_support'

def upgrade() -> None:
    # Create meeting_transcripts table
    op.create_table('meeting_transcripts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),  # "paste" or "upload"
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('board_members.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create meeting_documents junction table
    op.create_table('meeting_documents',
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('relationship_type', sa.String(30), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('board_members.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Drop recording_url from meetings
    op.drop_column('meetings', 'recording_url')

def downgrade() -> None:
    op.add_column('meetings', sa.Column('recording_url', sa.Text(), nullable=True))
    op.drop_table('meeting_documents')
    op.drop_table('meeting_transcripts')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `recording_url` field on Meeting | Dedicated MeetingTranscript model with text content | Phase 03 (this phase) | Transcripts are first-class entities with metadata, not just a URL field |
| No meeting-document linkage | MeetingDocument junction table | Phase 03 (this phase) | Generated minutes and other documents can be formally linked to meetings |
| Manual minutes writing | AI-generated minutes from transcripts | Phase 03 (this phase) | Chairs can get a first draft of minutes in seconds instead of manually writing them |

**Deprecated/outdated:**
- `recording_url` on Meeting model: Being removed. Was never fully used (UI shows "No recording available" placeholder). Replaced by transcript paste/upload.

## Files to Modify (Comprehensive List)

### Backend - Models
| File | Action | Changes |
|------|--------|---------|
| `backend/app/models/meeting.py` | MODIFY | Add `MeetingTranscript` and `MeetingDocument` classes. Add `transcript` and `documents` relationships to `Meeting`. Remove `recording_url` column from `Meeting`. |
| `backend/app/models/__init__.py` | MODIFY | Add `MeetingTranscript`, `MeetingDocument` to imports and `__all__` |

### Backend - API
| File | Action | Changes |
|------|--------|---------|
| `backend/app/api/meetings.py` | MODIFY | Remove `recording_url` from `UpdateMeetingRequest` schema and update handler. Add transcript endpoints (or import from transcripts router). |
| `backend/app/api/transcripts.py` | CREATE | Transcript CRUD endpoints: paste, upload, view, replace, delete. Meeting-document linking endpoint. |
| `backend/app/main.py` | MODIFY | Register transcripts router (if separate from meetings) |

### Backend - Schemas
| File | Action | Changes |
|------|--------|---------|
| `backend/app/schemas/transcript.py` | CREATE | `CreateTranscriptRequest`, `TranscriptResponse`, `TranscriptSummary` Pydantic models |

### Backend - Agent Tools
| File | Action | Changes |
|------|--------|---------|
| `backend/app/tools/transcripts.py` | CREATE | Agent tool definitions and executors: `get_meeting_transcript`, `get_meeting_details`, `create_minutes_document` |

### Backend - Migrations
| File | Action | Changes |
|------|--------|---------|
| `backend/migrations/versions/005_add_transcripts.py` | CREATE | Create `meeting_transcripts` table, `meeting_documents` table, drop `recording_url` column |

### Frontend - Pages
| File | Action | Changes |
|------|--------|---------|
| `frontend/src/app/meetings/[id]/page.tsx` | MODIFY | Remove Recording card from sidebar. Add Transcript section. Add "Generate Minutes" button. Fetch transcript data in `fetchMeeting`. Remove `recording` from `MeetingDetail` interface. |

### Frontend - Components
| File | Action | Changes |
|------|--------|---------|
| `frontend/src/components/transcript-section.tsx` | CREATE | Transcript paste/upload/view component with collapsible text display |
| `frontend/src/components/minutes-generator.tsx` | CREATE | "Generate Minutes" button that invokes the agent via SSE and shows progress inline |

### Frontend - API
| File | Action | Changes |
|------|--------|---------|
| `frontend/src/lib/api.ts` | MODIFY | Add transcript methods to `meetingsApi`: `getTranscript`, `addTranscript`, `uploadTranscript`, `replaceTranscript`, `deleteTranscript`. Add `Transcript` TypeScript interface. Remove `recording` from `MeetingDetail`-related types if present. |

## Open Questions

1. **Transcript character/size limit**
   - What we know: PostgreSQL TEXT column has no practical limit. The real constraint is LLM context window for minutes generation.
   - What's unclear: What is a reasonable max size to enforce at the API level?
   - Recommendation: Set 5MB (approximately 5 million characters / ~1.25M tokens) as the hard limit. This covers even very long meetings. Add a frontend warning above 200,000 characters noting it may impact minutes generation quality.

2. **Minutes document format**
   - What we know: The existing Document model supports HTML files (`file_path` ending in `.html`). The documents API has a `render` endpoint for HTML viewing.
   - What's unclear: Should minutes be stored as HTML or as a styled PDF?
   - Recommendation: HTML. The project already has HTML document rendering infrastructure. The agent can generate well-structured HTML directly. PDF generation can be added later if needed.

3. **Should transcript replacement be allowed?**
   - What we know: TRANS-01 and TRANS-02 describe adding a transcript. No explicit mention of editing/replacing.
   - What's unclear: Can users fix typos or paste a corrected transcript?
   - Recommendation: Support replacement via PUT endpoint. If minutes have already been generated, warn the user that the existing minutes may be stale. Don't auto-regenerate.

4. **Agent dependency: Is Phase 01 complete?**
   - What we know: Phase 03 depends on Phase 01 for the agent infrastructure (agent runner, SSE streaming, tool system).
   - What's unclear: Will Phase 01 be complete before Phase 03 starts?
   - Recommendation: Plan Phase 03 in two waves: (1) Transcript CRUD + migration + UI (no agent dependency), (2) Minutes Generator agent configuration + tools + "Generate Minutes" button (requires Phase 01). Wave 1 can proceed independently.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python backend) |
| Config file | None -- needs setup |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ --tb=short -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRANS-01 | Chair/admin can paste transcript for completed meeting | unit | `pytest tests/test_transcripts.py::test_paste_transcript -x` | No -- Wave 0 |
| TRANS-01 | Non-chair cannot paste transcript | unit | `pytest tests/test_transcripts.py::test_paste_transcript_forbidden -x` | No -- Wave 0 |
| TRANS-01 | Cannot paste transcript for non-completed meeting | unit | `pytest tests/test_transcripts.py::test_paste_transcript_not_completed -x` | No -- Wave 0 |
| TRANS-02 | Chair/admin can upload .txt transcript | unit | `pytest tests/test_transcripts.py::test_upload_transcript -x` | No -- Wave 0 |
| TRANS-02 | Non-.txt files are rejected | unit | `pytest tests/test_transcripts.py::test_upload_non_txt_rejected -x` | No -- Wave 0 |
| TRANS-03 | Any board member can view transcript | unit | `pytest tests/test_transcripts.py::test_view_transcript -x` | No -- Wave 0 |
| TRANS-04 | Minutes Generator produces document from transcript | integration | `pytest tests/test_minutes_generator.py::test_generate_minutes -x` | No -- Wave 0 |
| TRANS-05 | recording_url removed from model and API | unit | `pytest tests/test_transcripts.py::test_recording_url_removed -x` | No -- Wave 0 |
| TRANS-05 | Migration drops column and creates tables | unit | Manual verification via `alembic upgrade head` | N/A |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_transcripts.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py` -- Shared fixtures (test DB, test client, test users with roles)
- [ ] `backend/tests/test_transcripts.py` -- Covers TRANS-01, TRANS-02, TRANS-03, TRANS-05
- [ ] `backend/tests/test_minutes_generator.py` -- Covers TRANS-04, BUILT-02 (integration test with mocked LLM)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` (test dependencies)
- [ ] Test database setup: SQLite in-memory or test PostgreSQL for isolated testing

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/models/meeting.py` -- Current Meeting model with `recording_url` field
- Codebase analysis: `backend/app/models/document.py` -- Document, DocumentVersion, RelatedDocument models (established patterns)
- Codebase analysis: `backend/app/api/documents.py` -- File upload pattern using `UploadFile`, `File(...)`, `Form(...)`
- Codebase analysis: `backend/app/api/meetings.py` -- Meeting CRUD endpoints, `UpdateMeetingRequest` with `recording_url`
- Codebase analysis: `frontend/src/app/meetings/[id]/page.tsx` -- Meeting detail page with Recording card (lines 829-848)
- Codebase analysis: `frontend/src/lib/api.ts` -- API client patterns, `meetingsApi` and `documentsApi` interfaces
- Codebase analysis: `backend/migrations/versions/004_add_timezone_support.py` -- Migration pattern (manual revisions)
- Phase 01 Research: `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` -- Agent loop, tool definitions, SSE streaming patterns

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 documentation -- Mapped column style, relationship patterns (verified by existing codebase usage)
- FastAPI documentation -- UploadFile, File, Form for multipart uploads (verified by existing documents API)

### Tertiary (LOW confidence)
- None. All findings are verified by existing codebase patterns.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies. All libraries already in requirements.txt.
- Architecture: HIGH -- All patterns (CRUD endpoints, file upload, models, migrations, junction tables) have direct precedents in the existing codebase.
- Pitfalls: HIGH -- Based on concrete analysis of existing code, data flow, and deployment patterns.
- Agent integration: MEDIUM -- Depends on Phase 01 completion. Agent config and tools follow the researched Phase 01 patterns but haven't been validated against running code.

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days -- stable domain, no rapidly changing dependencies)
