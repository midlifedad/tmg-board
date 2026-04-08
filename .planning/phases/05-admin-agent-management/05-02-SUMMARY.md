---
phase: 05-admin-agent-management
plan: 02
subsystem: frontend-admin-agents
tags: [admin, agents, crud, usage-stats, modals, sidebar]
dependency_graph:
  requires: [05-01]
  provides: [admin-agents-ui, agent-create-modal, agent-edit-modal, sidebar-agents-nav]
  affects: [frontend/src/lib/api.ts, frontend/src/components/sidebar.tsx]
tech_stack:
  added: []
  patterns: [admin-page-layout, card-based-modals, button-based-tabs, tool-checkbox-assignment]
key_files:
  created:
    - frontend/src/app/admin/agents/page.tsx
    - frontend/src/components/create-agent-modal.tsx
    - frontend/src/components/edit-agent-modal.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/sidebar.tsx
decisions:
  - "AdminAgentConfig type avoids collision with user-facing AgentConfig"
  - "Hardcoded MODEL_LABELS map for friendly model display in table"
  - "Stale tool warnings in edit modal for tool registry sync visibility"
  - "Partial update in edit modal sends only changed fields"
metrics:
  duration: 3min
  completed: 2026-03-05
---

# Phase 05 Plan 02: Frontend Admin Agents Page Summary

Frontend admin agent management page with create/edit modals, tool assignment checkboxes, usage stats tab, and sidebar navigation -- following existing admin Users page patterns exactly.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | API client types and methods | c2753c6 | frontend/src/lib/api.ts |
| 2 | Admin agents page, modals, sidebar entry | a465bbf | frontend/src/app/admin/agents/page.tsx, create-agent-modal.tsx, edit-agent-modal.tsx, sidebar.tsx |

## What Was Built

### Task 1: API Client Types and Methods
- Added `AdminAgentConfig`, `ToolInfo`, `AgentUsageStats` TypeScript interfaces
- Added six `adminApi` methods: `listAgents`, `createAgent`, `updateAgent`, `deleteAgent`, `listAvailableTools`, `getAgentUsageStats`
- Follows existing adminApi patterns: PaginatedResponse handling, URLSearchParams for query params

### Task 2: Admin Agents Page, Modals, and Sidebar
- **Sidebar**: Added "Agents" nav item with Bot icon between Templates and Settings in Admin group
- **Create Agent Modal**: Full form with name, description, model dropdown (6 models across 3 providers), system prompt textarea (monospace, 12 rows), temperature, max iterations, tool checkboxes loaded from backend registry
- **Edit Agent Modal**: Same fields pre-populated from agent data, partial update (only changed fields sent), stale tool reference warnings (amber banner when agent has tools not in current registry)
- **Admin Agents Page**: Gold-accent header, 4 stats cards (total/active agents, total calls, cost), Button-based tab switching (Agents/Usage), agent table with name/description, model label, tool count badge, active/inactive status, edit/deactivate actions, inactive row dimming, usage table with per-agent breakdown and bold totals row, window.confirm for deactivation

## Verification

- Frontend `next build`: PASSED (all routes compile, /admin/agents listed)
- Backend `pytest`: 101 passed, 1 xfailed (no regressions)
- TypeScript `tsc --noEmit`: PASSED (zero errors)

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **AdminAgentConfig type name** -- used `AdminAgentConfig` instead of `AgentConfig` to avoid collision with any user-facing agent types
2. **MODEL_LABELS lookup map** -- hardcoded Record<string, string> in the page file for clean model ID to friendly name conversion in the agents table
3. **Stale tool warnings** -- edit modal shows amber warning banner when an agent's allowed_tool_names includes tools not found in the current registry (helps admins spot tool registry drift)
4. **Partial update optimization** -- edit modal compares current values against original agent data and only sends changed fields in the PATCH request
