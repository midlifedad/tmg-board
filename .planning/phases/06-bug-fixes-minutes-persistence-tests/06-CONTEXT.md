# Phase 06: Bug Fixes, Minutes Persistence & Test Coverage — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning
**Source:** Comprehensive code review of PR #52 (v2.0 Agentic Layer)

<domain>
## Phase Boundary

This phase fixes critical bugs discovered during code review, adds the missing minutes persistence endpoint so generated minutes survive page refresh, adds print CSS for meeting minutes, and closes the most critical test coverage gaps.

</domain>

<decisions>
## Implementation Decisions

### Bug Fixes (from review)
- Fix route conflict: `GET /api/agents/api-keys` shadowed by `GET /api/agents/{slug}` — reorder routes so static paths come before parameterized
- Fix XSS: `dangerouslySetInnerHTML` in `resolutions/[id]/page.tsx` — replace with ReactMarkdown or DOMPurify
- Fix auth leak: `isChairOrAdmin` includes `|| !session` in meetings/decisions pages — remove the `|| !session` fallback
- Fix `create_minutes_document` tool: calls non-existent `POST /api/meetings/{id}/minutes` — create the endpoint

### Minutes Persistence
- Add `POST /api/meetings/{meeting_id}/minutes` endpoint that creates a Document (type="minutes") and links via MeetingDocument junction table
- Add `GET /api/meetings/{meeting_id}/minutes` endpoint that retrieves the latest minutes document
- Frontend: load existing minutes on meeting detail page, display as rendered HTML/markdown
- This follows staging's existing pattern of storing minutes as Documents, not a separate model

### Print CSS
- Add `@media print` styles for meeting minutes content
- Add `.prose-minutes` class for markdown/HTML rendering in dark theme
- Add print button to meeting detail page when minutes exist
- Hide nav/sidebar in print view

### Test Coverage
- Focus on highest-impact gaps: meetings CRUD (14 untested endpoints), auth deps, tool handlers
- Fix test environment (install missing deps in venv)
- Target: bring coverage from ~35% to ~60%+

### Architecture Alignment
- Work within staging's existing patterns: LiteLLM, agent streaming, tool loopback
- Do NOT introduce Anthropic SDK directly or Jinja2 template system (staging uses LiteLLM + hardcoded prompts)
- Admin prompt editing is already available via the agent admin page (Phase 05)

</decisions>

<specifics>
## Specific Details

### Route Conflict Fix
The `agents.py` file defines routes in this order:
1. `GET /api/agents` (list)
2. `GET /api/agents/{slug}` (detail by slug)
3. `POST /api/agents/run` (run agent)
4. `GET /api/agents/api-keys` (admin)
5. `PUT /api/agents/api-keys` (admin)

Routes 4-5 are shadowed by route 2. Fix: move api-keys routes before the {slug} route.

### Minutes Persistence Endpoint
The `create_minutes_document` tool in `tools/transcripts.py` already calls:
- `POST /api/meetings/{meeting_id}/minutes` with `{"html_content": "...", "title": "..."}`
It expects a response with `document_id`. The tool has a graceful fallback for 404, but the endpoint should exist.

### XSS in Resolution Detail
Lines 174 and 246 of `resolutions/[id]/page.tsx` use `dangerouslySetInnerHTML={{ __html: resolution.description }}`. Since resolution descriptions may be AI-generated, this is an XSS vector. Replace with ReactMarkdown (already installed).

</specifics>

<deferred>
## Deferred

- Admin-configurable AI prompt templates (DocumentTemplate model) — staging's agent admin already allows editing system prompts
- Full integration tests (end-to-end flows)
- Rate limiting on agent endpoints
- API key encryption at rest
- Agent streaming timeout in proxy
- Resolution export to PDF
</deferred>
