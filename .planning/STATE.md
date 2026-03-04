# Project State — TMG Board

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-04 — Milestone v2.0 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.0 Agentic Layer & Board Enhancements

## Tech Stack
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Auth:** Google OAuth via NextAuth, email whitelist, role-based (admin/chair/board/shareholder)
- **Theme:** Dark theme with gold accents (`var(--gold)`)
- **Deployment:** Railway

## Accumulated Context

### Key Decisions
- **Multi-model via LiteLLM** — unified API for Anthropic, Gemini, Groq
- **Custom lightweight agent loop** — no heavy frameworks
- **Tools call board REST API** — preserves auth, validation, audit logging
- **FastAPI native SSE** (v0.135+) — no sse-starlette dependency
- **Digital signatures are lightweight** — name + timestamp + IP, not DocuSign
- **Remove recording_url** — replace with transcript paste/upload

### Key Files
- `frontend/src/components/sidebar.tsx` — Left navigation
- `frontend/src/lib/api.ts` — API client
- `backend/app/api/` — All API routes
- `backend/app/models/` — All SQLAlchemy models
- `backend/app/models/decision.py` — Decisions (has resolution type)
- `backend/app/models/meeting.py` — Meetings (has recording_url to remove)
- `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` — Agentic layer research

### Blockers
(none)
