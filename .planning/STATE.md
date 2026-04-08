---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Stability & Quality
status: in_progress
stopped_at: Completed 07-01-PLAN.md
last_updated: "2026-04-08T19:19:00Z"
last_activity: 2026-04-08 — Executed Phase 07 Plan 01 (Gemini removal, SUPPORTED_MODELS, has_minutes fix)
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 4
  completed_plans: 3
  percent: 75
---

# Project State — TMG Board

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.1 — Agent configuration UI, provider management, bug fixes

## Current Position

Phase: 07 of 07 (Agent Configuration & Provider Management) — IN PROGRESS
Plan: 1 of 2 in current phase
Status: Executing
Last activity: 2026-04-08 — Executed Plan 07-01

Progress: [=======---] 75%

## Tech Stack
- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI (>=0.135.0 needed), SQLAlchemy 2.0, PostgreSQL
- **Auth:** Google OAuth via NextAuth, email whitelist, role-based (admin/chair/board/shareholder)
- **AI:** LiteLLM (multi-provider), custom agent loop, SSE streaming
- **Theme:** Dark theme with gold accents (`var(--gold)`)
- **Deployment:** Railway

## Key Decisions

### Phase 06 Decisions
- **Work within staging's architecture** — LiteLLM agents, tool loopback, SSE streaming (NOT direct Anthropic SDK)
- **Minutes stored as Documents** — via MeetingDocument junction table with relationship_type="minutes"
- **ReactMarkdown for safe rendering** — replaces dangerouslySetInnerHTML
- **Test focus on highest-impact gaps** — meetings CRUD, minutes, auth, agent API keys

### Phase 07 Decisions
- **API key UI on Admin Agents page** — section, not separate page
- **Remove Gemini provider** — only Anthropic and Groq supported
- **Consolidate model list** — single shared file, provider-aware dropdown
- **DOMPurify for minutes HTML** — not ReactMarkdown (minutes are HTML, not markdown)
- **Fix has_minutes with actual DB query** — not hardcoded to completed status

### Phase 07 Plan 01 Decisions
- **SUPPORTED_MODELS as list-of-dicts** — value/label/provider keys for direct JSON serialization
- **available-models endpoint open to all members** — not admin-only, since agent modals need it
- **Set pre-query for minutes_meeting_ids** — single query before loop, O(1) lookups

### Key Files
- `backend/app/services/llm_provider.py` — Provider key map, sync_api_keys
- `backend/app/api/agents.py` — API key endpoints, agent run
- `backend/app/api/meetings.py` — has_minutes bug (line 158)
- `frontend/src/app/admin/agents/page.tsx` — Admin agents page (MODEL_LABELS hardcoded)
- `frontend/src/components/create-agent-modal.tsx` — SUPPORTED_MODELS hardcoded
- `frontend/src/components/edit-agent-modal.tsx` — SUPPORTED_MODELS hardcoded
- `frontend/src/app/meetings/[id]/page.tsx` — Minutes XSS (dangerouslySetInnerHTML)

### Blockers
None

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 06 | 01 | 7min | 3 | 9 |
| 06 | 02 | 5min | 4 | 7 |
| 07 | 01 | 2min | 2 | 3 |

## Session Continuity

Last session: 2026-04-08T19:19:00Z
Stopped at: Completed 07-01-PLAN.md
Resume file: None
