# TMG Board Management Interface - Frontend Spec

**Status**: READY FOR APPROVAL
**Author**: Beth (Frontend)
**Collaborator**: Drew (Backend)
**Last Updated**: 2026-01-23

## Overview

Frontend for TMG Board Management Interface at tmgboard.themany.com. Elegant, simple board portal for The Many Group board members to access documents, track meetings, and participate in decisions.

## Tech Stack

Based on themany-forecasting patterns:

- **Framework**: Next.js 16+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Components**: Radix UI primitives + custom shadcn/ui-inspired library
- **Icons**: Lucide React
- **Auth**: NextAuth with Google OAuth
- **Data Fetching**: React Query or SWR (with 30-60s polling for updates)
- **Forms**: React Hook Form + Zod validation
- **PDF Viewing**: react-pdf (PDF.js wrapper) - client-side rendering
- **File Uploads**: S3 presigned URLs (direct upload from browser)

## Design Principles

1. **Clean & Professional** - Board members expect executive-level polish
2. **Minimal Clicks** - Quick access to common actions
3. **Mobile-Friendly** - Board members travel; responsive is essential
4. **Accessible** - Follow WCAG 2.1 AA guidelines
5. **Dark Theme** - Match themany-forecasting aesthetic

## User Roles & Access

| Role | Description | Access |
|------|-------------|--------|
| Board Member | Standard board participant | View docs, vote, sign, submit ideas |
| Board Chair | Meeting leadership | + Schedule meetings, manage agenda |
| Admin | System administration | + Manage members, upload docs, full control |

## Core Screens

### 1. Login Page

Simple Google OAuth login, matching themany-forecasting pattern.

```
┌─────────────────────────────────────────┐
│                                         │
│         TMG Board Portal               │
│         ───────────────                │
│                                         │
│    ┌────────────────────────────┐      │
│    │  Sign in with Google       │      │
│    └────────────────────────────┘      │
│                                         │
│    Authorized board members only       │
│                                         │
└─────────────────────────────────────────┘
```

**Behavior**:
- Redirect if already authenticated
- Show error for unauthorized emails
- Clean, centered card layout

### 2. Dashboard (Home)

Primary landing page after login. Shows overview and quick actions.

```
┌──────────────────────────────────────────────────────────┐
│ [Logo] TMG Board              [User Menu ▼]              │
├─────────┬────────────────────────────────────────────────┤
│         │                                                │
│ Dashboard│  Welcome, [Name]                              │
│ Documents│  ─────────────────                            │
│ Meetings │                                               │
│ Decisions│  ┌──────────────┐ ┌──────────────┐           │
│ Ideas    │  │ Next Meeting │ │ Pending Sigs │           │
│          │  │ Jan 28, 2pm  │ │     3        │           │
│ ─────────│  └──────────────┘ └──────────────┘           │
│ Admin    │                                               │
│ (if admin)│  ┌──────────────┐ ┌──────────────┐           │
│          │  │ Open Votes   │ │ New Ideas    │           │
│          │  │     2        │ │     5        │           │
│          │  └──────────────┘ └──────────────┘           │
│          │                                               │
│          │  Recent Documents                            │
│          │  ────────────────                            │
│          │  • 2026 Q1 Budget Report         [View]     │
│          │  • January Meeting Minutes       [Sign]     │
│          │  • Resolution 2026-001          [Signed]   │
│          │                                               │
└─────────┴────────────────────────────────────────────────┘
```

**Components**:
- `<KPICard>` - Stat cards for quick metrics
- `<RecentDocuments>` - List with status badges
- `<UpcomingMeetings>` - Calendar preview

### 3. Document Repository

Central document hub with filtering and organization.

```
┌──────────────────────────────────────────────────────────┐
│ Documents                           [+ Upload] (admin)   │
│ ─────────                                                │
│                                                          │
│ [All ▼] [2026 ▼] [Search...]                            │
│                                                          │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Type         │ Title              │ Date    │Status│  │
│ ├──────────────┼────────────────────┼─────────┼──────┤  │
│ │ Resolution   │ 2026-001 Budget    │ Jan 15  │Signed│  │
│ │ Minutes      │ January Meeting    │ Jan 10  │Draft │  │
│ │ Report       │ Q4 2025 Financials │ Jan 5   │Final │  │
│ │ Consent      │ Officer Elections  │ Jan 3   │Pending│  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ Showing 1-10 of 45                    [< 1 2 3 4 5 >]   │
└──────────────────────────────────────────────────────────┘
```

**Document Types** (with icons/colors):
- Resolutions (blue)
- Meeting Minutes (green)
- Financial Reports (amber)
- Consent Documents (purple)
- Legal Documents (red)

**Features**:
- Filter by type, year, status
- Search by title
- Sort by date, type, status
- Click to view/download
- Signature status badges
- Admin: Upload button

### 4. Document Detail View

Individual document with metadata and actions.

```
┌──────────────────────────────────────────────────────────┐
│ ← Back to Documents                                      │
│                                                          │
│ Resolution 2026-001: Annual Budget Approval              │
│ ───────────────────────────────────────────              │
│                                                          │
│ Status: [Pending Signatures]     Type: Resolution        │
│ Uploaded: Jan 15, 2026           By: John Smith         │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐│
│ │                                                      ││
│ │              [PDF Preview / Viewer]                  ││
│ │                                                      ││
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ [Download PDF]  [Sign Document]                          │
│                                                          │
│ Signature Status                                         │
│ ────────────────                                         │
│ • Jane Doe        ✓ Signed Jan 16                       │
│ • John Smith      ⏳ Pending                             │
│ • You             [Sign Now]                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Features**:
- PDF preview (embedded viewer)
- Download button
- DocuSign status per signer
- Sign button (redirects to DocuSign)
- Version history (collapsible)
- Access log (admin only)

### 5. Meetings

Calendar view and meeting management.

```
┌──────────────────────────────────────────────────────────┐
│ Meetings                        [+ Schedule] (chair)     │
│ ─────────                                                │
│                                                          │
│ [Calendar] [List]                [2026 ▼] [January ▼]   │
│                                                          │
│        January 2026                                      │
│  Su  Mo  Tu  We  Th  Fr  Sa                             │
│               1   2   3   4                              │
│   5   6   7   8   9  10  11                             │
│  12  13  14  15  16  17  18                             │
│  19  20  21  22  23  24  25                             │
│  26  27 [28] 29  30  31                                 │
│                                                          │
│ Upcoming                                                 │
│ ────────                                                 │
│ • Jan 28, 2:00 PM - Q1 Board Meeting     [View Agenda]  │
│ • Mar 15, 2:00 PM - Annual Meeting       [View]         │
│                                                          │
│ Past Meetings                                            │
│ ─────────────                                            │
│ • Jan 10 - January Board Meeting         [Minutes]      │
│ • Dec 12 - December Board Meeting        [Minutes]      │
└──────────────────────────────────────────────────────────┘
```

**Features**:
- Calendar and list view toggle
- Meeting details on click
- Agenda items list
- Link to minutes
- Meeting recordings (if available)
- Chair: Schedule/edit meetings

### 6. Meeting Detail

Single meeting with agenda and documents.

```
┌──────────────────────────────────────────────────────────┐
│ ← Back to Meetings                                       │
│                                                          │
│ Q1 Board Meeting                                         │
│ ────────────────                                         │
│ Date: January 28, 2026 at 2:00 PM                       │
│ Location: Virtual (Zoom)        [Join Meeting]          │
│ Status: Scheduled                                        │
│                                                          │
│ Agenda                          [+ Add Item] (chair)     │
│ ──────                                                   │
│ 1. Call to Order                          5 min         │
│ 2. Approval of Previous Minutes           5 min         │
│ 3. Financial Report - Jane Doe           15 min         │
│ 4. 2026 Budget Discussion                30 min         │
│    └─ Related: Resolution 2026-001                      │
│ 5. New Business                          15 min         │
│ 6. Adjournment                                          │
│                                                          │
│ Documents                                                │
│ ─────────                                                │
│ • Q4 2025 Financial Report                              │
│ • 2026 Proposed Budget                                  │
│                                                          │
│ Recording                                                │
│ ─────────                                                │
│ [Not yet available]                                      │
└──────────────────────────────────────────────────────────┘
```

### 7. Decisions & Voting

Track decisions and participate in votes.

```
┌──────────────────────────────────────────────────────────┐
│ Decisions                       [+ New Decision] (chair) │
│ ─────────                                                │
│                                                          │
│ [Open] [Closed] [All]                                    │
│                                                          │
│ Open Votes (2)                                           │
│ ────────────                                             │
│ ┌──────────────────────────────────────────────────────┐│
│ │ Approve 2026 Budget                    Closes Jan 30 ││
│ │ Resolution requiring board approval                   ││
│ │ Your vote: [Not yet cast]                            ││
│ │                                    [Cast Vote →]      ││
│ └──────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────┐│
│ │ Officer Elections                      Closes Feb 1  ││
│ │ Annual election of board officers                    ││
│ │ Your vote: ✓ Cast                                    ││
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ Recent Decisions                                         │
│ ────────────────                                         │
│ • Q4 Dividend Approval - Passed (5-0)                   │
│ • Committee Appointments - Passed (4-1)                 │
└──────────────────────────────────────────────────────────┘
```

### 8. Vote Detail / Casting

```
┌──────────────────────────────────────────────────────────┐
│ ← Back to Decisions                                      │
│                                                          │
│ Approve 2026 Budget                                      │
│ ────────────────────                                     │
│ Type: Resolution          Status: Open                   │
│ Deadline: January 30, 2026                              │
│                                                          │
│ Description                                              │
│ ───────────                                              │
│ Approval of the proposed 2026 operating budget as       │
│ presented in the Q1 Board Meeting materials.            │
│                                                          │
│ Related Documents                                        │
│ • 2026 Proposed Budget                                  │
│ • Budget Presentation Slides                            │
│                                                          │
│ Cast Your Vote                                           │
│ ──────────────                                           │
│                                                          │
│ [ Yes ]    [ No ]    [ Abstain ]                        │
│                                                          │
│ Current Results (visible after voting or to admin)      │
│ ───────────────                                          │
│ Yes: 3  |  No: 0  |  Abstain: 1  |  Pending: 2         │
└──────────────────────────────────────────────────────────┘
```

### 9. Ideas Backlog

Submit and discuss ideas for board consideration.

```
┌──────────────────────────────────────────────────────────┐
│ Ideas                                   [+ Submit Idea]  │
│ ─────                                                    │
│                                                          │
│ [New] [Under Review] [Approved] [All]                   │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐│
│ │ Expand to European Markets           [Under Review]  ││
│ │ Submitted by: Jane Doe on Jan 5                      ││
│ │ Consider establishing EU subsidiary...               ││
│ │ 💬 3 comments                         [View →]       ││
│ └──────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────┐│
│ │ Quarterly Town Halls                        [New]    ││
│ │ Submitted by: John Smith on Jan 3                    ││
│ │ Propose regular all-hands meetings...               ││
│ │ 💬 0 comments                         [View →]       ││
│ └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

### 10. Idea Detail

```
┌──────────────────────────────────────────────────────────┐
│ ← Back to Ideas                                          │
│                                                          │
│ Expand to European Markets                               │
│ ──────────────────────────                               │
│ Status: Under Review          Submitted: Jan 5, 2026    │
│ By: Jane Doe                                             │
│                                                          │
│ Description                                              │
│ ───────────                                              │
│ I propose we consider establishing a subsidiary in      │
│ the European Union to expand our market presence...     │
│                                                          │
│ [Promote to Decision] (chair/admin)                      │
│                                                          │
│ Discussion (3)                                           │
│ ──────────────                                           │
│ ┌──────────────────────────────────────────────────────┐│
│ │ John Smith - Jan 6                                   ││
│ │ Great idea. We should research regulatory...         ││
│ └──────────────────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────────────────┐│
│ │ You - Jan 7                                          ││
│ │ I agree. What timeline are you thinking?             ││
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ [Add Comment]                                            │
└──────────────────────────────────────────────────────────┘
```

### 11. Admin: User Management

Admin-only screen for managing board members.

```
┌──────────────────────────────────────────────────────────┐
│ User Management                         [+ Add Member]   │
│ ───────────────                                          │
│                                                          │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Name           │ Email              │ Role   │     │  │
│ ├────────────────┼────────────────────┼────────┼─────┤  │
│ │ Jane Doe       │ jane@example.com   │ Admin  │ [⋮] │  │
│ │ John Smith     │ john@example.com   │ Chair  │ [⋮] │  │
│ │ Alice Johnson  │ alice@example.com  │ Member │ [⋮] │  │
│ │ Bob Williams   │ bob@example.com    │ Member │ [⋮] │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ Pending Invites                                          │
│ ───────────────                                          │
│ • newmember@example.com (invited Jan 20)   [Resend]     │
└──────────────────────────────────────────────────────────┘
```

## Component Library

### From themany-forecasting (reuse)
- Button, Input, Label, Select
- Dialog, Card, Table
- DropdownMenu, Tabs
- Sidebar navigation pattern
- Loading spinners, skeletons
- Toast notifications

### New Components Needed
- `<PDFViewer>` - Embedded document viewer
- `<CalendarView>` - Month/week calendar display
- `<VoteButtons>` - Yes/No/Abstain voting UI
- `<StatusBadge>` - Document/vote status indicators
- `<CommentThread>` - Discussion comments display
- `<SignatureStatus>` - DocuSign signer list

## Navigation Structure

```
Sidebar:
├── Dashboard (home icon)
├── Documents (file icon)
├── Meetings (calendar icon)
├── Decisions (check-square icon)
├── Ideas (lightbulb icon)
├── ─────────
└── Admin (if admin)
    ├── Users (users icon)
    └── Settings (settings icon)
```

## Responsive Behavior

**Desktop (1024px+)**:
- Fixed sidebar (264px)
- Full feature set

**Tablet (768-1023px)**:
- Collapsible sidebar
- Stacked cards instead of grid

**Mobile (<768px)**:
- Bottom navigation or hamburger menu
- Single column layout
- Simplified tables (card view)

## Technical Decisions (Resolved with Drew)

| Question | Decision | Rationale |
|----------|----------|-----------|
| Real-time Updates | Polling (30-60s) | Simple for MVP, ~10 board members. WebSockets later if needed. |
| PDF Viewing | Client-side PDF.js (react-pdf) | Keeps backend simple, just serves files. |
| Email Notifications | Frontend calls API only | Backend handles queuing. Optional /api/notifications for pending. |
| Calendar Sync | "Add to Google Calendar" button | Generate gcal URL with meeting details. No API integration. |
| Offline Access | Skip for MVP | Service workers add complexity. Board members have connectivity. |
| File Uploads | S3 presigned URLs | Request URL from backend, upload directly, confirm when done. |
| Meeting Recordings | Link to Zoom/Google | Embedding is complex, just link out. |
| Document Annotations | Skip for MVP | Keep it simple. |
| Mobile App | PWA sufficient | Native later if needed. |
| Audit Log UI | Yes, for admins | Backend will expose /api/admin/audit endpoint. |

## Implementation Order

Phase 1 - Core Auth & Navigation:
1. [ ] Project setup (Next.js, Tailwind, components)
2. [ ] Google Auth login flow
3. [ ] App shell with sidebar navigation
4. [ ] Dashboard skeleton

Phase 2 - Documents:
5. [ ] Document list with filtering
6. [ ] Document detail view
7. [ ] PDF viewer integration
8. [ ] DocuSign status display

Phase 3 - Meetings:
9. [ ] Meeting list view
10. [ ] Calendar view
11. [ ] Meeting detail with agenda
12. [ ] Chair: meeting scheduling

Phase 4 - Decisions:
13. [ ] Decision list
14. [ ] Vote casting UI
15. [ ] Results display

Phase 5 - Ideas & Admin:
16. [ ] Ideas list and detail
17. [ ] Comment threads
18. [ ] Admin user management

Phase 6 - Polish:
19. [ ] Mobile responsive
20. [ ] Loading states everywhere
21. [ ] Error handling
22. [ ] Accessibility audit

---

## Approval

**Frontend Spec**: Ready for approval - Beth
**Backend Spec**: Ready for approval - Drew (see BACKEND_SPEC.md)

Once approved, we can begin implementation with coordinated phases.
