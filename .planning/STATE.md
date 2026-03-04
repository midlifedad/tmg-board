# Project State — TMG Board

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.0 Phase 01 — Agent Infrastructure & Streaming UX

## Current Position

Phase: 01 of 05 (Agent Infrastructure & Streaming UX)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-04 — Roadmap created, ready to begin Phase 01 planning

Progress: [░░░░░░░░░░] 0%

## Tech Stack
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI (>=0.135.0 needed), SQLAlchemy 2.0, PostgreSQL
- **Auth:** Google OAuth via NextAuth, email whitelist, role-based (admin/chair/board/shareholder)
- **Theme:** Dark theme with gold accents (`var(--gold)`)
- **Deployment:** Railway

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

## Accumulated Context

### Key Decisions
- **Multi-model via LiteLLM** — unified API for Anthropic, Gemini, Groq
- **Custom lightweight agent loop** — ~100 lines, no LangChain/CrewAI
- **Tools call board REST API** — preserves auth, validation, audit logging
- **FastAPI native SSE** (v0.135+) — no sse-starlette dependency
- **Digital signatures are lightweight** — name + timestamp + IP, not DocuSign
- **Remove recording_url** — replace with transcript paste/upload (Phase 03)
- **Agents are embedded** — inline on existing pages, not a standalone chat UI

### Key Files
- `frontend/src/components/sidebar.tsx` — Left navigation
- `frontend/src/lib/api.ts` — API client
- `backend/app/api/` — All API routes
- `backend/app/models/` — All SQLAlchemy models
- `backend/app/models/decision.py` — Decisions (has resolution type, used in Phase 04)
- `backend/app/models/meeting.py` — Meetings (has recording_url to remove in Phase 03)
- `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` — Agentic layer research (HIGH confidence)

### Blockers
None

## Session Continuity

Last session: 2026-03-04
Stopped at: Roadmap created — next step is `/gsd:plan-phase 01`
Resume file: None
