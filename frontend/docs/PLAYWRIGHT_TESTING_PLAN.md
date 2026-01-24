# Playwright Testing Plan - TMG Board Portal

## Overview

This document outlines the comprehensive Playwright testing plan for all frontend features. Each section includes checkpoints to verify functionality after the backend PRs (#11) and frontend PR (#12) are merged.

## Prerequisites

Before running tests:
1. Ensure PRs #11 (backend) and #12 (frontend) are merged to staging
2. Start the development server: `npm run dev`
3. Ensure backend is running with test data seeded
4. Have test users created for each role: admin, chair, member

## Test Environment Setup

```bash
# Install Playwright
npx playwright install

# Run tests
npx playwright test

# Run with UI
npx playwright test --ui
```

---

## 1. Authentication & Navigation

### 1.1 Login Flow
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| AUTH-01 | Navigate to login page | Login form displays |
| AUTH-02 | Login with valid credentials | Redirect to dashboard |
| AUTH-03 | Login with invalid credentials | Error message shown |
| AUTH-04 | Logout from authenticated session | Redirect to login |

### 1.2 Navigation
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| NAV-01 | Click Dashboard in sidebar | Dashboard page loads |
| NAV-02 | Click Documents in sidebar | Documents list loads |
| NAV-03 | Click Meetings in sidebar | Meetings list loads |
| NAV-04 | Click Decisions in sidebar | Decisions list loads |
| NAV-05 | Click Ideas in sidebar | Ideas list loads |
| NAV-06 | Click Admin (as admin user) | Admin page loads |
| NAV-07 | Admin menu hidden for member role | No Admin option in sidebar |

---

## 2. Documents Page

### 2.1 Document List
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DOC-01 | Navigate to /documents | Document list displays |
| DOC-02 | Filter by document type | Filtered results shown |
| DOC-03 | Search documents | Search results displayed |
| DOC-04 | Click document row | Navigate to detail page |

### 2.2 Document Detail
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DOC-05 | View document detail page | Title, type, metadata shown |
| DOC-06 | See signature status panel | Signers and status displayed |
| DOC-07 | Click "Download PDF" | File downloads |
| DOC-08 | Expand version history | Version list appears |
| DOC-09 | Download specific version | Correct version downloads |

### 2.3 Document CRUD (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DOC-10 | Click "Upload Document" | Upload modal opens |
| DOC-11 | Upload new document | Document appears in list |
| DOC-12 | Click "Edit" on document | Edit modal opens |
| DOC-13 | Update document metadata | Changes saved, UI updated |
| DOC-14 | Click "New Version" | Upload version modal opens |
| DOC-15 | Upload new version | Version appears in history |
| DOC-16 | Click "Archive" | Document archived, badge shown |
| DOC-17 | Click "Restore" on archived | Document unarchived |

### 2.4 Permissions Check
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DOC-18 | Member views document | Can view, no edit buttons |
| DOC-19 | Chair views document | Edit/Upload buttons visible |
| DOC-20 | Admin views document | All actions available |

---

## 3. Meetings Page

### 3.1 Meeting List
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| MTG-01 | Navigate to /meetings | Meeting list displays |
| MTG-02 | See upcoming meetings tab | Future meetings shown |
| MTG-03 | See past meetings tab | Historical meetings shown |
| MTG-04 | Click meeting row | Navigate to detail page |

### 3.2 Meeting CRUD (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| MTG-05 | Click "Schedule Meeting" | Create modal opens |
| MTG-06 | Fill form with in-person location | Location field visible |
| MTG-07 | Toggle to virtual meeting | Meeting link field visible |
| MTG-08 | Submit create form | Meeting appears in list |
| MTG-09 | Click "Edit" on meeting | Edit modal opens |
| MTG-10 | Update meeting details | Changes saved |
| MTG-11 | Cancel a meeting | Meeting marked cancelled |

### 3.3 Meeting Detail
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| MTG-12 | View meeting detail | All info displayed |
| MTG-13 | See agenda section | Agenda items listed |
| MTG-14 | See attendees section | Attendee list shown |

### 3.4 Agenda Management (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| MTG-15 | Click "Add Item" | Add form appears |
| MTG-16 | Fill and submit agenda item | Item added to list |
| MTG-17 | Click edit on agenda item | Edit form appears |
| MTG-18 | Update agenda item | Changes saved |
| MTG-19 | Click up arrow to reorder | Item moves up |
| MTG-20 | Click down arrow to reorder | Item moves down |
| MTG-21 | Delete agenda item | Item removed |

### 3.5 Meeting Lifecycle (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| MTG-22 | Click "Start Meeting" | Status changes to in_progress |
| MTG-23 | Take attendance | Attendance recorded |
| MTG-24 | Click "End Meeting" | Status changes to completed |

---

## 4. Decisions Page

### 4.1 Decision List
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DEC-01 | Navigate to /decisions | Decision list displays |
| DEC-02 | See open decisions | Open votes highlighted |
| DEC-03 | See closed decisions | Past decisions shown |
| DEC-04 | Filter by status | Filtered results |

### 4.2 Decision CRUD (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DEC-05 | Click "New Decision" | Create modal opens |
| DEC-06 | Select vote type | Radio button selected |
| DEC-07 | Select consent type | Radio button selected |
| DEC-08 | Select resolution type | Radio button selected |
| DEC-09 | Set voting deadline | Date saved |
| DEC-10 | Submit decision | Decision created, status open |
| DEC-11 | Click "Edit" | Edit modal opens |
| DEC-12 | Update decision | Changes saved |

### 4.3 Voting
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DEC-13 | Navigate to open decision | Vote buttons visible |
| DEC-14 | Click "Yes" vote | Vote recorded, UI updates |
| DEC-15 | Click "No" vote | Vote recorded, UI updates |
| DEC-16 | Click "Abstain" vote | Vote recorded, UI updates |
| DEC-17 | See live vote tally | Results update |

### 4.4 Decision Lifecycle (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| DEC-18 | Close voting | Status changes to closed |
| DEC-19 | See final results | Pass/fail determined |
| DEC-20 | Reopen voting | Status changes to open |
| DEC-21 | Archive decision | Decision archived |

---

## 5. Ideas Page

### 5.1 Idea List
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| IDEA-01 | Navigate to /ideas | Idea list displays |
| IDEA-02 | Filter by status | Filtered results |
| IDEA-03 | Click idea row | Navigate to detail |

### 5.2 Submit Idea (All Users)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| IDEA-04 | Click "Submit Idea" | Modal opens |
| IDEA-05 | Fill title and description | Form validates |
| IDEA-06 | Submit idea | Idea appears with "New" status |

### 5.3 Idea Detail
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| IDEA-07 | View idea detail | Title, description, status |
| IDEA-08 | See comments section | Comments displayed |
| IDEA-09 | Add comment | Comment appears |

### 5.4 Idea Moderation (Admin/Chair)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| IDEA-10 | Click "Edit" | Edit modal opens |
| IDEA-11 | Update idea | Changes saved |
| IDEA-12 | Change status to "Under Review" | Status badge updates |
| IDEA-13 | Change status to "Approved" | Status badge updates |
| IDEA-14 | Change status to "Rejected" | Status badge updates |
| IDEA-15 | Click "Promote to Decision" | Decision created, idea status = promoted |

---

## 6. Admin Pages

### 6.1 User Management (Admin Only)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| ADMIN-01 | Navigate to /admin/users | User list displays |
| ADMIN-02 | Click "Invite User" | Invite modal opens |
| ADMIN-03 | Fill email and role | Form validates |
| ADMIN-04 | Submit invitation | Invitation sent |
| ADMIN-05 | Click user row | User detail shown |
| ADMIN-06 | Change user role | Role updated |
| ADMIN-07 | Deactivate user | User deactivated |

### 6.2 Settings (Admin Only)
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| ADMIN-08 | Navigate to /admin/settings | Settings tabs display |
| ADMIN-09 | View Organization tab | Org settings shown |
| ADMIN-10 | Update organization name | Changes saved |
| ADMIN-11 | View Permissions tab | Role matrix displayed |
| ADMIN-12 | Toggle permission | Permission updated |
| ADMIN-13 | View Integrations tab | Integration options shown |

### 6.3 Access Control
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| ADMIN-14 | Member navigates to /admin | Redirected or 403 |
| ADMIN-15 | Chair navigates to /admin | Limited access |
| ADMIN-16 | Admin navigates to /admin | Full access |

---

## 7. Cross-Feature Tests

### 7.1 Meeting + Decision Integration
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| CROSS-01 | Create decision linked to meeting | Decision shows meeting link |
| CROSS-02 | View meeting agenda with decision | Decision item highlighted |

### 7.2 Idea + Decision Flow
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| CROSS-03 | Promote idea to decision | Decision created from idea |
| CROSS-04 | Original idea shows "Promoted" | Status updated |

### 7.3 Document + Signature
| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| CROSS-05 | Send document for signature | DocuSign flow initiates |
| CROSS-06 | Check signature status | Status updates shown |

---

## 8. Error Handling

| Checkpoint | Test Description | Expected Result |
|------------|------------------|-----------------|
| ERR-01 | Submit empty required field | Validation error shown |
| ERR-02 | Network error during submit | Error toast displayed |
| ERR-03 | 403 on unauthorized action | Permission denied message |
| ERR-04 | 404 on invalid resource | Not found page shown |

---

## Test Execution Checklist

### Pre-merge Testing
- [ ] Run TypeScript compilation: `npx tsc --noEmit`
- [ ] Run linter: `npm run lint`
- [ ] Build succeeds: `npm run build`

### Post-merge Testing (Staging)
- [ ] Complete all AUTH checkpoints
- [ ] Complete all NAV checkpoints
- [ ] Complete all DOC checkpoints
- [ ] Complete all MTG checkpoints
- [ ] Complete all DEC checkpoints
- [ ] Complete all IDEA checkpoints
- [ ] Complete all ADMIN checkpoints
- [ ] Complete all CROSS checkpoints
- [ ] Complete all ERR checkpoints

### Role-based Testing
- [ ] Run all tests as admin user
- [ ] Run permission checks as chair user
- [ ] Run permission checks as member user

---

## Notes

- All timestamps should display in user's local timezone
- Loading states should show spinners, not blank screens
- Error messages should be user-friendly, not technical
- Forms should disable submit while processing
- Modals should close on backdrop click (when not submitting)
