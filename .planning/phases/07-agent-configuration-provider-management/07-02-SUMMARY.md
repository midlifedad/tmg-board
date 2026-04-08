---
phase: 07-agent-configuration-provider-management
plan: 02
subsystem: ui
tags: [react, next.js, dompurify, admin-ui, api-keys, provider-management]

# Dependency graph
requires:
  - phase: 07-agent-configuration-provider-management
    provides: "SUPPORTED_MODELS constant, available-models endpoint, API key endpoints"
provides:
  - "API key management UI on Admin Agents page"
  - "Shared models.ts with SUPPORTED_MODELS and getModelLabel"
  - "Provider-aware model dropdowns in create/edit agent modals"
  - "DOMPurify-sanitized minutes rendering (XSS fix)"
affects: []

# Tech tracking
tech-stack:
  added: [dompurify, "@types/dompurify"]
  patterns: ["Provider-aware dynamic model dropdowns via available-models API", "DOMPurify sanitization for user-generated HTML"]

key-files:
  created:
    - frontend/src/lib/models.ts
  modified:
    - frontend/src/app/admin/agents/page.tsx
    - frontend/src/components/create-agent-modal.tsx
    - frontend/src/components/edit-agent-modal.tsx
    - frontend/src/app/meetings/[id]/page.tsx
    - frontend/src/lib/api.ts
    - frontend/package.json

key-decisions:
  - "DOMPurify over ReactMarkdown for minutes HTML — minutes are HTML not markdown, DOMPurify strips XSS while preserving formatting"
  - "Dynamic model fetch on modal open — models fetched from available-models endpoint each time modal opens to reflect current provider key status"
  - "Stale model warning in edit modal — if agent's current model is not in available list, show warning but still allow selection"

patterns-established:
  - "Single source of truth for model definitions in frontend/src/lib/models.ts"
  - "Provider-aware UI pattern: fetch available models from API, show warning when no providers configured"

requirements-completed: [AGCFG-01, AGCFG-02, AGCFG-03, AGCFG-04, AGCFG-06]

# Metrics
duration: 3min
completed: 2026-04-08
---

# Phase 07 Plan 02: Frontend Provider UI Summary

**API key management cards on Admin Agents page, consolidated models.ts, dynamic provider-aware model dropdowns, and DOMPurify XSS fix for meeting minutes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-08T19:21:19Z
- **Completed:** 2026-04-08T19:25:01Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Admin Agents page now has an "LLM API Keys" section with cards for Anthropic and Groq showing configured/not configured status, masked key preview, and save functionality
- Model definitions consolidated into single shared `frontend/src/lib/models.ts` (4 models, zero Gemini)
- Create and edit agent modals fetch models dynamically from `/api/agents/available-models` — only models for configured providers appear
- Meeting minutes HTML sanitized with DOMPurify, eliminating the dangerouslySetInnerHTML XSS vector

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shared models.ts, add API client functions, and install DOMPurify** - `0233dc9` (feat)
2. **Task 2: API key management UI, provider-aware dropdowns, and minutes XSS fix** - `b626c13` (feat)

## Files Created/Modified
- `frontend/src/lib/models.ts` - Single source of truth for SUPPORTED_MODELS (4 models) and getModelLabel function
- `frontend/src/lib/api.ts` - Added adminApi.getApiKeys, adminApi.updateApiKey, adminApi.getAvailableModels
- `frontend/package.json` - Added dompurify and @types/dompurify dependencies
- `frontend/src/app/admin/agents/page.tsx` - Removed hardcoded MODEL_LABELS, added API key management section with provider cards
- `frontend/src/components/create-agent-modal.tsx` - Replaced static SUPPORTED_MODELS with dynamic fetch from available-models endpoint
- `frontend/src/components/edit-agent-modal.tsx` - Replaced static SUPPORTED_MODELS with dynamic fetch, added stale model warning
- `frontend/src/app/meetings/[id]/page.tsx` - Replaced raw dangerouslySetInnerHTML with DOMPurify.sanitize

## Decisions Made
- Used DOMPurify instead of ReactMarkdown because minutes content is HTML (not markdown) — DOMPurify strips script tags, event handlers, and other XSS vectors while preserving safe formatting
- Models are fetched fresh each time a modal opens to reflect current provider key status in real time
- Edit modal shows a warning banner when the agent's current model is not in the available models list (provider key may have been removed), but still allows the stale value in the dropdown for visibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 07 is now fully complete (both plans executed)
- v2.1 milestone (Stability & Quality) is complete
- All frontend model references consolidated, Gemini fully purged, XSS vectors eliminated
- API key management is end-to-end functional (backend from Plan 01, UI from Plan 02)

## Self-Check: PASSED

- All 7 created/modified files exist on disk
- Commit `0233dc9` (Task 1) found in git log
- Commit `b626c13` (Task 2) found in git log
- SUMMARY.md created at expected path

---
*Phase: 07-agent-configuration-provider-management*
*Completed: 2026-04-08*
