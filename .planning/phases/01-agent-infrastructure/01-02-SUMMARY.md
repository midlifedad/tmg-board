---
phase: 01-agent-infrastructure
plan: 02
subsystem: services, tools
tags: [litellm, agent-loop, tool-calling, httpx, sse-events, async-streaming]

# Dependency graph
requires:
  - phase: 01-01
    provides: AgentConfig model, test fixtures (conftest.py), LLM provider API key config
provides:
  - LiteLLM wrapper with get_completion() and validate_provider_keys()
  - Core agent loop (run_agent, run_agent_streaming) with tool iteration
  - Tool registry (TOOL_REGISTRY, ToolDefinition, get_tools_for_agent, execute_tool)
  - Three meeting tools (create_agenda_item, get_meeting, list_meetings)
  - SSE event protocol (start, tool_start, tool_result, text_delta, usage, done)
affects: [01-03, 01-04, 02, 03, 04, 05]

# Tech tracking
tech-stack:
  added: [litellm>=1.82.0]
  patterns: [hybrid streaming (non-stream for tools, single text_delta for final), tool-via-API with X-User-Email header, tool registry with auto-registration on import]

key-files:
  created:
    - backend/app/services/llm_provider.py
    - backend/app/services/agent_runner.py
    - backend/app/tools/__init__.py
    - backend/app/tools/meetings.py
    - backend/tests/test_tools.py
    - backend/tests/test_agent_runner.py
  modified: []

key-decisions:
  - "Hybrid streaming strategy: non-streaming for tool iterations, single text_delta for final response (avoids tool call accumulation pitfall)"
  - "Tools call board REST API via httpx.AsyncClient with X-User-Email header for auth context forwarding"
  - "Tool registry uses auto-registration on import via register_tool() at module level"
  - "Used __future__ annotations for Python 3.9 compatibility with union type syntax"

patterns-established:
  - "Tool registration: import tool module at bottom of __init__.py to trigger register_tool() calls"
  - "Agent runner takes config object with model/temperature/max_iterations/allowed_tool_names"
  - "SSE event protocol: start -> tool_start/tool_result (if tools) -> text_delta -> usage -> done"
  - "Tool error handling: catch exceptions and return JSON {error: message} instead of raising"

requirements-completed: [AGENT-01, AGENT-02, AGENT-04]

# Metrics
duration: 4min
completed: 2026-03-04
---

# Phase 01 Plan 02: Agent Runner & Tool System Summary

**Core agent loop with LiteLLM tool iteration, 3 meeting tools calling board REST API via httpx, and hybrid streaming SSE event protocol -- 15 tests passing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-04T20:46:20Z
- **Completed:** 2026-03-04T20:50:43Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- LiteLLM wrapper with centralized get_completion() and provider key validation
- Agent runner loop (run_agent) that calls LLM, executes tool calls, and iterates until final text
- Streaming agent runner (run_agent_streaming) yielding SSE events in protocol order
- Tool registry with ToolDefinition dataclass, filtering by agent allowed_tool_names
- Three meeting tools (create_agenda_item, get_meeting, list_meetings) calling board REST API with auth context
- Max iterations safety limit prevents infinite tool loops
- All tool errors caught and returned as JSON (no exceptions bubble up)

## Task Commits

Each task was committed atomically:

1. **Task 1: LLM provider wrapper, tool registry, and tool implementations**
   - `f9750d4` (test) - Failing tests for tool registry, tool execution, and LLM provider (RED)
   - `c4bc635` (feat) - LLM provider wrapper, tool registry, and meeting tools (GREEN)
2. **Task 2: Agent runner -- core loop with tool iteration and streaming**
   - `0e439e6` (test) - Failing tests for agent runner loop and streaming (RED)
   - `6b58987` (feat) - Agent runner with tool iteration loop and streaming (GREEN)

_TDD tasks have RED + GREEN commits as shown above._

## Files Created/Modified
- `backend/app/services/llm_provider.py` - LiteLLM wrapper with get_completion() and validate_provider_keys()
- `backend/app/services/agent_runner.py` - Core agent loop: run_agent() and run_agent_streaming()
- `backend/app/tools/__init__.py` - Tool registry with ToolDefinition, get_tools_for_agent(), execute_tool()
- `backend/app/tools/meetings.py` - Three meeting tools calling board REST API with X-User-Email
- `backend/tests/test_tools.py` - 8 tests for tool registry, execution, API calls, error handling, provider keys
- `backend/tests/test_agent_runner.py` - 7 tests for agent loop, tool cycles, max iterations, streaming events

## Decisions Made
- **Hybrid streaming strategy** -- non-streaming LLM calls for tool detection (avoids the tool call accumulation pitfall from streaming), yield final response content as a single text_delta event. Progressive streaming of the final response can be optimized later.
- **Tool-via-API pattern** -- tools call the board's own REST API using httpx.AsyncClient with the invoking user's X-User-Email header, preserving auth, validation, and audit logging.
- **Auto-registration on import** -- tool modules call register_tool() at module level, and are imported at the bottom of tools/__init__.py. No manual registry maintenance needed.
- **Python 3.9 compatibility** -- used `from __future__ import annotations` instead of `X | None` union syntax, matching the Python version in the backend .venv.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed litellm dependency**
- **Found during:** Task 1 (tool tests failing on import)
- **Issue:** litellm was listed in requirements.txt but not installed in .venv
- **Fix:** Ran `pip install litellm` in the backend .venv
- **Files modified:** .venv/ (gitignored)
- **Verification:** All imports succeed, tests pass
- **Committed in:** N/A (.venv is gitignored)

**2. [Rule 1 - Bug] Fixed Python 3.9 type annotation syntax**
- **Found during:** Task 1 (llm_provider.py failing with TypeError)
- **Issue:** Used `list[dict] | None` syntax which requires Python 3.10+; backend runs Python 3.9
- **Fix:** Added `from __future__ import annotations` and used `Optional[List[dict]]` from typing
- **Files modified:** backend/app/services/llm_provider.py
- **Verification:** test_validate_provider_keys passes
- **Committed in:** `c4bc635` (part of Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both necessary for correct execution. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations.

## User Setup Required
None - no external service configuration required. LLM API keys are read from environment variables by LiteLLM automatically.

## Next Phase Readiness
- Agent runner and tool system ready for Plan 03 (SSE endpoint wrapping run_agent_streaming)
- Tool registry can be extended with new tool modules (documents, decisions) in future phases
- SSE event protocol defined and tested, ready for frontend consumption in Plan 04
- All 25 tests passing (10 from Plan 01 + 15 from Plan 02) as baseline

## Self-Check: PASSED

All 6 created files verified on disk. All 4 commits verified in git log.

---
*Phase: 01-agent-infrastructure*
*Completed: 2026-03-04*
