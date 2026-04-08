# Phase 1: Meeting Minutes Generation - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning
**Source:** Direct stakeholder discussion

<domain>
## Phase Boundary

This phase delivers the ability for chairs/admins to generate AI-powered meeting minutes from a pasted transcript within an existing meeting's detail page. The generated minutes are stored as markdown, viewable inline, and printable.

</domain>

<decisions>
## Implementation Decisions

### AI Framework
- Use Anthropic SDK (`anthropic` Python package) directly — no LangChain, LiteLLM, or other framework
- Use Jinja2 for prompt templates (already a transitive dependency of FastAPI)
- Templates stored in database as plain text strings
- AsyncAnthropic client for non-blocking LLM calls in FastAPI async handlers

### Backend Architecture
- New `DocumentTemplate` SQLAlchemy model for admin-configurable prompt templates
- New `MeetingMinutes` model to link generated minutes to meetings (or extend existing Document model with meeting_id FK)
- New service: `app/services/document_generator.py` following existing singleton pattern (like StorageService)
- New API router for generation endpoints
- Anthropic API key stored as environment variable in config.py Settings
- Generated markdown stored via existing StorageService (local or S3)

### Frontend — Meeting Detail Page
- Replace "Recording" section (which says "Recording will be available after the meeting") with "Meeting Minutes" section
- "Create Meeting Minutes" button opens a modal
- Modal has: textarea for pasting transcript, "Generate Minutes" button
- Generation is async — show loading state while LLM processes
- Generated minutes displayed inline within the meeting detail page (similar to agenda display)
- Minutes should be printable (print-friendly CSS)

### Admin Section
- Template management UI under existing admin section
- Follow existing RBAC — admin role required
- Ability to view and edit prompt templates for different document types
- Starting with "meeting_minutes" template type

### Minutes Format
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

</decisions>

<specifics>
## Specific Ideas

- The "Recording" text in the meeting detail sidebar should become "Meeting Minutes"
- The modal should be simple: just a large textarea to paste transcript + a generate button
- Minutes should be stored as a markdown file but rendered inline (not as a downloadable document initially)
- Admin template editor should be a simple form with a textarea for the system prompt and user prompt templates
- Use Jinja2 template syntax in stored prompts: `{{ meeting.title }}`, `{% for item in agenda_items %}`, etc.
- The prompt should receive full meeting context: title, date, attendees, agenda items with types and presenters

</specifics>

<deferred>
## Deferred Ideas

- DocuSign signing of generated minutes (future phase)
- PDF export of minutes (future)
- Auto-transcription from recording URL (future)
- Multiple document type generation beyond minutes (future — but architecture supports it)
- Version history for regenerated minutes (future)

</deferred>

---

*Phase: 01-meeting-minutes-generation*
*Context gathered: 2026-04-07 via stakeholder discussion*
