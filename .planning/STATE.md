---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Agentic Layer & Board Enhancements
status: executing
stopped_at: Completed 01-02-PLAN.md
last_updated: "2026-03-04T20:52:36.247Z"
last_activity: 2026-03-04 — Completed 01-02 (Agent runner service, tool registry, meeting tools)
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 4
  completed_plans: 2
  percent: 50
---

# Project State — TMG Board

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.0 Phase 01 — Agent Infrastructure & Streaming UX

## Current Position

Phase: 01 of 05 (Agent Infrastructure & Streaming UX)
Plan: 2 of 4 in current phase
Status: Executing
Last activity: 2026-03-04 — Completed 01-02 (Agent runner service, tool registry, meeting tools)

Progress: [█████░░░░░] 50%

## Tech Stack
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI (>=0.135.0 needed), SQLAlchemy 2.0, PostgreSQL
- **Auth:** Google OAuth via NextAuth, email whitelist, role-based (admin/chair/board/shareholder)
- **Theme:** Dark theme with gold accents (`var(--gold)`)
- **Deployment:** Railway

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 5.5min
- Total execution time: 11min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | 11min | 5.5min |

## Accumulated Context

### Key Decisions
- **Multi-model via LiteLLM** — unified API for Anthropic, Gemini, Groq
- **Custom lightweight agent loop** — ~100 lines, no LangChain/CrewAI
- **Tools call board REST API** — preserves auth, validation, audit logging
- **FastAPI native SSE** (v0.135+) — no sse-starlette dependency
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
- `backend/app/tools/meetings.py` — Meeting tools (create_agenda_item, get_meeting, list_meetings)
- `backend/app/models/decision.py` — Decisions (has resolution type, used in Phase 04)
- `backend/app/models/meeting.py` — Meetings (has recording_url to remove in Phase 03)
- `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` — Agentic layer research (HIGH confidence)

### Blockers
None

## Session Continuity

Last session: 2026-03-04T20:52:36.245Z
Stopped at: Completed 01-02-PLAN.md
Resume file: None
