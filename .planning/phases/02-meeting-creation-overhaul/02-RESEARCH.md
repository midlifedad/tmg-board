# Phase 02: Meeting Creation Overhaul & Meeting Setup Agent - Research

**Researched:** 2026-03-04
**Domain:** Meeting creation UX, meeting template schema, agent-assisted text parsing, embedded agent UX
**Confidence:** HIGH

## Summary

Phase 02 transforms the existing modal-based meeting creation flow into a full-page experience with two creation paths: (1) paste a meeting description into an expandable section and let the Meeting Setup agent parse it into a structured meeting with agenda items, and (2) fill in meeting details manually with an improved UX. Additionally, admins can create reusable meeting templates with standard agenda items (including regulatory-flagged items), and any user can apply a template when creating a meeting.

The current codebase has a `CreateMeetingModal` (287 lines) that creates meetings with title, date, time, duration, location type, and description -- but no agenda items at creation time. Agenda items are added after creation on the meeting detail page via `AgendaItemManager`. The overhaul needs to: (a) replace the modal with a full page, (b) allow agenda items to be added during creation (not just after), (c) add the paste-to-populate agent integration, and (d) add template selection and management. This phase depends on Phase 01 (agent infrastructure) being complete -- it uses the agent loop, SSE streaming, and embedded agent UX patterns built there.

**Primary recommendation:** Build a new `/meetings/create` page (not a modal) with two tabs or sections: "Manual" and "AI-Assisted". Add `MeetingTemplate` and `TemplateAgendaItem` SQLAlchemy models with an Alembic migration. Create the Meeting Setup agent as a database-seeded `AgentConfig` row with a tool that calls the existing meetings/agenda REST API. The agent's system prompt instructs it to parse unstructured text into structured agenda items.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEET-01 | User can create a meeting by selecting a date and pasting a full description that the agent parses into structured agenda | Paste-to-populate UX pattern (expandable section), Meeting Setup agent with system prompt + `create_meeting_with_agenda` tool, SSE streaming from Phase 01 |
| MEET-02 | User can alternatively fill in meeting details manually (improved UX) | New full-page `/meetings/create` with inline agenda builder (instead of modal-only creation then separate agenda management) |
| MEET-03 | Admin can create meeting templates with standard agenda items | `MeetingTemplate` + `TemplateAgendaItem` models, admin CRUD API endpoints, admin UI under Admin section |
| MEET-04 | User can apply a template when creating a meeting, then customize | Template selector dropdown on create page, API endpoint to fetch template with items, pre-populate agenda from template |
| MEET-05 | Meeting templates can include required regulatory items (manual configuration for now) | `is_regulatory` boolean flag on `TemplateAgendaItem`, visual indicator in UI, cannot be deleted when applied (only modified) |
| UX-01 | Meeting creation page has an expandable section where user can paste a description for agent-assisted setup | Collapsible section with textarea, "Parse with AI" button, SSE streaming response display, progressive population of form fields |
| BUILT-01 | Meeting Setup agent can parse a pasted description into structured meeting with agenda items | AgentConfig row seeded in DB, system prompt for parsing, tools: `create_meeting_with_agenda`, `add_agenda_item`. Agent uses LiteLLM via Phase 01 infrastructure. |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 | API endpoints for templates CRUD, agent invocation | Already the backend framework. Phase 01 upgrades to 0.135+ for SSE. |
| SQLAlchemy 2.0 | >=2.0.25 | Meeting template models, relationships | Already the ORM. Mapped column pattern established in all existing models. |
| Alembic | >=1.13.1 | Database migration for new template tables | Already configured at `backend/alembic.ini` with migrations in `backend/migrations/versions/`. |
| Pydantic | >=2.5 | Request/response schemas for template API | Already used for all API schemas (inline in route files). |
| Next.js 15 | - | New meeting creation page | Already the frontend framework. |
| shadcn/ui | - | UI components (Card, Button, collapsible sections) | Already used throughout the app. |
| LiteLLM | >=1.80 | Meeting Setup agent LLM calls | Added in Phase 01. |

### Supporting (No New Dependencies)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | - | Icons (Sparkles for AI, FileTemplate for templates) | Already installed. Use for new UI elements. |
| httpx | >=0.26.0 | Agent tool internal API calls | Already in requirements.txt. Agent tools call board API via httpx. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full page for meeting creation | Enhanced modal | Modal is too small for agenda items + template selector + AI section. Full page gives room for all three sections without scrolling inside a popup. |
| Database-seeded agent config | Hardcoded agent in code | Phase 05 adds admin agent management -- seeding in DB now means it's already editable via the admin UI when Phase 05 ships. |
| `is_regulatory` boolean on template items | Separate regulatory items table | Boolean flag is simpler and sufficient for "manual configuration for now" (MEET-05). A separate table would be overengineering for the current requirement. |

**Installation:**
```bash
# No new dependencies needed. Phase 01 adds litellm.
# Phase 02 uses only existing project dependencies.
```

## Architecture Patterns

### Backend: New Files and Modifications

```
backend/app/
├── api/
│   ├── meetings.py              # MODIFY: Add template_id to CreateMeetingRequest, batch agenda creation
│   └── templates.py             # NEW: Meeting template CRUD (admin only) + list (all users)
├── models/
│   ├── meeting.py               # MODIFY: Add template_id FK to Meeting (optional)
│   └── template.py              # NEW: MeetingTemplate, TemplateAgendaItem models
├── tools/
│   └── meetings.py              # NEW (or MODIFY if created in Phase 01): Meeting Setup agent tools
└── migrations/
    └── versions/
        └── 005_add_meeting_templates.py  # NEW: Migration for template tables + meeting.template_id
```

### Frontend: New Files and Modifications

```
frontend/src/
├── app/
│   ├── meetings/
│   │   ├── create/
│   │   │   └── page.tsx         # NEW: Full-page meeting creation (replaces modal for creation)
│   │   ├── page.tsx             # MODIFY: Link "New Meeting" button to /meetings/create instead of opening modal
│   │   └── [id]/page.tsx        # No changes needed
│   └── admin/
│       └── templates/
│           └── page.tsx         # NEW: Admin template management page
├── components/
│   ├── create-meeting-modal.tsx # KEEP for now (deprecate later), or remove if page replaces it entirely
│   ├── template-selector.tsx    # NEW: Dropdown to pick a template when creating a meeting
│   ├── agenda-builder.tsx       # NEW: Inline agenda item editor for meeting creation (add/remove/reorder before save)
│   └── agent-paste-section.tsx  # NEW: Expandable AI-assisted section with textarea + streaming output
└── lib/
    └── api.ts                   # MODIFY: Add templatesApi, update meetingsApi.create for agenda items
```

### Pattern 1: MeetingTemplate + TemplateAgendaItem Models
**What:** Two new SQLAlchemy models that store reusable meeting templates. A template has a name, description, and a list of template agenda items. Each item has the same fields as `AgendaItem` (title, description, item_type, duration_minutes, order_index) plus an `is_regulatory` boolean flag.
**When to use:** Template CRUD (admin), template application (all users creating meetings).
**Example:**
```python
# backend/app/models/template.py
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MeetingTemplate(Base):
    """Reusable meeting template with standard agenda items."""

    __tablename__ = "meeting_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    default_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    created_by: Mapped["BoardMember"] = relationship("BoardMember")
    items: Mapped[List["TemplateAgendaItem"]] = relationship(
        "TemplateAgendaItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateAgendaItem.order_index",
    )

    def __repr__(self) -> str:
        return f"<MeetingTemplate {self.name}>"


class TemplateAgendaItem(Base):
    """Agenda item within a meeting template."""

    __tablename__ = "template_agenda_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_templates.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[str] = mapped_column(
        String(30), default="information", nullable=False
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_regulatory: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    template: Mapped["MeetingTemplate"] = relationship(
        "MeetingTemplate", back_populates="items"
    )

    def __repr__(self) -> str:
        return f"<TemplateAgendaItem {self.order_index}. {self.title}>"


from app.models.member import BoardMember
```

### Pattern 2: Meeting Creation with Inline Agenda Items
**What:** The existing `CreateMeetingRequest` only creates a meeting shell. The new flow needs to create a meeting AND its agenda items in a single API call. Add a `CreateMeetingWithAgendaRequest` that accepts an optional list of agenda items and an optional `template_id`.
**When to use:** Both manual creation (user builds agenda inline) and agent-assisted creation (agent populates via tool call).
**Example:**
```python
# Addition to backend/app/api/meetings.py

class AgendaItemInput(BaseModel):
    title: str
    description: Optional[str] = None
    item_type: str = "information"
    duration_minutes: Optional[int] = None
    presenter_id: Optional[int] = None
    is_regulatory: bool = False  # Carried from template


class CreateMeetingWithAgendaRequest(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: datetime
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    template_id: Optional[int] = None
    agenda_items: Optional[List[AgendaItemInput]] = None


@router.post("/with-agenda")
async def create_meeting_with_agenda(
    request: CreateMeetingWithAgendaRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Create a meeting with agenda items in a single operation."""
    meeting = Meeting(
        title=request.title,
        description=request.description,
        scheduled_date=request.scheduled_date,
        duration_minutes=request.duration_minutes,
        location=request.location,
        meeting_link=request.meeting_link,
        status="scheduled",
        created_by_id=current_user.id,
    )
    db.add(meeting)
    db.flush()  # Get meeting.id

    if request.agenda_items:
        for idx, item_data in enumerate(request.agenda_items):
            item = AgendaItem(
                meeting_id=meeting.id,
                title=item_data.title,
                description=item_data.description,
                item_type=item_data.item_type,
                duration_minutes=item_data.duration_minutes,
                presenter_id=item_data.presenter_id,
                order_index=idx,
            )
            db.add(item)

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=meeting.id,
        entity_name=request.title,
        action="create",
        changed_by_id=current_user.id,
    ))

    db.commit()
    db.refresh(meeting)
    return meeting
```

### Pattern 3: Paste-to-Populate Agent Flow
**What:** The Meeting Setup agent receives unstructured text (a pasted meeting description) and uses its system prompt + tools to create a structured meeting. The flow is: user pastes text -> frontend calls agent endpoint -> agent streams response via SSE -> agent calls `create_meeting_with_agenda` tool -> frontend shows the created meeting and allows editing.
**When to use:** MEET-01, UX-01, BUILT-01.
**Example:**
```python
# Meeting Setup Agent - System Prompt (seeded in agent_configs table)
MEETING_SETUP_SYSTEM_PROMPT = """You are the Meeting Setup Agent for a board governance platform.

Your job is to parse a pasted meeting description into a structured meeting with agenda items.

When given a meeting description, extract:
1. Meeting title
2. Date and time (if mentioned)
3. Location or virtual meeting link (if mentioned)
4. Duration (if mentioned, otherwise estimate from agenda)
5. Individual agenda items with:
   - Title
   - Description (if details provided)
   - Type: "information", "discussion", "decision_required", or "consent_agenda"
   - Estimated duration in minutes
   - Order (sequence as listed)

Rules:
- If the description mentions a vote, resolution, or approval, classify that item as "decision_required"
- If items are listed for review without discussion, classify as "consent_agenda"
- Default item type is "information" unless context suggests otherwise
- Estimate durations based on item complexity (5 min for simple items, 10-15 for discussions, 15-30 for decisions)
- Always call the create_meeting_with_agenda tool with the parsed data
- If information is ambiguous, make reasonable assumptions and note them in your response
- Respond with a brief summary of what you created after the tool call completes
"""
```

### Pattern 4: Expandable AI Section UX (Frontend)
**What:** A collapsible section on the meeting creation page where users can paste a description. When they click "Parse with AI", the section expands to show streaming agent output and the form fields populate progressively.
**When to use:** UX-01.
**Example:**
```typescript
// frontend/src/components/agent-paste-section.tsx
// Uses the SSE streaming pattern from Phase 01

interface AgentPasteSectionProps {
  onMeetingParsed: (data: ParsedMeetingData) => void;
}

interface ParsedMeetingData {
  title?: string;
  scheduled_date?: string;
  duration_minutes?: number;
  location?: string;
  meeting_link?: string;
  description?: string;
  agenda_items?: Array<{
    title: string;
    description?: string;
    item_type: string;
    duration_minutes?: number;
  }>;
}

// The component has three states:
// 1. Collapsed (default) - shows "Paste a description for AI-assisted setup" with expand button
// 2. Expanded (input) - shows textarea for pasting + "Parse with AI" button
// 3. Processing (streaming) - shows agent output streaming in, form fields populate as tools execute
```

### Anti-Patterns to Avoid
- **Keeping meeting creation as a modal:** The modal is too small for agenda items + template selector + AI section. A full page is needed.
- **Creating meeting then separately adding agenda items:** The current flow requires creating a meeting first, then navigating to the detail page to add agenda items. The new flow should create everything in one operation.
- **Hardcoding the agent prompt in Python code:** The prompt must be in the `agent_configs` database table so admins can edit it later (Phase 05).
- **Agent directly inserting into database:** The agent must call the board REST API tools (which enforce auth and audit logging), not access the database directly.
- **Separate API call per agenda item from the agent:** The agent should use a single `create_meeting_with_agenda` tool that creates the meeting and all items atomically, not N+1 separate calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing unstructured text into structured agenda | Regex-based text parser | LLM agent (Meeting Setup) via LiteLLM | Meeting descriptions are free-form natural language. No regex will handle the variety of formats (bullet points, numbered lists, prose, tables). LLMs excel at this. |
| SSE streaming for agent responses | Custom streaming logic | Phase 01 infrastructure (`EventSourceResponse`, `runAgent` frontend helper) | Phase 01 builds the entire SSE pipeline. This phase just uses it. |
| Collapsible/expandable UI sections | Custom CSS toggle logic | shadcn/ui `Collapsible` component or simple state toggle with existing Card/Button | The project already uses shadcn/ui for all UI components. |
| Drag-to-reorder agenda items in creation form | Custom drag-and-drop from scratch | Existing `AgendaItemManager` patterns (ChevronUp/ChevronDown reorder buttons) | The existing codebase uses simple up/down buttons for reordering, not drag-and-drop. Keep consistent. |

**Key insight:** The hardest part of this phase is NOT the template CRUD (straightforward) or the UX (standard patterns). The hard part is the agent's system prompt engineering -- getting the LLM to reliably parse varied meeting description formats into the correct structured output with appropriate `item_type` classifications. This requires iteration and testing, not complex code.

## Common Pitfalls

### Pitfall 1: Agent Creates Meeting but Frontend Doesn't Know the ID
**What goes wrong:** The agent calls `create_meeting_with_agenda` via a tool, which creates the meeting in the database. But the frontend doesn't know the new meeting's ID to redirect to the detail page.
**Why it happens:** Tool results flow back through the SSE stream as `tool_result` events. If the frontend doesn't parse the tool result to extract the meeting ID, the user is stuck.
**How to avoid:** The `create_meeting_with_agenda` tool must return the created meeting object (including its ID) in the tool result. The frontend SSE handler must watch for `tool_result` events with `name: "create_meeting_with_agenda"` and extract the meeting ID for navigation.
**Warning signs:** User sees "Meeting created successfully" but has no link to the meeting.

### Pitfall 2: Template Regulatory Items Accidentally Deletable
**What goes wrong:** User applies a template with regulatory items, then deletes the regulatory items from the agenda before creating the meeting.
**Why it happens:** The UI treats all agenda items the same during editing.
**How to avoid:** When agenda items are populated from a template, carry the `is_regulatory` flag. In the UI, show regulatory items with a visual indicator (e.g., a shield icon and gold/amber border). Allow editing the content but not deletion. Or show a confirmation warning: "This is a required regulatory item. Are you sure you want to remove it?"
**Warning signs:** Meetings created from templates missing required regulatory items.

### Pitfall 3: Agent Parses Date/Time Incorrectly
**What goes wrong:** The agent extracts "next Tuesday at 2pm" and converts it to the wrong date or wrong timezone.
**Why it happens:** Natural language date parsing is ambiguous. The LLM doesn't know the user's timezone or current date unless told.
**How to avoid:** Include the current date and user's timezone in the system prompt context. Example: "Today's date is 2026-03-04. The user's timezone is America/Los_Angeles." If the agent can't determine a date, it should leave the date field for the user to fill manually and mention this in its response.
**Warning signs:** Meetings created with dates in the past or wrong timezone.

### Pitfall 4: Migration Fails Due to Missing Model Import
**What goes wrong:** The Alembic migration for `meeting_templates` and `template_agenda_items` doesn't detect the new models.
**Why it happens:** Alembic's `autogenerate` only detects models imported into `Base.metadata`. If the new model file isn't imported in `models/__init__.py`, it's invisible.
**How to avoid:** Add `from app.models.template import MeetingTemplate, TemplateAgendaItem` to `backend/app/models/__init__.py` before running `alembic revision --autogenerate`.
**Warning signs:** `alembic revision --autogenerate` produces an empty migration.

### Pitfall 5: CreateMeetingRequest Date Alias Confusion
**What goes wrong:** The existing `CreateMeetingRequest` uses `Field(..., alias="date")` for `scheduled_date`, accepting both `date` and `scheduled_date` from the frontend. The new `CreateMeetingWithAgendaRequest` might not include this alias, breaking frontend compatibility.
**Why it happens:** The alias was added for frontend convenience. New schemas need to maintain the same convention.
**How to avoid:** Use the same `scheduled_date` field with `alias="date"` and `populate_by_name = True` in the new request schema, matching the existing pattern.
**Warning signs:** 422 Unprocessable Entity errors when creating meetings from the new form.

## Code Examples

### Template CRUD API Endpoints
```python
# backend/app/api/templates.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.template import MeetingTemplate, TemplateAgendaItem
from app.api.auth import require_admin, require_member

router = APIRouter()


class TemplateAgendaItemInput(BaseModel):
    title: str
    description: Optional[str] = None
    item_type: str = "information"
    duration_minutes: Optional[int] = None
    order_index: int = 0
    is_regulatory: bool = False


class CreateTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    default_duration_minutes: Optional[int] = None
    default_location: Optional[str] = None
    items: List[TemplateAgendaItemInput] = []


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_duration_minutes: Optional[int] = None
    default_location: Optional[str] = None
    items: Optional[List[TemplateAgendaItemInput]] = None


@router.get("")
async def list_templates(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """List all active meeting templates (any board member can view)."""
    templates = (
        db.query(MeetingTemplate)
        .filter(MeetingTemplate.is_active.is_(True))
        .order_by(MeetingTemplate.name)
        .all()
    )
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "default_duration_minutes": t.default_duration_minutes,
            "default_location": t.default_location,
            "items_count": len(t.items),
            "has_regulatory_items": any(i.is_regulatory for i in t.items),
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get template with all agenda items."""
    template = db.query(MeetingTemplate).filter(
        MeetingTemplate.id == template_id,
        MeetingTemplate.is_active.is_(True),
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template  # SQLAlchemy will serialize items via relationship


@router.post("")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Create a meeting template (admin only)."""
    template = MeetingTemplate(
        name=request.name,
        description=request.description,
        default_duration_minutes=request.default_duration_minutes,
        default_location=request.default_location,
        created_by_id=current_user.id,
    )
    db.add(template)
    db.flush()

    for idx, item_data in enumerate(request.items):
        item = TemplateAgendaItem(
            template_id=template.id,
            title=item_data.title,
            description=item_data.description,
            item_type=item_data.item_type,
            duration_minutes=item_data.duration_minutes,
            order_index=idx,
            is_regulatory=item_data.is_regulatory,
        )
        db.add(item)

    db.commit()
    db.refresh(template)
    return template
```

### Meeting Setup Agent Tool Definition
```python
# backend/app/tools/meetings.py
# Tool definition for the Meeting Setup agent

MEETING_SETUP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_meeting_with_agenda",
            "description": "Create a new board meeting with agenda items in a single operation. "
                          "Use this after parsing a meeting description to create the structured meeting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the meeting (e.g., 'Q1 2026 Board Meeting')",
                    },
                    "scheduled_date": {
                        "type": "string",
                        "description": "ISO 8601 datetime (e.g., '2026-04-15T10:00:00')",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Total meeting duration in minutes",
                    },
                    "location": {
                        "type": "string",
                        "description": "Physical location or 'Virtual' if online",
                    },
                    "meeting_link": {
                        "type": "string",
                        "description": "URL for virtual meeting (Zoom, Meet, etc.)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Meeting description or notes",
                    },
                    "agenda_items": {
                        "type": "array",
                        "description": "List of agenda items in order",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "item_type": {
                                    "type": "string",
                                    "enum": [
                                        "information",
                                        "discussion",
                                        "decision_required",
                                        "consent_agenda",
                                    ],
                                },
                                "duration_minutes": {"type": "integer"},
                            },
                            "required": ["title"],
                        },
                    },
                },
                "required": ["title", "agenda_items"],
            },
        },
    },
]
```

### Frontend: Template Selector Component
```typescript
// frontend/src/components/template-selector.tsx
"use client";

import { useState, useEffect } from "react";
import { FileText, ChevronDown, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { templatesApi, type MeetingTemplate } from "@/lib/api";

interface TemplateSelectorProps {
  onTemplateSelect: (template: MeetingTemplate | null) => void;
  selectedTemplateId: number | null;
}

// When a template is selected:
// 1. Fetch full template with items from API
// 2. Pre-populate the agenda builder with template items
// 3. Show regulatory items with Shield icon
// 4. User can modify items but gets a warning when removing regulatory ones
```

### Frontend API Additions
```typescript
// Additions to frontend/src/lib/api.ts

export interface MeetingTemplate {
  id: number;
  name: string;
  description?: string | null;
  default_duration_minutes?: number | null;
  default_location?: string | null;
  items_count: number;
  has_regulatory_items: boolean;
  created_at: string;
}

export interface TemplateDetail extends MeetingTemplate {
  items: Array<{
    id: number;
    title: string;
    description?: string | null;
    item_type: string;
    duration_minutes?: number | null;
    order_index: number;
    is_regulatory: boolean;
  }>;
}

export const templatesApi = {
  list: async (): Promise<MeetingTemplate[]> => {
    return api.get<MeetingTemplate[]>("/templates");
  },
  get: async (id: number): Promise<TemplateDetail> => {
    return api.get(`/templates/${id}`);
  },
  create: async (data: CreateTemplateRequest): Promise<TemplateDetail> => {
    return api.post("/templates", data);
  },
  update: async (id: number, data: UpdateTemplateRequest): Promise<TemplateDetail> => {
    return api.patch(`/templates/${id}`, data);
  },
  delete: async (id: number): Promise<void> => {
    return api.delete(`/templates/${id}`);
  },
};
```

## Specific Files to Modify and Create

### Files to CREATE (new)

| File | Purpose |
|------|---------|
| `backend/app/models/template.py` | MeetingTemplate + TemplateAgendaItem SQLAlchemy models |
| `backend/app/api/templates.py` | Template CRUD endpoints (admin create/update/delete, member list/get) |
| `backend/migrations/versions/005_add_meeting_templates.py` | Alembic migration for new tables |
| `frontend/src/app/meetings/create/page.tsx` | Full-page meeting creation with manual + AI-assisted modes |
| `frontend/src/app/admin/templates/page.tsx` | Admin template management page |
| `frontend/src/components/template-selector.tsx` | Template dropdown for meeting creation |
| `frontend/src/components/agenda-builder.tsx` | Inline agenda item editor for creation form |
| `frontend/src/components/agent-paste-section.tsx` | Expandable AI-assisted paste section |

### Files to MODIFY (existing)

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Add imports for `MeetingTemplate`, `TemplateAgendaItem` |
| `backend/app/main.py` | Register templates router: `app.include_router(templates.router, prefix="/api/templates")` |
| `backend/app/api/meetings.py` | Add `POST /meetings/with-agenda` endpoint for batch creation |
| `frontend/src/app/meetings/page.tsx` | Change "New Meeting" button to navigate to `/meetings/create` instead of opening modal |
| `frontend/src/lib/api.ts` | Add `templatesApi` object, update `meetingsApi` with `createWithAgenda` method |
| `frontend/src/components/sidebar.tsx` | Add "Templates" link under Admin section (if admin) |

### Files to KEEP (no changes)

| File | Reason |
|------|--------|
| `frontend/src/components/create-meeting-modal.tsx` | Keep as fallback or remove. The new full page replaces its purpose. |
| `frontend/src/components/agenda-item-manager.tsx` | Used on the meeting detail page for post-creation editing. No changes needed. |
| `frontend/src/components/edit-meeting-modal.tsx` | Editing existing meetings -- unaffected by creation overhaul. |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Modal-only meeting creation | Full-page creation with multiple input modes | This phase | More room for agenda items, template selection, AI section |
| Create meeting, then add agenda items on detail page | Batch creation (meeting + agenda in one API call) | This phase | Better UX, atomic creation, agent-compatible |
| Manual agenda typing only | AI-assisted agenda parsing from pasted descriptions | This phase | Dramatically faster meeting setup for users who copy from email/docs |
| No meeting templates | Reusable templates with regulatory item flags | This phase | Standardized governance meetings, regulatory compliance |

## Open Questions

1. **Should the AI-assisted flow create the meeting immediately or just populate the form?**
   - What we know: The agent has a `create_meeting_with_agenda` tool that creates the meeting in the database. But the user might want to review and edit before saving.
   - What's unclear: Does "agent parses into structured agenda" mean the agent creates it directly, or populates the form for user review?
   - Recommendation: **Populate the form, don't create immediately.** The agent should return the parsed data as structured output. The frontend populates the form fields and agenda builder. The user reviews, edits, and clicks "Create Meeting" to save. This gives users control and avoids creating meetings with mistakes. The agent's tool should be `parse_meeting_description` (returns structured data) rather than `create_meeting_with_agenda` (creates in DB). However, the requirements say "agent parses into structured agenda" which leans toward populate-then-confirm. The planner should decide which approach to take.

2. **Template management: separate admin page or integrated into settings?**
   - What we know: Admin already has `/admin/settings` and `/admin/users` pages. Templates are an admin function.
   - What's unclear: New page at `/admin/templates` or a section within the existing settings page?
   - Recommendation: **New page at `/admin/templates`.** Templates have enough complexity (CRUD + agenda items per template + regulatory flags) to warrant their own page. Add a sidebar link under the Admin section.

3. **How should the Meeting Setup agent handle missing information?**
   - What we know: A pasted description might not include a date, time, or location.
   - What's unclear: Should the agent ask follow-up questions, make assumptions, or leave fields blank?
   - Recommendation: **Leave missing fields blank and note them.** The agent should populate what it can extract and tell the user which fields need manual completion. Do not enter a follow-up question loop -- these agents are designed as single-turn (Phase 01 decision).

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `backend/app/models/meeting.py`, `backend/app/api/meetings.py`, `frontend/src/components/create-meeting-modal.tsx` -- full read of current meeting creation flow
- Phase 01 research: `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` -- agent loop, SSE streaming, tool calling patterns, LiteLLM integration
- SQLAlchemy 2.0 mapped column pattern -- verified from all existing models in `backend/app/models/`
- Alembic migration pattern -- verified from `backend/migrations/versions/` (4 existing migrations)
- FastAPI router registration pattern -- verified from `backend/app/main.py`
- Frontend API client pattern -- verified from `frontend/src/lib/api.ts` (meetingsApi, adminApi)
- Auth dependency pattern -- verified from `backend/app/api/auth.py` (require_admin, require_chair, require_member)

### Secondary (MEDIUM confidence)
- AgendaItem fields and types -- verified from both backend model and frontend TypeScript interface. Types are: `information`, `discussion`, `decision_required`, `consent_agenda`
- Meeting creation auth: `require_chair` -- meaning board, chair, and admin roles can create meetings. Template creation uses `require_admin` (admin only).

### Tertiary (LOW confidence)
- shadcn/ui Collapsible component availability -- assumed based on the project using shadcn/ui. May need to add via `npx shadcn-ui@latest add collapsible` if not already installed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies. Uses only what Phase 01 adds (LiteLLM) and existing project libraries.
- Architecture: HIGH - Models, API endpoints, and frontend patterns directly follow established codebase conventions (verified from reading all existing models and API files).
- Template schema: HIGH - Simple two-table design mirrors the existing Meeting/AgendaItem relationship.
- Agent integration: HIGH - Uses Phase 01 agent infrastructure (agent loop, SSE, tools). The Meeting Setup agent is the first concrete agent built on that infrastructure.
- Pitfalls: HIGH - All pitfalls identified from reading the existing codebase and understanding the interaction between agent tool calls and frontend state.
- Open questions: MEDIUM - The populate-vs-create question for the agent flow needs a decision from the planner.

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days - existing codebase patterns are stable, no external dependency changes)
