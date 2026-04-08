---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Stability & Quality
status: complete
stopped_at: Completed 07-02-PLAN.md
last_updated: "2026-04-08T19:25:01Z"
last_activity: 2026-04-08 — Executed Phase 07 Plan 02 (API key UI, models.ts, provider-aware dropdowns, DOMPurify XSS fix)
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State — TMG Board

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-04)

**Core value:** Board members can efficiently conduct governance and leverage AI assistants to automate repetitive board tasks
**Current focus:** v2.1 — Agent configuration UI, provider management, bug fixes

## Current Position

Phase: 07 of 07 (Agent Configuration & Provider Management) — COMPLETE
Plan: 2 of 2 in current phase (all done)
Status: Complete
Last activity: 2026-04-08 — Executed Plan 07-02

Progress: [==========] 100%

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

### Phase 07 Plan 02 Decisions
- **DOMPurify over ReactMarkdown for minutes HTML** — minutes are HTML not markdown, DOMPurify strips XSS while preserving formatting
- **Dynamic model fetch on modal open** — models fetched from available-models endpoint each time to reflect current provider key status
- **Stale model warning in edit modal** — if agent's current model not in available list, show warning but still allow selection

### Key Files
- `backend/app/services/llm_provider.py` — Provider key map, sync_api_keys, SUPPORTED_MODELS
- `backend/app/api/agents.py` — API key endpoints, available-models endpoint, agent run
- `backend/app/api/meetings.py` — has_minutes via MeetingDocument query
- `frontend/src/lib/models.ts` — Single source of truth for SUPPORTED_MODELS and getModelLabel
- `frontend/src/app/admin/agents/page.tsx` — Admin agents page with API key management section
- `frontend/src/components/create-agent-modal.tsx` — Dynamic provider-aware model dropdown
- `frontend/src/components/edit-agent-modal.tsx` — Dynamic provider-aware model dropdown with stale warning
- `frontend/src/app/meetings/[id]/page.tsx` — DOMPurify-sanitized minutes rendering
- `frontend/src/lib/api.ts` — API client with getApiKeys, updateApiKey, getAvailableModels

### Blockers
None

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 06 | 01 | 7min | 3 | 9 |
| 06 | 02 | 5min | 4 | 7 |
| 07 | 01 | 2min | 2 | 3 |
| 07 | 02 | 3min | 2 | 7 |

## Session Continuity

Last session: 2026-04-08T19:25:01Z
Stopped at: Completed 07-02-PLAN.md (v2.1 milestone complete)
Resume file: None
