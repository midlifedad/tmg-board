---
phase: 04-board-resolutions-resolution-writer
plan: 03
subsystem: frontend-resolutions
tags: [resolutions, signatures, sidebar, print, agent-integration]
dependency_graph:
  requires: [04-01]
  provides: [resolutions-ui, signature-panel, resolution-writer-component]
  affects: [sidebar, decisions-page, permissions]
tech_stack:
  added: []
  patterns: [useAgentStream-agent-invocation, CSS-print-styles, signature-panel]
key_files:
  created:
    - frontend/src/app/resolutions/page.tsx
    - frontend/src/app/resolutions/[id]/page.tsx
    - frontend/src/components/signature-panel.tsx
    - frontend/src/components/resolution-writer.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/sidebar.tsx
    - frontend/src/app/decisions/page.tsx
    - frontend/src/lib/permissions.ts
decisions:
  - "ResolutionDetailResponse extends DecisionDetail for resolution_number field access"
  - "isChairOrAbove added to permissions.ts for print button visibility gate"
  - "Gold accent styling on sign and generate buttons matching app theme"
metrics:
  duration: 4min
  completed: "2026-03-05T02:37:24Z"
---

# Phase 04 Plan 03: Frontend Resolutions UI Summary

Dedicated resolutions section with sidebar navigation, list/detail pages, signature panel with digital sign flow, printable export via CSS @media print, and inline Resolution Writer agent component.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | API client, sidebar, and resolutions list page | 92f5e41 | api.ts, sidebar.tsx, resolutions/page.tsx, decisions/page.tsx |
| 2 | Resolution detail with signature panel, print, and Resolution Writer | 946640f | resolutions/[id]/page.tsx, signature-panel.tsx, resolution-writer.tsx, permissions.ts |

## What Was Built

### Resolutions API Client (api.ts)
- `resolutionsApi.list()` -- fetches resolution-type decisions with signature counts
- `resolutionsApi.get()` -- fetches resolution detail (extends DecisionDetail)
- `resolutionsApi.getSignatures()` -- fetches signature status for all board members
- `resolutionsApi.sign()` -- records digital signature on a resolution
- Types: `ResolutionSignature`, `SignatureStatus`, `ResolutionListItem`

### Sidebar Navigation (sidebar.tsx)
- Added `Stamp` icon import from lucide-react
- Added "Resolutions" nav item after "Decisions" in the Main group
- Visible to all board+ users via existing `visibleTo: "board"` group

### Resolutions List Page (/resolutions)
- AppShell wrapper with gold accent header ("Board resolutions and digital signatures")
- Filter tabs: All, Open, Closed with counts
- Resolution cards show: type badge, status badge, resolution_number, title, description
- Signature progress: "{count}/{total} signed" with green progress bar
- Loading state (Loader2 spinner), error state with retry

### Resolution Detail Page (/resolutions/[id])
- Two-column layout: content (lg:col-span-2) + sidebar (lg:col-span-1)
- Back link to /resolutions, gold accent header, status badge, resolution number
- Description rendered as HTML with prose-invert styling
- Signature panel in right column
- Print button visible to chair/admin only (isChairOrAbove gate)
- Resolution Writer agent component always visible in left column
- Sign success feedback auto-dismisses after 3 seconds
- Print styles: hidden screen UI, formal document with signatures table

### Signature Panel (signature-panel.tsx)
- Displays all board members with signature status
- Signed members: green CheckCircle + date
- Unsigned members: "Pending" in muted text
- "Sign Resolution" button with gold accent styling (only when resolution is closed and user hasn't signed)
- Loader2 spinner during signing
- "You have signed this resolution" confirmation after signing

### Resolution Writer (resolution-writer.tsx)
- Follows MinutesGenerator pattern exactly
- Uses useAgentStream hook to invoke "resolution-writer" agent
- "Draft Resolution Document" trigger button with gold accent
- Streaming output: thinking indicator, tool call status, markdown rendering
- Actions: Generate Again, Dismiss, Cancel

### Decisions Page Filter (decisions/page.tsx)
- Added `data.filter(d => d.type !== "resolution")` in both initial fetch and refetch
- Resolutions no longer appear in /decisions

### Permissions (permissions.ts)
- Added `isChairOrAbove()` function: returns true for chair or admin roles

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added isChairOrAbove to permissions.ts**
- **Found during:** Task 2
- **Issue:** Plan references `isChairOrAbove` but it didn't exist in permissions.ts
- **Fix:** Added the function alongside existing `isBoardOrAbove` and `isAdmin`
- **Files modified:** frontend/src/lib/permissions.ts
- **Commit:** 946640f

**2. [Rule 1 - Bug] Fixed TypeScript type for resolution_number access**
- **Found during:** Task 2 build verification
- **Issue:** `Decision` type doesn't include `resolution_number`; casting to `Record<string, unknown>` failed TS strict check
- **Fix:** Created `ResolutionDetailResponse` interface extending `DecisionDetail` with `resolution_number` field
- **Files modified:** frontend/src/app/resolutions/[id]/page.tsx
- **Commit:** 946640f

## Verification

- `npx next build` succeeds with no errors
- `/resolutions` route listed as static page
- `/resolutions/[id]` route listed as dynamic page
- Sidebar shows Resolutions entry with Stamp icon
- Decisions page filters out resolution-type items
- Print button gated by isChairOrAbove permission check
