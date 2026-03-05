---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Agentic Layer & Board Enhancements
status: in_progress
stopped_at: Completed 03-03-PLAN.md (Phase 03 complete)
last_updated: "2026-03-05T02:12:40Z"
last_activity: 2026-03-05 — Completed 03-03 (Frontend transcript section, minutes generator, recording card removal)
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# Project State — TMG Board

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.0 Phase 03 complete, ready for Phase 04

## Current Position

Phase: 03 of 05 (Transcripts & Minutes Generator) -- COMPLETE
Plan: 3 of 3 in current phase (all complete)
Status: Phase Complete
Last activity: 2026-03-05 — Completed 03-03 (Frontend transcript section, minutes generator, recording card removal)

Progress: [██████████] 100%

## Tech Stack
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI (>=0.135.0 needed), SQLAlchemy 2.0, PostgreSQL
- **Auth:** Google OAuth via NextAuth, email whitelist, role-based (admin/chair/board/shareholder)
- **Theme:** Dark theme with gold accents (`var(--gold)`)
- **Deployment:** Railway

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 4min
- Total execution time: 38min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | 19min | 5min |
| 02 | 3 | 10min | 3min |
| 03 | 3 | 9min | 3min |

## Accumulated Context

### Key Decisions
- **Multi-model via LiteLLM** — unified API for Anthropic, Gemini, Groq
- **Custom lightweight agent loop** — ~100 lines, no LangChain/CrewAI
- **Tools call board REST API** — preserves auth, validation, audit logging
- **Starlette StreamingResponse for SSE** — Python 3.9 can't use FastAPI >=0.135.0, manual SSE format identical
- **Digital signatures are lightweight** — name + timestamp + IP, not DocuSign
- **Remove recording_url** — replace with transcript paste/upload (Phase 03)
- **Agents are embedded** — inline on existing pages, not a standalone chat UI

### Key Decisions (01-01)
- **Extracted _seed_agents()** — standalone function for testability outside lifespan
- **JSON column for allowed_tool_names** — simpler than junction table for small tool lists
- **Created backend .venv** — required for isolated test execution

### Key Decisions (01-02)
- **Hybrid streaming strategy** — non-streaming for tool iterations, single text_delta for final response
- **Tools call board REST API via httpx** — X-User-Email header for auth context forwarding
- **Tool auto-registration on import** — register_tool() at module level, import at bottom of __init__.py
- **Python 3.9 compat** — `from __future__ import annotations` for union type syntax

### Key Decisions (01-03)
- **StreamingResponse for SSE** — Python 3.9 prevents FastAPI >=0.135.0; Starlette StreamingResponse with manual SSE format is wire-compatible
- **Route path '' not '/'** — matches redirect_slashes=False convention
- **Usage logging inside async generator** — after all events yielded, captures accurate token/duration data

### Key Decisions (01-04)
- **react-markdown for agent output** — prose-invert dark theme styling for markdown rendering
- **Buffer-based SSE parsing** — robust chunked event handling in useAgentStream hook
- **userEmail as prop, not useSession** — decouples hook from NextAuth; parent passes email
- **onToolComplete callback** — fires after tool_result events for page data refresh

### Key Decisions (02-01)
- **Soft-delete via is_active boolean** — simpler than deleted_at for template configuration data
- **Batch meeting creation as /with-agenda** — separate route from POST / to avoid overloading
- **_seed_templates standalone function** — matches _seed_agents pattern for testability

### Key Decisions (02-02)
- **Single-turn agent prompt** — Meeting Setup agent parses what it can and reports missing fields, no follow-up question loop
- **Seed data upgrade block** — _seed_agents() detects placeholder prompt and auto-updates existing agents
- **Replaced list_members with list_meetings** — list_members was never a registered tool; corrected to list_meetings

### Key Decisions (03-03)
- **useAgentStream directly in MinutesGenerator** — AgentResponsePanel embeds its own text input; MinutesGenerator needs one-click generate, not a chat interface
- **Inline feedback instead of toast library** — auto-dismissing messages match existing patterns without adding dependencies

### Key Decisions (02-03)
- **Full-page creation replaces modal** — modal too constrained for three creation modes (AI, template, manual) plus inline agenda editing
- **AI-assisted section expanded by default** — primary recommended flow; collapse for manual/template
- **ClipboardList icon for Templates sidebar** — differentiates from Documents (FileText)
- **Regulatory items: Shield icon + amber border** — visual language for governance/compliance items

### Key Files
- `frontend/src/components/sidebar.tsx` — Left navigation
- `frontend/src/lib/api.ts` — API client
- `backend/app/api/` — All API routes
- `backend/app/models/` — All SQLAlchemy models
- `backend/app/models/agent.py` — AgentConfig and AgentUsageLog models
- `backend/app/schemas/agent.py` — Agent Pydantic schemas
- `backend/tests/conftest.py` — Shared test fixtures
- `backend/app/services/agent_runner.py` — Core agent loop (run_agent, run_agent_streaming)
- `backend/app/services/llm_provider.py` — LiteLLM wrapper
- `backend/app/tools/__init__.py` — Tool registry
- `backend/app/tools/meetings.py` — Meeting tools (create_agenda_item, get_meeting, list_meetings, create_meeting_with_agenda)
- `backend/app/models/decision.py` — Decisions (has resolution type, used in Phase 04)
- `backend/app/models/meeting.py` — Meetings (recording_url removed in Phase 03)
- `frontend/src/components/transcript-section.tsx` — Transcript paste/upload/view component
- `frontend/src/components/minutes-generator.tsx` — Minutes generator with inline agent invocation
- `backend/app/api/transcripts.py` — Transcript CRUD endpoints (nested under meetings router)
- `backend/app/tools/transcripts.py` — Minutes Generator agent tools
- `backend/app/api/agents.py` — Agent API: list, detail, SSE run endpoint
- `backend/tests/test_agent_api.py` — 10 integration tests for agent API
- `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` — Agentic layer research (HIGH confidence)
- `frontend/src/lib/agent-types.ts` — AgentEvent, ToolCallEvent, AgentStreamState types
- `frontend/src/hooks/use-agent-stream.ts` — SSE consumption hook with run/cancel/reset API
- `frontend/src/components/agent-response-panel.tsx` — Collapsible inline agent panel
- `frontend/src/components/tool-call-indicator.tsx` — Tool call status indicator
- `backend/app/models/template.py` — MeetingTemplate and TemplateAgendaItem models
- `backend/app/api/templates.py` — Template CRUD API (list, get, create, update, delete)
- `backend/migrations/versions/005_add_meeting_templates.py` — Template tables migration
- `frontend/src/app/meetings/create/page.tsx` — Full-page meeting creation (AI, templates, manual)
- `frontend/src/app/admin/templates/page.tsx` — Admin template CRUD management

### Blockers
None

## Session Continuity

Last session: 2026-03-05T02:12:40Z
Stopped at: Completed 03-03-PLAN.md (Phase 03 complete)
Resume file: None
