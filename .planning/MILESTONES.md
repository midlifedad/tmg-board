# Milestones — TMG Board

## v1.0 Meetings UX Redesign (Complete)

**Completed:** 2026-03-04
**Phases:** 2 (Design Discovery, Implementation)
**PRs:** #41-51

### What Shipped
- Dynamic org branding (logo, name, colors configurable by admin)
- Meetings list page redesign (enriched cards, status indicators, iPad-friendly)
- Meeting detail page redesign (time slots, type-colored borders, inline edit, drag reorder)
- Backend: item_type on agenda items, presenter tracking, duration calculations
- Document download with auth headers, PDF viewer (react-pdf v10)
- Timezone support across meetings
- Session race condition fixes across all pages
- Presenter field fix (member dropdown with backend FK)

### Key Learnings
- react-pdf v10 transfers ArrayBuffers to Web Workers (detaches them) — use Blob URLs instead
- NextAuth session loads async — guard all API calls with `if (!email) return`
- CSS import paths changed in react-pdf v10 with Turbopack (`dist/Page/` not `dist/esm/Page/`)
