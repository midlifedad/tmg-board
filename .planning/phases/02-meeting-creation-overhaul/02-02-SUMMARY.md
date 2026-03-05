---
phase: 02-meeting-creation-overhaul
plan: 02
subsystem: tools, agents
tags: [tool-calling, httpx, agent-prompt, meeting-setup, system-prompt, agenda-parsing]

# Dependency graph
requires:
  - phase: 01-02
    provides: Tool registry (TOOL_REGISTRY, ToolDefinition, register_tool), meeting tools pattern, httpx API call pattern
  - phase: 01-01
    provides: AgentConfig model, _seed_agents() function, test fixtures (conftest.py)
provides:
  - create_meeting_with_agenda tool registered in TOOL_REGISTRY
  - Production system prompt for Meeting Setup agent with item_type classification rules
  - Upgrade path for existing agents (placeholder detection and auto-update)
affects: [02-03, 03, 05]

# Tech tracking
tech-stack:
  added: []
  patterns: [batch tool calling (single tool creates meeting + N agenda items), agent prompt with classification rules, seed data upgrade block for existing databases]

key-files:
  created: []
  modified:
    - backend/app/tools/meetings.py
    - backend/app/main.py
    - backend/tests/test_tools.py
    - backend/tests/test_seed_agents.py

key-decisions:
  - "Production system prompt instructs single-turn parsing (no follow-up questions) with missing field reporting"
  - "Upgrade block in _seed_agents() auto-updates agents still on Phase 01 placeholder prompt"
  - "Replaced list_members with list_meetings in allowed_tool_names (list_members was never a registered tool)"

patterns-established:
  - "Agent prompt classification: information/discussion/decision_required/consent_agenda with heuristic rules"
  - "Seed data upgrade pattern: check for placeholder text, update system_prompt and allowed_tool_names if found"

requirements-completed: [BUILT-01, MEET-01]

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 02 Plan 02: Meeting Setup Agent Summary

**create_meeting_with_agenda tool calling /api/meetings/with-agenda via httpx, production system prompt with item_type classification rules, and seed data upgrade block -- 14 tool tests passing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T01:35:07Z
- **Completed:** 2026-03-05T01:38:11Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- New `create_meeting_with_agenda` tool registered in TOOL_REGISTRY with full OpenAI function-calling schema (title, scheduled_date, duration_minutes, location, meeting_link, description, agenda_items array)
- Production system prompt for Meeting Setup agent: instructs LLM to parse unstructured meeting descriptions, classify item types, estimate durations, and report missing fields without follow-up questions
- Updated allowed_tool_names to include create_meeting_with_agenda and list_meetings (replacing non-existent list_members)
- Seed data upgrade block auto-updates existing agents still on Phase 01 placeholder prompt
- 6 new tests covering tool registration, schema, API call, error handling, and agent config

## Task Commits

Each task was committed atomically:

1. **Task 1: create_meeting_with_agenda tool and Meeting Setup agent prompt update (TDD)**
   - `7773ff0` (test) - Failing tests for tool registration, schema, API calls, agent config (RED)
   - `af180fc` (feat) - Tool implementation, production system prompt, seed upgrade block (GREEN)

_TDD task with RED + GREEN commits as shown above._

## Files Created/Modified
- `backend/app/tools/meetings.py` - Added create_meeting_with_agenda tool handler and registration (POSTs to /api/meetings/with-agenda)
- `backend/app/main.py` - Production system prompt (_MEETING_SETUP_SYSTEM_PROMPT), updated seed data, upgrade block for existing agents
- `backend/tests/test_tools.py` - 6 new tests for create_meeting_with_agenda tool
- `backend/tests/test_seed_agents.py` - Updated assertions for new allowed_tool_names

## Decisions Made
- **Single-turn prompt design** -- Agent parses what it can and reports missing fields in response. No follow-up question loop (aligns with Phase 01 decision for narrow-purpose agents).
- **Seed data upgrade pattern** -- Added an `else` branch in `_seed_agents()` that detects the Phase 01 placeholder text and upgrades the agent's system_prompt and allowed_tool_names. This handles databases created before this plan.
- **Replaced list_members with list_meetings** -- The original seed data referenced `list_members` which was never a registered tool. Replaced with `list_meetings` which exists in TOOL_REGISTRY.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_seed_agents.py for new allowed_tool_names**
- **Found during:** Task 1 (full test suite verification)
- **Issue:** `test_meeting_setup_agent_config` in `test_seed_agents.py` asserted `list_members` was in allowed_tool_names, which was correct for the old seed data but fails after the intentional update
- **Fix:** Updated assertions to check for `create_meeting_with_agenda`, `create_agenda_item`, `get_meeting`, `list_meetings`
- **Files modified:** backend/tests/test_seed_agents.py
- **Verification:** Full test suite passes (47 tests)
- **Committed in:** `af180fc` (part of Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary update to match intentional seed data change. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- create_meeting_with_agenda tool is ready for the frontend to invoke via the Meeting Setup agent
- Plan 02-01 provides the /api/meetings/with-agenda endpoint that this tool calls
- Plan 02-03 (frontend) can now build the AI-assisted paste section that invokes the Meeting Setup agent
- All 47 tests passing as baseline (up from 41 before this plan)

## Self-Check: PASSED

All 4 modified files verified on disk. Both commits verified in git log.

---
*Phase: 02-meeting-creation-overhaul*
*Completed: 2026-03-05*
