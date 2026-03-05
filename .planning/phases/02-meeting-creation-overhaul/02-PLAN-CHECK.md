# Phase 02: Meeting Creation Overhaul & Meeting Setup Agent - Plan Check

**Checked:** 2026-03-04
**Plans verified:** 3 (02-01, 02-02, 02-03)
**Status:** PASSED

## Phase Goal

Users can create meetings by pasting a description for agent-assisted population or filling fields manually, and admins can define reusable templates with regulatory items.

## Dimension 1: Requirement Coverage

| Requirement | Description | Plans | Tasks | Status |
|-------------|-------------|-------|-------|--------|
| MEET-01 | User can paste description for agent-parsed meeting | 02-02, 02-03 | 02-02:T1, 02-03:T1 | COVERED |
| MEET-02 | User can fill in meeting details manually (improved UX) | 02-03 | 02-03:T1 | COVERED |
| MEET-03 | Admin can create meeting templates with standard agenda items | 02-01 | 02-01:T1, 02-01:T2 | COVERED |
| MEET-04 | User can apply template when creating a meeting, then customize | 02-01, 02-03 | 02-01:T2 (API), 02-03:T1 (UI) | COVERED |
| MEET-05 | Templates can include required regulatory items | 02-01, 02-03 | 02-01:T1 (model), 02-03:T1 (UI) | COVERED |
| UX-01 | Expandable section for paste-to-populate agent setup | 02-03 | 02-03:T1 | COVERED |
| BUILT-01 | Meeting Setup agent parses description into structured meeting | 02-02 | 02-02:T1 | COVERED |

**Result:** ALL 7 requirements covered. No gaps.

## Dimension 2: Task Completeness

### Plan 02-01 (2 tasks)

| Task | Type | Has Files | Has Action | Has Verify | Has Done | Status |
|------|------|-----------|------------|------------|----------|--------|
| T1: Models, migration, tests | auto (tdd) | Yes | Yes (detailed) | Yes (automated) | Yes | COMPLETE |
| T2: Template CRUD API, batch endpoint, seed, tests | auto (tdd) | Yes | Yes (detailed) | Yes (automated) | Yes | COMPLETE |

### Plan 02-02 (1 task)

| Task | Type | Has Files | Has Action | Has Verify | Has Done | Status |
|------|------|-----------|------------|------------|----------|--------|
| T1: Tool + agent prompt | auto (tdd) | Yes | Yes (detailed) | Yes (automated) | Yes | COMPLETE |

### Plan 02-03 (3 tasks)

| Task | Type | Has Files | Has Action | Has Verify | Has Done | Status |
|------|------|-----------|------------|------------|----------|--------|
| T1: API client, create page, meetings page nav | auto | Yes | Yes (detailed) | Yes (automated) | Yes | COMPLETE |
| T2: Admin templates page, sidebar update | auto | Yes | Yes (detailed) | Yes (automated) | Yes | COMPLETE |
| T3: E2E verification | checkpoint:human-verify | N/A | N/A | N/A | N/A | VALID |

**Result:** All tasks have required elements. Actions are specific with code samples, file paths, and exact implementation steps. Verify commands are runnable (pytest, tsc). Done criteria are measurable.

## Dimension 3: Dependency Correctness

| Plan | Wave | depends_on | Valid? |
|------|------|------------|--------|
| 02-01 | 1 | [] | Yes - no dependencies, foundation plan |
| 02-02 | 1 | [] | Yes - runs parallel with 02-01 |
| 02-03 | 2 | [02-01, 02-02] | Yes - needs both backend APIs before frontend |

**Dependency graph:**
```
Wave 1:  02-01 (backend templates/batch API)  ||  02-02 (agent tool + prompt)
              \                                   /
Wave 2:       02-03 (frontend: create page, admin templates, sidebar)
```

**Analysis:**
- No cycles detected.
- All references are valid (02-01 and 02-02 exist).
- Wave assignments are consistent with dependencies: Wave 1 plans have no deps, Wave 2 plan depends on both Wave 1 plans.
- 02-02 correctly notes it can run parallel with 02-01 since the tool definition is independent code (the tool calls the endpoint from 02-01 but the code itself is standalone).

**Result:** Dependency graph is valid and acyclic. Wave assignments are correct.

## Dimension 4: Key Links Planned

### Plan 02-01 Key Links

| From | To | Via | Task Coverage | Status |
|------|----|----|---------------|--------|
| templates.py (API) | template.py (models) | SQLAlchemy queries | T2 action: endpoints query MeetingTemplate/TemplateAgendaItem | WIRED |
| meetings.py (batch endpoint) | meeting.py (models) | batch agenda creation | T2 action: create Meeting + AgendaItems atomically | WIRED |
| main.py | templates.py | router registration | T2 action step 3: include_router(templates.router) | WIRED |

### Plan 02-02 Key Links

| From | To | Via | Task Coverage | Status |
|------|----|----|---------------|--------|
| main.py (seed) | tools/meetings.py | allowed_tool_names includes create_meeting_with_agenda | T1 action step 2: update allowed_tool_names | WIRED |
| tools/meetings.py | api/meetings.py | httpx POST to /api/meetings/with-agenda | T1 action step 1: handler calls the batch endpoint | WIRED |

### Plan 02-03 Key Links

| From | To | Via | Task Coverage | Status |
|------|----|----|---------------|--------|
| create/page.tsx | api.ts | meetingsApi.createWithAgenda and templatesApi calls | T1 action: API methods added + used in page | WIRED |
| create/page.tsx | use-agent-stream.ts | useAgentStream hook for AI section | T1 action: calls meeting-setup agent, handles tool_result for redirect | WIRED |
| meetings/page.tsx | create/page.tsx | navigation link (replaces modal) | T1 action step 3: replace modal with router.push | WIRED |
| sidebar.tsx | admin/templates/page.tsx | sidebar nav link | T2 action step 2: add Templates to Admin nav group | WIRED |

**Result:** All key links are planned with specific wiring instructions. No orphaned artifacts.

## Dimension 5: Scope Sanity

| Plan | Tasks | Files Modified | Wave | Status |
|------|-------|----------------|------|--------|
| 02-01 | 2 | 8 | 1 | OK (2 tasks, 8 files is within range) |
| 02-02 | 1 | 3 | 1 | OK (1 task, 3 files is lean) |
| 02-03 | 3 | 5 | 2 | OK (2 auto + 1 checkpoint, 5 files) |

**Analysis:**
- Plan 02-01: 2 TDD tasks with 8 files. The files are well-scoped: 2 model files, 1 migration, 2 API files, 1 main.py, 2 test files. Within the 5-8 files target.
- Plan 02-02: 1 TDD task with 3 files. Very lean and focused. Well within budget.
- Plan 02-03: 2 auto tasks + 1 human checkpoint with 5 files. Task 1 modifies 3 files (api.ts, create/page.tsx, meetings/page.tsx) and Task 2 modifies 2 files (admin/templates/page.tsx, sidebar.tsx). Reasonable.

**Concern (info-level):** Plan 02-03 Task 1 creates a large meeting creation page (min_lines: 150 per must_haves). This page has three sections (AI-assisted, template selector, manual form with inline agenda builder) which is significant UI complexity. However, the action is extremely detailed with exact component structure, state management, and styling guidance, which mitigates risk. The planner chose to consolidate the page into one task rather than splitting it, which is reasonable since these sections are tightly coupled within one page component.

**Result:** All plans are within scope thresholds.

## Dimension 6: Verification Derivation

### Plan 02-01 must_haves.truths

| Truth | User-Observable? | Testable? |
|-------|-------------------|-----------|
| "Admin can create a meeting template with name, description, and agenda items" | Yes - admin action | Yes - API test |
| "Admin can update and soft-delete (deactivate) meeting templates" | Yes - admin action | Yes - API test |
| "Any board member can list active templates and view template details" | Yes - user action | Yes - API test |
| "Template agenda items can be flagged as regulatory (is_regulatory boolean)" | Yes - visible in UI | Yes - model test |
| "A meeting can be created with agenda items in a single API call" | Yes - user action | Yes - API test |
| "A meeting can be created from a template, pre-populating its agenda items" | Yes - user action | Yes - API test |

### Plan 02-02 must_haves.truths

| Truth | User-Observable? | Testable? |
|-------|-------------------|-----------|
| "Meeting Setup agent has a detailed system prompt that can parse unstructured meeting descriptions" | Partially - prompt is internal, but the parsing behavior is observable | Yes - behavior test via agent invocation |
| "Agent has a create_meeting_with_agenda tool that creates a meeting and its agenda items in one call" | Yes - agent creates meeting | Yes - tool registration test |
| "Agent system prompt includes rules for classifying item_type" | Internal detail | Warning: implementation-focused |
| "Agent leaves missing fields blank and tells the user what needs manual completion" | Yes - user sees agent response | Yes - behavior test |

### Plan 02-03 must_haves.truths

| Truth | User-Observable? | Testable? |
|-------|-------------------|-----------|
| "User can navigate to /meetings/create from the Meetings page" | Yes | Yes - navigation test |
| "User can fill in meeting details manually with inline agenda item editing" | Yes | Yes - UI interaction |
| "User can expand an AI-assisted section, paste a description, and trigger the Meeting Setup agent" | Yes | Yes - UI interaction |
| "Agent response streams inline and the created meeting is navigated to after success" | Yes | Yes - E2E test |
| "User can select a template to pre-populate the agenda items" | Yes | Yes - UI interaction |
| "Template regulatory items are visually indicated and warn on removal" | Yes | Yes - UI behavior |
| "Admin can view and manage templates at /admin/templates" | Yes | Yes - page exists |
| "Templates link appears in the sidebar Admin section for admin users" | Yes | Yes - UI check |

**Result:** Truths are predominantly user-observable and testable. One minor concern in Plan 02-02 where "Agent system prompt includes rules for classifying item_type" is implementation-focused rather than outcome-focused. This is an info-level observation -- the other truths in that plan adequately cover the user-observable behavior.

## Dimension 7: Context Compliance

No CONTEXT.md file exists for this phase. Skipped.

## Dimension 8: Nyquist Compliance

No VALIDATION.md exists. No RESEARCH.md "Validation Architecture" section. Skipped.

---

## Coverage Summary

| Requirement | Plans | Status |
|-------------|-------|--------|
| MEET-01 | 02-02, 02-03 | Covered |
| MEET-02 | 02-03 | Covered |
| MEET-03 | 02-01 | Covered |
| MEET-04 | 02-01, 02-03 | Covered |
| MEET-05 | 02-01, 02-03 | Covered |
| UX-01 | 02-03 | Covered |
| BUILT-01 | 02-02 | Covered |

## Plan Summary

| Plan | Tasks | Files | Wave | Status |
|------|-------|-------|------|--------|
| 02-01 | 2 | 8 | 1 | Valid |
| 02-02 | 1 | 3 | 1 | Valid |
| 02-03 | 3 (2 auto + 1 checkpoint) | 5 | 2 | Valid |

## Issues

```yaml
issues:
  - plan: "02-02"
    dimension: "verification_derivation"
    severity: "info"
    description: "Truth 'Agent system prompt includes rules for classifying item_type' is implementation-focused rather than user-observable"
    task: 1
    fix_hint: "Could reframe as 'Agent correctly classifies agenda items as information, discussion, decision_required, or consent_agenda based on meeting description content' but this is minor"
```

## Overall Assessment

**VERIFICATION PASSED**

All 7 phase requirements (MEET-01 through MEET-05, UX-01, BUILT-01) are covered by at least one plan with specific implementing tasks. Task completeness is excellent -- all tasks have detailed actions with code samples, runnable verify commands, and measurable done criteria. The dependency graph is clean with two parallel Wave 1 plans feeding into a Wave 2 frontend plan. Key links are explicitly planned between all dependent artifacts. Scope is well-managed: the largest plan (02-01) has only 2 tasks with 8 files, and the most complex single task (02-03:T1 for the meeting creation page) has exceptionally detailed guidance that mitigates its complexity.

The plans demonstrate strong alignment with both the success criteria from ROADMAP.md and the phase requirements from REQUIREMENTS.md. The research document's open questions (populate-vs-create for agent flow) have been resolved in the plans -- the planner chose the "agent creates directly + redirect" approach, which is a valid decision.

One info-level observation about an implementation-focused truth in Plan 02-02, but this does not affect plan viability.

Plans verified. Ready for execution.

---
*Plan check completed: 2026-03-04*
