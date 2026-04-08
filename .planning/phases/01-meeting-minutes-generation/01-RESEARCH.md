# Phase 1: Meeting Minutes Generation - Research

**Researched:** 2026-04-07
**Domain:** FastAPI + Anthropic SDK + Jinja2 (backend); Next.js 16 + React 19 (frontend)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**AI Framework**
- Use Anthropic SDK (`anthropic` Python package) directly — no LangChain, LiteLLM, or other framework
- Use Jinja2 for prompt templates (already a transitive dependency of FastAPI)
- Templates stored in database as plain text strings
- AsyncAnthropic client for non-blocking LLM calls in FastAPI async handlers

**Backend Architecture**
- New `DocumentTemplate` SQLAlchemy model for admin-configurable prompt templates
- New `MeetingMinutes` model to link generated minutes to meetings (or extend existing Document model with meeting_id FK)
- New service: `app/services/document_generator.py` following existing singleton pattern (like StorageService)
- New API router for generation endpoints
- Anthropic API key stored as environment variable in config.py Settings
- Generated markdown stored via existing StorageService (local or S3)

**Frontend — Meeting Detail Page**
- Replace "Recording" section (which says "Recording will be available after the meeting") with "Meeting Minutes" section
- "Create Meeting Minutes" button opens a modal
- Modal has: textarea for pasting transcript, "Generate Minutes" button
- Generation is async — show loading state while LLM processes
- Generated minutes displayed inline within the meeting detail page (similar to agenda display)
- Minutes should be printable (print-friendly CSS)

**Admin Section**
- Template management UI under existing admin section
- Follow existing RBAC — admin role required
- Ability to view and edit prompt templates for different document types
- Starting with "meeting_minutes" template type

**Minutes Format**
- Markdown with specific formatting suitable for board minutes
- Includes: meeting metadata (date, attendees, location), agenda items covered, discussions, decisions, action items
- Must render cleanly in-app and be printable

### Claude's Discretion
- Specific markdown template structure for minutes output
- Error handling for failed LLM calls
- Whether to use streaming for generation progress
- Alembic migration details for new models
- Exact API endpoint paths and request/response schemas
- How to handle regeneration (allow re-generating minutes for same meeting)

### Deferred Ideas (OUT OF SCOPE)
- DocuSign signing of generated minutes (future phase)
- PDF export of minutes (future)
- Auto-transcription from recording URL (future)
- Multiple document type generation beyond minutes (future — but architecture supports it)
- Version history for regenerated minutes (future)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| M-1 | Backend AI service layer using Anthropic SDK + Jinja2 templates for document generation | AsyncAnthropic usage patterns, Jinja2 template rendering, service singleton pattern from StorageService |
| M-2 | Database-driven DocumentTemplate model so admins can configure/edit generation prompts | SQLAlchemy mapped_column patterns from existing models, Alembic migration pattern from 004_add_timezone_support.py |
| M-3 | Meeting detail page replaces "Recording" section with "Meeting Minutes" section, with modal | Exact "Recording" Card JSX identified in page.tsx lines 830-849; modal pattern from existing modals |
| M-4 | Generated minutes stored as markdown, viewable inline (similar to agenda display) and printable | StorageService.save() for markdown bytes; react-markdown for rendering; print CSS |
| M-5 | Admin section includes template management UI for viewing/editing document generation prompts, following existing RBAC patterns | require_admin dependency pattern; admin settings page tab pattern |
</phase_requirements>

---

## Summary

This phase adds AI-powered meeting minutes generation to the existing TMG Board system. The codebase is a FastAPI + SQLAlchemy backend with a Next.js 16 / React 19 / Tailwind CSS 4 frontend. Both layers are well-structured and follow consistent patterns.

The backend needs two new SQLAlchemy models (`DocumentTemplate` and `MeetingMinutes`), a new `document_generator.py` service following the `StorageService` singleton pattern, a new API router (`generation.py`) mounted under `/api/meetings/{id}/minutes`, and an Alembic migration `005_add_document_templates_and_meeting_minutes.py`. The Anthropic Python package and Jinja2 need to be added to `requirements.txt`.

The frontend needs: (1) the "Recording" Card in the meeting detail sidebar replaced with a "Meeting Minutes" Card containing a "Create Meeting Minutes" button that opens a transcript-paste modal, (2) a markdown renderer (`react-markdown`) to display the generated minutes inline, (3) print CSS for printable minutes, and (4) a new "Templates" tab in the admin settings page. No new routes are needed — everything fits into existing pages.

**Primary recommendation:** Build in this order: migration → models → service → API router → frontend meeting detail → admin template UI. This allows incremental testing at each layer.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | `>=0.40.0` | Anthropic SDK with AsyncAnthropic client | Locked decision; official SDK for claude-3-5-sonnet |
| `jinja2` | Transitive via FastAPI | Prompt template rendering with meeting context | Locked decision; already available |
| `sqlalchemy` | `>=2.0.25` | ORM for new models | Already in use; existing mapped_column pattern |
| `alembic` | `>=1.13.1` | Database migration for new tables | Already in use; 004 is the latest revision |

### Supporting (Frontend)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `react-markdown` | `^9.0.0` | Render generated markdown inline | Minutes display in meeting detail page |
| `@tailwindcss/typography` | `^0.5.0` | Prose styling for markdown content | Required for `prose` class to style rendered markdown |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `react-markdown` | `marked` + `dangerouslySetInnerHTML` | react-markdown is safer (no XSS); avoid dangerouslySetInnerHTML |
| `react-markdown` | `remark-react` | react-markdown is simpler API, more widely maintained |
| AsyncAnthropic streaming | Non-streaming | Streaming adds UX complexity; non-streaming is simpler and sufficient for minutes length |

**Installation:**

Backend:
```bash
pip install anthropic>=0.40.0
# jinja2 already installed transitively
```

Frontend:
```bash
npm install react-markdown @tailwindcss/typography
```

---

## Architecture Patterns

### Recommended Project Structure Changes
```
backend/app/
├── models/
│   ├── generation.py        # DocumentTemplate + MeetingMinutes models (NEW)
├── services/
│   ├── document_generator.py # AI generation service singleton (NEW)
├── api/
│   ├── generation.py        # /meetings/{id}/minutes + /admin/templates endpoints (NEW)

frontend/src/
├── components/
│   ├── generate-minutes-modal.tsx  # Transcript textarea + Generate button (NEW)
├── app/
│   ├── meetings/[id]/page.tsx      # MODIFY: replace Recording section
│   ├── admin/settings/page.tsx     # MODIFY: add Templates tab
```

### Pattern 1: SQLAlchemy Model — Follow Existing Mapped Column Style

**What:** New models use the same `Mapped[type] = mapped_column(...)` style as all existing models.
**When to use:** For both `DocumentTemplate` and `MeetingMinutes`.

```python
# Source: Codebase — app/models/meeting.py (verified)
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "meeting_minutes"
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MeetingMinutes(Base):
    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(Integer, ForeignKey("meetings.id"), nullable=False, unique=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)  # full markdown stored in DB
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # optional StorageService backup
    generated_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("document_templates.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship("Meeting")
    generated_by: Mapped["BoardMember"] = relationship("BoardMember")
    template: Mapped[Optional["DocumentTemplate"]] = relationship("DocumentTemplate")
```

**Storage decision:** Store `content_markdown` directly in the DB column (Text) rather than exclusively via StorageService. This avoids an extra async file read on every page load. StorageService backup is optional/future.

### Pattern 2: Service Singleton — Follow StorageService Pattern

**What:** Module-level singleton instance, initialized once at import time.
**When to use:** For `document_generator.py`.

```python
# Source: Codebase — app/services/storage.py (verified)
from anthropic import AsyncAnthropic
from jinja2 import Environment, BaseLoader
from app.config import get_settings

settings = get_settings()

class DocumentGeneratorService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.jinja_env = Environment(loader=BaseLoader())

    async def generate_meeting_minutes(
        self,
        transcript: str,
        meeting_context: dict,
        system_prompt: str,
        user_prompt_template: str,
    ) -> str:
        """Render Jinja2 template then call Anthropic API. Returns markdown string."""
        template = self.jinja_env.from_string(user_prompt_template)
        rendered_prompt = template.render(**meeting_context, transcript=transcript)

        message = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": rendered_prompt}
            ],
            system=system_prompt,
        )
        return message.content[0].text

# Singleton
document_generator = DocumentGeneratorService()
```

### Pattern 3: API Router — Follow meetings.py Style

**What:** Inline Pydantic schemas + FastAPI router with dependency injection.
**When to use:** New `api/generation.py` router.

```python
# Source: Codebase — app/api/meetings.py (verified)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.api.auth import require_chair, require_admin
from app.models.generation import DocumentTemplate, MeetingMinutes
from app.models.meeting import Meeting, AgendaItem, MeetingAttendance
from app.services.document_generator import document_generator

router = APIRouter()

class GenerateMinutesRequest(BaseModel):
    transcript: str

class MinutesResponse(BaseModel):
    id: int
    meeting_id: int
    content_markdown: str
    created_at: str
    generated_by_id: int

@router.post("/meetings/{meeting_id}/minutes")
async def generate_minutes(
    meeting_id: int,
    request: GenerateMinutesRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_chair)
):
    """Generate meeting minutes from transcript (Chair/Admin only)."""
    ...

@router.get("/meetings/{meeting_id}/minutes")
async def get_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_member)
):
    """Get generated minutes for a meeting."""
    ...
```

Register in `main.py`:
```python
from app.api import generation
app.include_router(generation.router, prefix="/api", tags=["generation"])
```

### Pattern 4: Alembic Migration — Follow 004 Style

**What:** Sequential revision with string IDs, explicit upgrade/downgrade.
**When to use:** Migration `005_add_document_templates_and_meeting_minutes.py`.

```python
# Source: Codebase — migrations/versions/004_add_timezone_support.py (verified)
revision = '005_add_document_templates_and_meeting_minutes'
down_revision = '004_add_timezone_support'

def upgrade() -> None:
    op.create_table('document_templates', ...)
    op.create_table('meeting_minutes', ...)
    # Seed default meeting_minutes template
    ...

def downgrade() -> None:
    op.drop_table('meeting_minutes')
    op.drop_table('document_templates')
```

### Pattern 5: Frontend Modal — Follow Existing Modal Component Style

**What:** Standalone modal component with backdrop, Card container, loading state.
**When to use:** `generate-minutes-modal.tsx`.

```typescript
// Source: Codebase — components/create-meeting-modal.tsx (pattern)
"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, FileText } from "lucide-react";

interface GenerateMinutesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (minutes: string) => void;
  meetingId: string;
}

export function GenerateMinutesModal({ isOpen, onClose, onSuccess, meetingId }: GenerateMinutesModalProps) {
  const [transcript, setTranscript] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={() => !generating && onClose()} />
      <Card className="relative z-10 w-full max-w-2xl mx-4 shadow-lg">
        <CardHeader>
          <CardTitle>Generate Meeting Minutes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">Paste the meeting transcript below.</p>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste transcript here..."
            rows={12}
            className="w-full px-3 py-2 rounded-md border bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            disabled={generating}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose} disabled={generating}>Cancel</Button>
            <Button onClick={handleGenerate} disabled={generating || !transcript.trim()}>
              {generating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileText className="h-4 w-4 mr-2" />}
              {generating ? "Generating..." : "Generate Minutes"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Pattern 6: Markdown Rendering Inline

**What:** Use `react-markdown` with Tailwind Typography `prose` class for inline display.
**When to use:** Displaying generated minutes in the meeting detail page.

```typescript
// Install: npm install react-markdown @tailwindcss/typography
import ReactMarkdown from "react-markdown";

// In meeting detail page, inside the Minutes Card:
<div className="prose prose-sm prose-invert max-w-none">
  <ReactMarkdown>{minutes.content_markdown}</ReactMarkdown>
</div>
```

### Pattern 7: Print CSS

**What:** `@media print` CSS to hide navigation and show only the minutes content.
**When to use:** Add to `globals.css` or inline on the component.

```css
/* In globals.css */
@media print {
  .no-print { display: none !important; }
  .print-only { display: block !important; }
}
```

Trigger print:
```typescript
<Button variant="outline" onClick={() => window.print()}>
  <Printer className="h-4 w-4 mr-2" />
  Print Minutes
</Button>
```

### Pattern 8: Admin Tab Extension

**What:** Add a "Templates" tab to the existing admin settings page tab navigation array.
**When to use:** M-5 admin template UI.

```typescript
// Source: Codebase — app/admin/settings/page.tsx lines 191-195 (verified)
// Existing pattern:
type SettingsTab = "general" | "permissions" | "audit";
const tabs = [
  { id: "general" as const, label: "General", icon: Building },
  { id: "permissions" as const, label: "Permissions", icon: Shield, adminOnly: true },
  { id: "audit" as const, label: "Audit Log", icon: History },
];

// Extend to:
type SettingsTab = "general" | "permissions" | "audit" | "templates";
// Add: { id: "templates" as const, label: "Templates", icon: FileText, adminOnly: true }
```

### Anti-Patterns to Avoid

- **Do not store minutes only in StorageService files:** Reading a file on every page load is slow. Store `content_markdown` as a Text column in `meeting_minutes` table directly.
- **Do not use a synchronous Anthropic client in async FastAPI handlers:** Always use `AsyncAnthropic`, not `Anthropic`.
- **Do not put Jinja2 template rendering outside the service:** Keep all AI logic in `document_generator.py`.
- **Do not use `dangerouslySetInnerHTML` to render markdown:** Use `react-markdown` to avoid XSS.
- **Do not hardcode the model string:** Define `ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"` as a constant or config value.
- **Do not block regeneration:** Allow re-generating minutes for the same meeting by upserting the `meeting_minutes` row (update if exists, insert if not).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom regex HTML converter | `react-markdown` | Handles all commonmark edge cases; XSS-safe |
| Markdown styling | Custom CSS for h1/h2/p/ul | `@tailwindcss/typography` + `prose` class | Handles nested elements, list nesting, code blocks |
| Jinja2 template rendering | Python `.format()` or f-strings | `jinja2.Environment.from_string()` | Supports loops, conditionals, filters for complex templates |
| Async HTTP to Anthropic | Raw `httpx` calls | `anthropic.AsyncAnthropic` | Handles auth, retries, error types, response parsing |

**Key insight:** The Anthropic SDK and Jinja2 handle the two most complex parts of this feature. The rest is plumbing — SQLAlchemy models and Next.js UI components — which the project already knows how to build.

---

## Common Pitfalls

### Pitfall 1: Missing `anthropic` in requirements.txt
**What goes wrong:** `ImportError: No module named 'anthropic'` at runtime or build.
**Why it happens:** The package must be explicitly added; it is not a transitive dependency.
**How to avoid:** Add `anthropic>=0.40.0` to `requirements.txt` before writing any service code.
**Warning signs:** Import error on backend startup.

### Pitfall 2: Using Synchronous `Anthropic` Client in Async FastAPI Handler
**What goes wrong:** Thread-blocking call inside async handler degrades performance under load; may also cause warnings.
**Why it happens:** Forgetting to use `AsyncAnthropic`.
**How to avoid:** Always `from anthropic import AsyncAnthropic` and `await client.messages.create(...)`.
**Warning signs:** No `await` before the `.create()` call.

### Pitfall 3: Anthropic API Key Not in Settings
**What goes wrong:** `AuthenticationError` from the Anthropic SDK at generation time.
**Why it happens:** New env var `ANTHROPIC_API_KEY` is not added to `config.py Settings` class.
**How to avoid:** Add `anthropic_api_key: str = ""` to `Settings` in `config.py` and set it in `.env`.
**Warning signs:** Service initializes but every call raises 401.

### Pitfall 4: Migration Not Registered Correctly
**What goes wrong:** `alembic upgrade head` skips the new migration or fails with "can't locate revision".
**Why it happens:** `down_revision` must exactly match `'004_add_timezone_support'` (the current head).
**How to avoid:** Verify `down_revision` string matches the exact revision ID of the previous migration file.
**Warning signs:** `alembic history` doesn't show the new revision.

### Pitfall 5: Jinja2 `UndefinedError` at Generation Time
**What goes wrong:** Template renders with `UndefinedError` if meeting context dict is missing expected keys.
**Why it happens:** Template variables like `{{ meeting.title }}` require the context dict to supply them.
**How to avoid:** Build the context dict from the full meeting + agenda + attendance data before rendering. Validate template at save time (try rendering with a dummy context).
**Warning signs:** 500 error during generation with `jinja2.exceptions.UndefinedError` in traceback.

### Pitfall 6: `react-markdown` Not Installed / Tailwind Typography Not Configured
**What goes wrong:** Markdown renders as raw text, or unstyled.
**Why it happens:** Forgetting to install or configure the packages.
**How to avoid:** `npm install react-markdown @tailwindcss/typography`, add `typography` plugin to Tailwind config.
**Warning signs:** Raw asterisks and hashes visible in the minutes display.

### Pitfall 7: Print CSS Hiding Minutes Content
**What goes wrong:** `@media print` CSS rule accidentally hides the minutes content along with the nav.
**Why it happens:** Overly broad `.no-print` selectors applied to parent containers.
**How to avoid:** Wrap minutes content in a dedicated `div.print-content` that is never given the `.no-print` class.
**Warning signs:** Blank page when printing.

---

## Code Examples

Verified patterns from the codebase:

### Meeting Context Builder (Backend)

Assemble the full meeting context dict from DB objects before Jinja2 rendering:

```python
# Build context from SQLAlchemy objects in the API handler
def build_meeting_context(meeting: Meeting, attendance: list, agenda: list) -> dict:
    return {
        "meeting": {
            "title": meeting.title,
            "date": meeting.scheduled_date.strftime("%B %d, %Y"),
            "location": meeting.location or "Virtual",
            "duration_minutes": meeting.duration_minutes,
        },
        "attendees": [
            {"name": a.member.name, "status": a.status}
            for a in attendance if a.status == "present"
        ],
        "agenda_items": [
            {
                "order": item.order_index + 1,
                "title": item.title,
                "type": item.item_type,
                "presenter": item.presenter.name if item.presenter else None,
                "description": item.description,
            }
            for item in agenda
        ],
    }
```

### Default Meeting Minutes Prompt Template (Jinja2)

Seed this in the migration as the default `DocumentTemplate`:

```
System prompt:
You are a professional board secretary generating formal meeting minutes.
Output clean, well-structured markdown suitable for a board of directors.
Be concise and factual. Use the transcript to extract discussions, decisions, and action items.

User prompt template:
# Meeting Minutes Request

**Meeting:** {{ meeting.title }}
**Date:** {{ meeting.date }}
**Location:** {{ meeting.location }}

## Attendees
{% for attendee in attendees %}
- {{ attendee.name }}
{% endfor %}

## Agenda
{% for item in agenda_items %}
{{ item.order }}. {{ item.title }} ({{ item.type }}){% if item.presenter %} — Presented by {{ item.presenter }}{% endif %}
{% endfor %}

## Transcript
{{ transcript }}

---

Please generate formal meeting minutes from the above transcript following this structure:
1. Meeting called to order / opening
2. Attendance / quorum
3. Agenda items covered (one section per agenda item)
4. Decisions made
5. Action items with responsible parties
6. Adjournment
```

### Frontend API Call Pattern

Follow the existing `api.post<T>` pattern:

```typescript
// In lib/api.ts — add to existing file
export const generationApi = {
  generateMinutes: (meetingId: string, transcript: string) =>
    api.post<{ id: number; content_markdown: string; created_at: string }>(
      `/meetings/${meetingId}/minutes`,
      { transcript }
    ),

  getMinutes: (meetingId: string) =>
    api.get<{ id: number; content_markdown: string; created_at: string } | null>(
      `/meetings/${meetingId}/minutes`
    ),
};
```

### Meeting Detail Page — Recording Card Replacement

The existing "Recording" Card is at lines 830-849 in `frontend/src/app/meetings/[id]/page.tsx`:

```typescript
// REPLACE this existing block:
{/* Recording */}
<Card>
  <CardHeader>
    <CardTitle className="text-base">Recording</CardTitle>
  </CardHeader>
  <CardContent>
    {meeting.recording ? ( ... ) : (
      <p>Recording will be available after the meeting</p>
    )}
  </CardContent>
</Card>

// WITH:
{/* Meeting Minutes */}
<Card>
  <CardHeader className="flex flex-row items-center justify-between">
    <CardTitle className="text-base">Meeting Minutes</CardTitle>
    {isChairOrAdmin && (
      <Button variant="outline" size="sm" onClick={() => setShowMinutesModal(true)}>
        <FileText className="h-4 w-4 mr-2" />
        {minutes ? "Regenerate" : "Create Minutes"}
      </Button>
    )}
  </CardHeader>
  <CardContent>
    {minutes ? (
      <>
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown>{minutes.content_markdown}</ReactMarkdown>
        </div>
        <Button variant="ghost" size="sm" className="mt-4 w-full" onClick={() => window.print()}>
          <Printer className="h-4 w-4 mr-2" />
          Print Minutes
        </Button>
      </>
    ) : (
      <p className="text-sm text-muted-foreground text-center py-2">
        No minutes generated yet.
      </p>
    )}
  </CardContent>
</Card>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Anthropic` sync client | `AsyncAnthropic` async client | Anthropic SDK v0.20+ | Non-blocking LLM calls in FastAPI async handlers |
| f-string prompt construction | Jinja2 template rendering | Locked decision | Admin-editable prompts stored in DB |
| Minutes as file-only | Minutes as DB Text column | Recommendation | Fast retrieval without file I/O on every page load |

**Deprecated/outdated:**
- `anthropic.Anthropic().messages.create()` — synchronous, blocks event loop. Use `AsyncAnthropic` in FastAPI.

---

## Open Questions

1. **Streaming vs. non-streaming for generation**
   - What we know: Claude's Discretion. Streaming provides better UX for long minutes (shows progress). Non-streaming is simpler.
   - What's unclear: Expected transcript length and resulting minutes length.
   - Recommendation: Start with non-streaming (simpler). If minutes generation takes >15 seconds in testing, add streaming with SSE.

2. **Minutes inline vs. full-page view**
   - What we know: Minutes displayed inline in the sidebar Card (locked decision).
   - What's unclear: Minutes can be very long (multiple pages). Sidebar may become very tall.
   - Recommendation: Add a `max-h-96 overflow-y-auto` scroll container for the inline view, with the full content visible on print.

3. **Regeneration behavior**
   - What we know: Claude's Discretion — allow re-generating. CONTEXT.md says allow it.
   - Recommendation: Upsert `meeting_minutes` row (UPDATE if exists, INSERT if not). Keep only one set of minutes per meeting (no version history — that's deferred).

4. **Jinja2 template validation in admin UI**
   - What we know: Admin edits system_prompt and user_prompt_template as raw text.
   - What's unclear: Should bad templates fail silently or with an error?
   - Recommendation: On save, render the template with a dummy context and return a validation error if it fails. Display the error in the admin UI.

---

## Validation Architecture

No `config.json` found — `workflow.nyquist_validation` is absent, so treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (standard FastAPI testing) |
| Config file | None detected — Wave 0 gap |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| M-1 | DocumentGeneratorService generates markdown from transcript + context | unit | `pytest tests/test_document_generator.py -x` | Wave 0 |
| M-1 | Jinja2 template renders meeting context correctly | unit | `pytest tests/test_document_generator.py::test_template_rendering -x` | Wave 0 |
| M-2 | DocumentTemplate model can be created and retrieved | unit | `pytest tests/test_models.py::test_document_template -x` | Wave 0 |
| M-2 | MeetingMinutes model links to meeting correctly | unit | `pytest tests/test_models.py::test_meeting_minutes -x` | Wave 0 |
| M-3 | POST /api/meetings/{id}/minutes requires chair/admin auth | integration | `pytest tests/test_generation_api.py::test_generate_requires_auth -x` | Wave 0 |
| M-3 | POST /api/meetings/{id}/minutes returns 200 with markdown | integration | `pytest tests/test_generation_api.py::test_generate_minutes -x` | Wave 0 |
| M-4 | GET /api/meetings/{id}/minutes returns stored markdown | integration | `pytest tests/test_generation_api.py::test_get_minutes -x` | Wave 0 |
| M-5 | GET /api/admin/templates requires admin auth | integration | `pytest tests/test_generation_api.py::test_templates_require_admin -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_document_generator.py` — covers M-1 service unit tests (mock Anthropic API)
- [ ] `backend/tests/test_generation_api.py` — covers M-3, M-4, M-5 API integration tests
- [ ] `backend/tests/test_models.py` — covers M-2 model tests (or extend existing test file if present)
- [ ] `backend/tests/conftest.py` — shared fixtures (test DB session, mock Anthropic client)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` — if not present in requirements-dev.txt

---

## Sources

### Primary (HIGH confidence)
- Codebase `backend/app/services/storage.py` — singleton service pattern
- Codebase `backend/app/models/meeting.py` — SQLAlchemy mapped_column pattern
- Codebase `backend/app/api/meetings.py` — inline Pydantic schema + router pattern
- Codebase `backend/app/api/admin.py` — require_admin RBAC pattern
- Codebase `backend/app/api/auth.py` — auth dependencies (require_chair, require_admin, require_member)
- Codebase `backend/app/config.py` — Settings pattern for env vars
- Codebase `backend/migrations/versions/004_add_timezone_support.py` — Alembic migration pattern
- Codebase `frontend/src/app/meetings/[id]/page.tsx` — Recording Card target (lines 830-849), modal pattern
- Codebase `frontend/src/app/admin/settings/page.tsx` — admin tab pattern
- Codebase `frontend/package.json` — confirmed React 19, Next.js 16.1.4, Tailwind CSS 4

### Secondary (MEDIUM confidence)
- `anthropic` Python SDK documentation — AsyncAnthropic usage pattern (consistent with SDK v0.40+)
- `react-markdown` v9 — compatible with React 19
- `@tailwindcss/typography` — compatible with Tailwind CSS v4

### Tertiary (LOW confidence)
- Streaming SSE approach for generation progress — not verified against this specific Next.js/FastAPI setup

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified against codebase, locked decisions confirmed
- Architecture: HIGH — directly mirrors existing codebase patterns
- Pitfalls: HIGH — derived from actual code inspection, not speculation
- Test infrastructure: MEDIUM — no existing test files found; test commands inferred from standard FastAPI/pytest convention

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable libraries; Anthropic SDK may release new versions)
