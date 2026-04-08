# Phase 01 Plan Verification: Agent Infrastructure & Streaming UX

**Verified:** 2026-03-04
**Plans checked:** 4 (01-01, 01-02, 01-03, 01-04)
**Status:** ISSUES FOUND

---

## Phase Goal

Board members can invoke AI agents that stream responses inline on existing pages, with tool call indicators, using any configured LLM provider.

## Phase Requirements

AGENT-01, AGENT-02, AGENT-03, AGENT-04, UX-02, UX-03, UX-04

---

## Dimension 1: Requirement Coverage

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| AGENT-01: Route user requests to configured agents | 01-01, 01-02 | 01-01 T1 (models/schemas), 01-01 T2 (seed data), 01-02 T2 (agent runner) | COVERED |
| AGENT-02: Tools call board REST API with user auth context | 01-02 | 01-02 T1 (tool registry + meeting tools with X-User-Email) | COVERED |
| AGENT-03: Agent responses stream via SSE | 01-03 | 01-03 T1 (SSE endpoint), 01-03 T2 (proxy fix) | COVERED |
| AGENT-04: Multiple LLM providers via LiteLLM | 01-01, 01-02 | 01-01 T1 (litellm dep + config keys), 01-02 T1 (LLM provider wrapper) | COVERED |
| UX-02: Agent responses appear inline on page | 01-04 | 01-04 T2 (AgentResponsePanel) | COVERED |
| UX-03: Streaming output with tool call indicators | 01-04 | 01-04 T1 (useAgentStream hook), 01-04 T2 (ToolCallIndicator) | COVERED |
| UX-04: Agent actions apply to current context | 01-04 | 01-04 T1 (onToolComplete callback), 01-04 T2 (panel integration pattern) | COVERED |

**Result: PASS** -- All 7 requirements have covering tasks with specific implementation details.

---

## Dimension 2: Task Completeness

### Plan 01-01 (2 tasks)

| Task | Type | Files | Action | Verify | Done | Status |
|------|------|-------|--------|--------|------|--------|
| T1: Dependencies, config, models, schemas | auto/tdd | YES (5 files) | YES (5 specific steps) | YES (automated import check) | YES | PASS |
| T2: Test infra, seed data, model tests | auto/tdd | YES (5 files) | YES (5 specific steps) | YES (automated pytest run) | YES | PASS |

### Plan 01-02 (2 tasks)

| Task | Type | Files | Action | Verify | Done | Status |
|------|------|-------|--------|--------|------|--------|
| T1: LLM provider, tool registry, tool implementations | auto/tdd | YES (5 files) | YES (5 specific steps, 8 test behaviors) | YES (automated pytest run) | YES | PASS |
| T2: Agent runner -- core loop with streaming | auto/tdd | YES (2 files) | YES (detailed run_agent + run_agent_streaming, 7 test behaviors) | YES (automated pytest run) | YES | PASS |

### Plan 01-03 (2 tasks)

| Task | Type | Files | Action | Verify | Done | Status |
|------|------|-------|--------|--------|------|--------|
| T1: Agent API endpoints with SSE streaming | auto/tdd | YES (2 files) | YES (3 endpoints + 10 test behaviors) | YES (automated pytest run) | YES | PASS |
| T2: Next.js proxy SSE streaming fix | auto | YES (1 file) | YES (specific code with insertion point) | YES (automated next build) | YES | PASS |

### Plan 01-04 (3 tasks)

| Task | Type | Files | Action | Verify | Done | Status |
|------|------|-------|--------|--------|------|--------|
| T1: Types, useAgentStream hook, react-markdown | auto | YES (3 files) | YES (3 specific steps) | YES (automated tsc --noEmit) | YES | PASS |
| T2: AgentResponsePanel and ToolCallIndicator | auto | YES (2 files) | YES (detailed component specs) | YES (automated tsc --noEmit) | YES | PASS |
| T3: Visual checkpoint | checkpoint:human-verify | N/A | YES (verification steps) | Human | YES | PASS |

**Result: PASS** -- All 9 tasks have required fields. Actions are specific with file paths, function names, and parameter details. Verify commands are automated and runnable.

---

## Dimension 3: Dependency Correctness

| Plan | depends_on | Wave | Valid? |
|------|------------|------|--------|
| 01-01 | [] | 1 | YES |
| 01-02 | [01-01] | 2 | YES -- uses models, schemas, config, test fixtures from 01-01 |
| 01-03 | [01-02] | 3 | YES -- uses agent_runner, tool registry from 01-02 |
| 01-04 | [01-03] | 4 | YES -- needs SSE endpoint and proxy fix from 01-03 |

Dependency graph: 01-01 -> 01-02 -> 01-03 -> 01-04

- No cycles
- No missing references
- All forward references are valid (01-02 references 01-01-SUMMARY.md which will exist after 01-01 executes)
- Wave assignments are consistent with dependencies
- Sequential ordering is correct (each plan builds on the previous)

**Result: PASS** -- Linear dependency chain with no issues.

---

## Dimension 4: Key Links Planned

### Plan 01-01: Foundation
| From | To | Via | Planned? |
|------|----|-----|----------|
| agent.py models | models/__init__.py | import and __all__ | YES (Task 1 step 4) |
| main.py | agent.py | seed data in lifespan | YES (Task 2 step 5) |
| config.py | environment variables | pydantic-settings | YES (Task 1 step 2) |
| main.py | agents.py router | include_router placeholder | YES (Task 2 step 5) |

### Plan 01-02: Agent Engine
| From | To | Via | Planned? |
|------|----|-----|----------|
| agent_runner.py | litellm.acompletion | async LLM call | YES (Task 2 action) |
| agent_runner.py | tools/__init__.py | get_tools_for_agent, execute_tool | YES (Task 2 action) |
| tools/meetings.py | board REST API | httpx with X-User-Email | YES (Task 1 step 4) |
| tools/__init__.py | tools/meetings.py | import at bottom for registration | YES (Task 1 step 4 IMPORTANT note) |

### Plan 01-03: SSE Layer
| From | To | Via | Planned? |
|------|----|-----|----------|
| agents.py endpoint | agent_runner.py | run_agent_streaming call | YES (Task 1 action step 3) |
| agents.py endpoint | fastapi.sse | EventSourceResponse wrapping | YES (Task 1 action step 3) |
| proxy route.ts | backend SSE | ReadableStream pass-through | YES (Task 2 action) |

### Plan 01-04: Frontend
| From | To | Via | Planned? |
|------|----|-----|----------|
| use-agent-stream.ts | /api/proxy/agents/run | fetch POST with SSE consumption | YES (Task 1 step 3) |
| agent-response-panel.tsx | use-agent-stream.ts | useAgentStream hook | YES (Task 2 step 2) |
| agent-response-panel.tsx | tool-call-indicator.tsx | renders ToolCallIndicator | YES (Task 2 step 2) |
| use-agent-stream.ts | onToolComplete callback | fires after tool_result | YES (Task 1 step 3) |

**Result: PASS** -- All critical wiring is explicitly described in task actions. The tool registration import pattern (bottom-of-file import for side-effect registration) is called out. The proxy SSE fix is detailed with exact code. The frontend hook connects to the proxy endpoint (not direct backend).

---

## Dimension 5: Scope Sanity

| Plan | Tasks | Files | Estimated Context | Status |
|------|-------|-------|-------------------|--------|
| 01-01 | 2 | 10 | ~30% | WARNING (file count) |
| 01-02 | 2 | 7 | ~35% | OK |
| 01-03 | 2 | 3 | ~25% | OK |
| 01-04 | 3 | 5 + npm install | ~35% | OK |

**Plan 01-01** has 10 files_modified, which exceeds the warning threshold of 10. However, 4 of these files are minimal (pytest.ini, tests/__init__.py, conftest.py, models/__init__.py update) -- the substantial work is in 3 files (models/agent.py, schemas/agent.py, config.py). The scope is reasonable for a foundation plan.

**Plan 01-04** has 3 tasks but one is a checkpoint (no executor work), so effective implementation tasks = 2. This is fine.

**Total tasks across all plans:** 9 (8 auto + 1 checkpoint). Sequential execution with 4 waves.

**Result: PASS** (with info note on 01-01 file count)

---

## Dimension 6: Verification Derivation (must_haves)

### Plan 01-01 must_haves
- Truths: "AgentConfig and AgentUsageLog tables exist" (testable), "Three built-in agents are seeded" (testable), "LLM provider API keys are configurable" (testable), "pytest runs and passes" (testable) -- all user-observable/verifiable
- Artifacts: models, schemas, conftest.py, pytest.ini -- all map to truths
- Key links: model registration, seed data, config -- critical wiring

### Plan 01-02 must_haves
- Truths: "Agent runner calls LiteLLM correctly" (testable), "Agent executes tools and feeds results back" (testable), "Agent stops after max_iterations" (testable), "Tools call REST API with user auth" (testable), "Tool registry returns correct schemas" (testable), "Tool errors caught gracefully" (testable)
- Artifacts: llm_provider.py, agent_runner.py, tools/__init__.py, meetings.py, 2 test files -- all map to truths

### Plan 01-03 must_haves
- Truths: "POST returns text/event-stream" (testable), "SSE events in correct order" (testable), "Auth required" (testable), "404 for unknown agent" (testable), "Usage log created" (testable), "Proxy forwards SSE" (testable)
- Artifacts: agents.py, proxy route.ts, test file -- all map to truths

### Plan 01-04 must_haves
- Truths: "User can trigger agent and see inline response" (user-observable), "Streaming text appears progressively" (user-observable), "Tool calls show spinner/checkmark" (user-observable), "Panel is collapsible with dark theme" (user-observable), "User can cancel" (user-observable), "onToolComplete fires" (testable)
- Artifacts: types, hook, panel, indicator -- all map to truths

**Result: PASS** -- All truths are user-observable or testable, not implementation-focused. Artifacts map to truths.

---

## Dimension 7: Context Compliance

No CONTEXT.md exists for this phase. Skipped.

---

## Dimension 8: Nyquist Compliance

SKIPPED -- No "Validation Architecture" section in RESEARCH.md, and no VALIDATION.md exists.

---

## Critical Path Analysis

### Proxy SSE Fix
The research identified that the Next.js proxy buffers SSE responses (Pitfall S1). Plan 01-03 Task 2 explicitly fixes this with the `text/event-stream` detection and `ReadableStream` pass-through. This is on the critical path and is properly addressed.

### Streaming Strategy
The research recommended Pattern S1 (hybrid streaming: non-stream for tool iterations, stream only final text). Plan 01-02 Task 2 implements a simplified version where the non-streaming response content is yielded as a single `text_delta` event (not re-calling with stream=True). This is noted as an "OPTIMIZATION" simplification for v1. The plan explicitly acknowledges this tradeoff and notes progressive streaming can be added later. This is acceptable for Phase 01.

### Test Coverage
Every plan includes tests:
- Plan 01-01: 6 model tests (test_models.py)
- Plan 01-02: 8 tool tests (test_tools.py) + 7 agent runner tests (test_agent_runner.py)
- Plan 01-03: 10 API integration tests (test_agent_api.py)
- Plan 01-04: TypeScript compilation check + human visual verification

Total: ~31 automated backend tests + TypeScript compilation + human checkpoint. This is thorough for the scope.

### Multi-Provider Verification
Success Criterion 4 states "the same agent invocation works when the underlying model is swapped to Anthropic, Gemini, or Groq without frontend changes." The plans handle this via:
- Plan 01-01: config.py stores all three provider API keys
- Plan 01-02: LLM provider wrapper + LiteLLM abstraction (model string like "anthropic/...", "gemini/...", "groq/...")
- Plan 01-02: Agent runner passes config.model directly to LiteLLM

However, no test explicitly verifies multi-provider compatibility (all tests use "anthropic/claude-sonnet-4-5-20250929"). This is acceptable because LiteLLM handles provider normalization -- the plans correctly rely on the library rather than testing it. The validate_provider_keys function in Plan 01-02 does verify key configuration per provider.

---

## Success Criteria Verification

| # | Success Criterion | How Plans Achieve It |
|---|-------------------|---------------------|
| 1 | User can trigger agent, see response inline (no redirect) | Plan 01-04: AgentResponsePanel embeds on existing pages with collapsible design, useAgentStream hook fetches from proxy |
| 2 | Response streams in real time | Plan 01-02: run_agent_streaming yields events; Plan 01-03: SSE endpoint + proxy fix; Plan 01-04: useAgentStream processes events progressively |
| 3 | Tool calls show indicator with result | Plan 01-02: tool_start/tool_result events; Plan 01-04: ToolCallIndicator component with executing/completed/failed states |
| 4 | Same invocation works across Anthropic/Gemini/Groq | Plan 01-01: 3 API keys in config; Plan 01-02: LiteLLM abstraction, model string from AgentConfig |
| 5 | Tool actions take effect, respect permissions | Plan 01-02: tools call board REST API with X-User-Email; Plan 01-04: onToolComplete triggers page data refresh |

**Result: PASS** -- All 5 success criteria are traceable to specific plan tasks.

---

## Warnings

### Warning 1: [scope_sanity] Plan 01-01 has 10 files_modified

- **Plan:** 01-01
- **Severity:** info
- **Description:** Plan 01-01 lists 10 files in files_modified, which reaches the warning threshold. However, 4 of those are minimal files (empty __init__.py, pytest.ini config, etc.) and the plan has only 2 tasks with well-scoped actions. The scope is actually reasonable.
- **Fix:** No action needed. This is informational.

### Warning 2: [key_links_planned] agent-api.ts mentioned in research but absent from plans

- **Plan:** 01-04
- **Severity:** info
- **Description:** The research supplement lists `frontend/src/lib/agent-api.ts` as a file to create (Agent API client functions). This file is not included in any plan. However, Plan 01-04 embeds the fetch call directly in the useAgentStream hook, which accomplishes the same purpose without a separate API client file. The hook IS the API client for agent invocation.
- **Fix:** No action needed. The hook approach is simpler and sufficient for Phase 01. A separate agent-api.ts could be added later if needed.

### Warning 3: [key_links_planned] `list_members` tool referenced in seed data but not implemented

- **Plan:** 01-01, 01-02
- **Severity:** warning
- **Description:** The Meeting Setup agent's `allowed_tool_names` in the seed data (Plan 01-01 Task 2) includes `"list_members"`, but Plan 01-02 only implements 3 meeting tools: `create_agenda_item`, `get_meeting`, `list_meetings`. The `list_members` tool is not implemented in any plan. When the agent tries to use this tool at runtime, the tool registry will return an "Unknown tool" error.
- **Fix:** Either (a) remove `list_members` from the Meeting Setup seed data allowed_tool_names, or (b) add a `list_members` tool implementation in Plan 01-02 Task 1 (under tools/meetings.py or a new tools/members.py). Option (a) is simpler since the detailed Meeting Setup agent prompt is deferred to Phase 02 anyway and the allowed_tool_names can be updated then.

### Warning 4: [task_completeness] Plan 01-04 frontend has no automated tests

- **Plan:** 01-04
- **Severity:** info
- **Description:** Plan 01-04 relies on TypeScript compilation checks and a human visual checkpoint for verification. There are no automated frontend tests (no Jest, Vitest, or Playwright). The research supplement explicitly acknowledges this: "Frontend tests are manual-only for Phase 01. The project has no frontend test setup."
- **Fix:** No action needed for Phase 01. TypeScript compilation catches type errors. The human checkpoint covers visual/behavioral verification. Frontend test infrastructure can be added in a later phase.

### Warning 5: [verification_derivation] Streaming text_delta is a single chunk in v1

- **Plan:** 01-02
- **Severity:** info
- **Description:** Plan 01-02 Task 2 notes that the initial implementation yields the final response content as a single `text_delta` event rather than streaming it token-by-token. This means the text will appear all at once (after tool iterations complete) rather than word-by-word. This partially addresses Success Criterion 2 ("text appears progressively") -- it is progressive relative to tool call events, but the final text itself is not progressive.
- **Fix:** The plan explicitly acknowledges this tradeoff and defers token-by-token streaming as an optimization. For Phase 01, the UX still shows: start -> tool indicators -> text result -> done, which is sufficient to demonstrate the streaming infrastructure. The research Pattern S1 shows the full streaming approach that can be added later.

---

## Structured Issues

```yaml
issues:
  - issue:
      plan: "01-01"
      dimension: scope_sanity
      severity: info
      description: "Plan 01-01 has 10 files_modified (at warning threshold), but most are minimal. Scope is manageable with 2 tasks."
      fix_hint: "No action needed. Informational."

  - issue:
      plan: "01-04"
      dimension: key_links_planned
      severity: info
      description: "agent-api.ts from research is absent; useAgentStream hook handles API calls directly."
      fix_hint: "No action needed. Hook approach is simpler."

  - issue:
      plan: "01-01, 01-02"
      dimension: key_links_planned
      severity: warning
      description: "list_members tool is in Meeting Setup seed data allowed_tool_names but not implemented in any plan's tool registry."
      fix_hint: "Remove list_members from seed data allowed_tool_names in Plan 01-01 Task 2 step 5a, or add a list_members tool in Plan 01-02 Task 1."

  - issue:
      plan: "01-04"
      dimension: task_completeness
      severity: info
      description: "No automated frontend tests. Relies on tsc compilation + human checkpoint."
      fix_hint: "Acceptable for Phase 01. No frontend test infra exists in the project."

  - issue:
      plan: "01-02"
      dimension: verification_derivation
      severity: info
      description: "Final text response yielded as single text_delta (not progressive token streaming). Partially addresses SC-2."
      fix_hint: "Acknowledged in plan as v1 simplification. Progressive streaming deferred."
```

---

## Overall Assessment

### VERIFICATION PASSED (with minor warnings)

**Phase:** 01 - Agent Infrastructure & Streaming UX
**Plans verified:** 4
**Status:** All checks passed. 0 blockers, 1 warning, 4 info.

### Coverage Summary

| Requirement | Plans | Status |
|-------------|-------|--------|
| AGENT-01 | 01-01, 01-02 | COVERED |
| AGENT-02 | 01-02 | COVERED |
| AGENT-03 | 01-03 | COVERED |
| AGENT-04 | 01-01, 01-02 | COVERED |
| UX-02 | 01-04 | COVERED |
| UX-03 | 01-04 | COVERED |
| UX-04 | 01-04 | COVERED |

### Plan Summary

| Plan | Tasks | Files | Wave | Status |
|------|-------|-------|------|--------|
| 01-01 | 2 | 10 | 1 | Valid |
| 01-02 | 2 | 7 | 2 | Valid |
| 01-03 | 2 | 3 | 3 | Valid |
| 01-04 | 3 (2 auto + 1 checkpoint) | 5 | 4 | Valid |

### Recommendation

The plans are well-structured, thoroughly detailed, and will achieve the phase goal. The only actionable item is **Warning 3** (list_members tool mismatch) -- the planner should decide whether to remove it from seed data or add a tool implementation. This is minor and non-blocking since the seed data uses placeholder prompts anyway, and the Meeting Setup agent will be fully configured in Phase 02.

Plans verified. Proceed to execution with `/gsd:execute-phase 01`.

---
*Verification completed: 2026-03-04*
