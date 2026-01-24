# TMG Board Portal - Backend Requirements for Full CRUD & RBAC

**Prepared by:** Beth (Frontend)
**Date:** 2026-01-24
**For coordination with:** Drew (Backend)

## Executive Summary

This document consolidates all backend requirements needed to support a full-featured board management portal with:
- Complete CRUD operations on all entities
- Role-based access control (RBAC) with granular permissions
- Comprehensive audit trail
- User management and invitation system

---

## 1. New Database Tables Required

### 1.1 Admin & RBAC Tables

```sql
-- Invitations (pending board member invites)
CREATE TABLE invitations (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    invited_by_id INTEGER REFERENCES board_members(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    message TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP
);

-- Permissions (granular permission definitions)
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,  -- e.g., 'documents.upload'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL
);

-- Role Permissions (many-to-many)
CREATE TABLE role_permissions (
    role VARCHAR(20) NOT NULL,
    permission_id INTEGER REFERENCES permissions(id),
    PRIMARY KEY (role, permission_id)
);

-- Settings (key-value store)
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER REFERENCES board_members(id)
);

-- User sessions (for tracking last login)
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES board_members(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

### 1.2 Document Enhancement Tables

```sql
-- Document versions
CREATE TABLE document_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) NOT NULL,
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_by_id INTEGER REFERENCES board_members(id) NOT NULL,
    upload_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version_number)
);

-- Related documents (many-to-many)
CREATE TABLE related_documents (
    document_id INTEGER REFERENCES documents(id),
    related_document_id INTEGER REFERENCES documents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, related_document_id)
);
```

### 1.3 Meeting Enhancement Tables

```sql
-- Meeting notes (per agenda item or general)
CREATE TABLE meeting_notes (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) NOT NULL,
    agenda_item_id INTEGER REFERENCES agenda_items(id),  -- NULL for general notes
    content TEXT NOT NULL,
    created_by_id INTEGER REFERENCES board_members(id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Meeting templates
CREATE TABLE meeting_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_duration_minutes INTEGER,
    agenda_template JSONB,  -- [{title, duration, order}]
    created_by_id INTEGER REFERENCES board_members(id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Meeting attendance
CREATE TABLE meeting_attendance (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) NOT NULL,
    member_id INTEGER REFERENCES board_members(id) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- present, absent, excused
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(meeting_id, member_id)
);

-- Action items (from meetings)
CREATE TABLE action_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) NOT NULL,
    agenda_item_id INTEGER REFERENCES agenda_items(id),
    title VARCHAR(255) NOT NULL,
    assignee_id INTEGER REFERENCES board_members(id),
    due_date DATE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 1.4 Ideas Enhancement Tables

```sql
-- Idea categories
CREATE TABLE idea_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(7) NOT NULL  -- hex color
);

-- Idea history (change tracking)
CREATE TABLE idea_history (
    id SERIAL PRIMARY KEY,
    idea_id INTEGER REFERENCES ideas(id) NOT NULL,
    field_changed VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by_id INTEGER REFERENCES board_members(id) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comment reactions
CREATE TABLE comment_reactions (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER REFERENCES comments(id) NOT NULL,
    user_id INTEGER REFERENCES board_members(id) NOT NULL,
    reaction_type VARCHAR(20) NOT NULL,  -- thumbs_up, lightbulb, heart, warning
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comment_id, user_id, reaction_type)
);
```

### 1.5 Decision Enhancement Tables

```sql
-- Decision comments (threaded discussion)
CREATE TABLE decision_comments (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id) NOT NULL,
    parent_id INTEGER REFERENCES decision_comments(id),  -- For threading
    user_id INTEGER REFERENCES board_members(id) NOT NULL,
    content TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP  -- Soft delete
);
```

---

## 2. Existing Table Modifications

### 2.1 Documents Table
```sql
ALTER TABLE documents ADD COLUMN archived_at TIMESTAMP;
ALTER TABLE documents ADD COLUMN archived_by_id INTEGER REFERENCES board_members(id);
```

### 2.2 Meetings Table
```sql
ALTER TABLE meetings ADD COLUMN duration_minutes INTEGER;
ALTER TABLE meetings ADD COLUMN started_at TIMESTAMP;
ALTER TABLE meetings ADD COLUMN ended_at TIMESTAMP;
ALTER TABLE meetings ADD COLUMN recording_url TEXT;
```

### 2.3 Agenda Items Table
```sql
ALTER TABLE agenda_items ADD COLUMN time_allocation_minutes INTEGER;
ALTER TABLE agenda_items ADD COLUMN presenter_id INTEGER REFERENCES board_members(id);
ALTER TABLE agenda_items ADD COLUMN decision_id INTEGER REFERENCES decisions(id);
ALTER TABLE agenda_items ADD COLUMN document_ids JSONB DEFAULT '[]';
```

### 2.4 Ideas Table
```sql
ALTER TABLE ideas ADD COLUMN category_id INTEGER REFERENCES idea_categories(id);
ALTER TABLE ideas ADD COLUMN promoted_to_decision_id INTEGER REFERENCES decisions(id);
```

### 2.5 Comments Table
```sql
ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id);
ALTER TABLE comments ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE;
ALTER TABLE comments ADD COLUMN edited_at TIMESTAMP;
```

### 2.6 Decisions Table
```sql
ALTER TABLE decisions ADD COLUMN visibility VARCHAR(20) DEFAULT 'standard';  -- standard, anonymous, transparent
ALTER TABLE decisions ADD COLUMN archived_at TIMESTAMP;
ALTER TABLE decisions ADD COLUMN archived_reason TEXT;
```

### 2.7 Audit Log Table
```sql
ALTER TABLE audit_log ADD COLUMN ip_address VARCHAR(45);
ALTER TABLE audit_log ADD COLUMN user_agent TEXT;
ALTER TABLE audit_log ADD COLUMN entity_name VARCHAR(255);
```

---

## 3. New API Endpoints Required

### 3.1 Admin - User Management
```
GET    /api/admin/users              # List all users (with last_login)
GET    /api/admin/users/{id}         # Get user details
POST   /api/admin/users/invite       # Send invitation
PATCH  /api/admin/users/{id}         # Update user (role, status)
DELETE /api/admin/users/{id}         # Deactivate user (soft delete)
POST   /api/admin/users/{id}/restore # Reactivate user
GET    /api/admin/invites            # List pending invites
POST   /api/admin/invites/{id}/resend # Resend invite
DELETE /api/admin/invites/{id}       # Cancel invite
```

### 3.2 Admin - Roles & Permissions
```
GET    /api/admin/roles              # List all roles with user counts
GET    /api/admin/roles/{name}       # Get role with permissions
PATCH  /api/admin/roles/{name}       # Update role permissions
GET    /api/admin/permissions        # Get full permission matrix
PATCH  /api/admin/permissions        # Bulk update permissions
```

### 3.3 Admin - Audit Trail
```
GET    /api/admin/audit              # List audit entries (paginated)
       ?user_id=&action=&entity_type=&start_date=&end_date=
GET    /api/admin/audit/export       # Export as CSV
```

### 3.4 Admin - Settings
```
GET    /api/admin/settings           # Get all settings
PATCH  /api/admin/settings           # Update settings
POST   /api/admin/settings/logo      # Upload logo
DELETE /api/admin/settings/logo      # Remove logo
```

### 3.5 Documents - Enhancements
```
GET    /api/documents/{id}/versions  # List document versions
POST   /api/documents/{id}/versions  # Upload new version
GET    /api/documents/{id}/activity  # Get document activity log
POST   /api/documents/{id}/archive   # Archive document
POST   /api/documents/{id}/unarchive # Unarchive document
GET    /api/documents/archived       # List archived documents
POST   /api/documents/{id}/related   # Link related documents
DELETE /api/documents/{id}/related/{relatedId} # Unlink
POST   /api/documents/{id}/reminder  # Send signature reminder
POST   /api/documents/{id}/void      # Void signature envelope
```

### 3.6 Meetings - Full CRUD
```
POST   /api/meetings/                # Create meeting
PATCH  /api/meetings/{id}/           # Update meeting
DELETE /api/meetings/{id}/           # Soft delete (cancel)
POST   /api/meetings/{id}/start      # Start meeting (set in_progress)
POST   /api/meetings/{id}/end        # End meeting (set completed)
```

### 3.7 Meetings - Agenda
```
POST   /api/meetings/{id}/agenda/            # Add agenda item
PATCH  /api/meetings/{id}/agenda/{item_id}/  # Update agenda item
DELETE /api/meetings/{id}/agenda/{item_id}/  # Delete agenda item
PATCH  /api/meetings/{id}/agenda/reorder     # Batch reorder items
```

### 3.8 Meetings - Attendance & Notes
```
GET    /api/meetings/{id}/attendance         # Get attendance
POST   /api/meetings/{id}/attendance         # Record attendance (batch)
PATCH  /api/meetings/{id}/attendance/{member_id} # Update single
GET    /api/meetings/{id}/notes              # Get notes by agenda item
PATCH  /api/meetings/{id}/notes/{item_id}    # Update notes
POST   /api/meetings/{id}/minutes/generate   # Generate draft minutes
GET    /api/meetings/{id}/minutes            # Get minutes document
```

### 3.9 Meetings - Templates
```
GET    /api/meeting-templates/               # List templates
POST   /api/meeting-templates/               # Create template
POST   /api/meetings/from-template/{id}      # Create meeting from template
```

### 3.10 Decisions - Enhancements
```
POST   /api/decisions/               # Create decision (currently missing)
PATCH  /api/decisions/{id}/          # Update decision
POST   /api/decisions/{id}/archive   # Archive with reason
POST   /api/decisions/{id}/close     # Close voting early
POST   /api/decisions/{id}/extend    # Extend deadline
POST   /api/decisions/{id}/remind    # Send reminder to pending voters
GET    /api/decisions/{id}/audit     # Get decision audit trail
POST   /api/decisions/{id}/comments  # Add comment
GET    /api/decisions/{id}/comments  # Get comments (threaded)
```

### 3.11 Ideas - Enhancements
```
PATCH  /api/ideas/{id}/              # Update idea
POST   /api/ideas/{id}/status        # Change status with reason
GET    /api/ideas/{id}/history       # Get change history
GET    /api/categories               # List categories
POST   /api/categories               # Create category (admin)
```

### 3.12 Comments - Enhancements
```
PATCH  /api/comments/{id}            # Edit comment
DELETE /api/comments/{id}            # Soft delete comment
POST   /api/comments/{id}/react      # Add/remove reaction
POST   /api/comments/{id}/pin        # Pin/unpin comment (chair only)
```

---

## 4. Middleware & Integrations

### 4.1 Audit Middleware
Create middleware that automatically logs all write operations:
- Capture IP address from request headers (X-Forwarded-For, etc.)
- Capture user agent
- Log before/after values for updates
- Include entity name for readability

### 4.2 Permission Checking
Implement permission-checking dependency:
```python
async def require_permission(permission_code: str):
    """Dependency that checks if current user has specific permission"""
    # Check role_permissions table
    # Return 403 if not authorized
```

### 4.3 Email Notifications (Future)
Hooks for sending notifications:
- Invitation emails
- Signature reminders
- Vote reminders
- Meeting notifications

---

## 5. Implementation Priority

### Phase 1: Admin Foundation (Critical)
1. Invitations table + endpoints
2. Permissions + role_permissions tables
3. Settings table + endpoints
4. Enhanced audit_log with IP/user agent

### Phase 2: User Management
5. User list with last login tracking
6. Invite user flow
7. Edit user (role, status)
8. Audit trail viewer

### Phase 3: Document CRUD
9. Document versioning
10. Archive/unarchive
11. Activity log per document
12. Related documents

### Phase 4: Meeting CRUD
13. Create/update/delete meetings
14. Full agenda CRUD with reorder
15. Attendance tracking
16. Meeting notes

### Phase 5: Decision CRUD
17. Create decision endpoint
18. Update/archive/close endpoints
19. Discussion comments
20. Reminder system

### Phase 6: Ideas CRUD
21. Update idea with status reason
22. Categories system
23. Comment threading + reactions
24. Change history

---

## 6. Questions for Drew

1. **Database migrations**: Should we create a single migration or break into phases?
2. **Audit log approach**: Use triggers vs. application-level logging?
3. **Permission seeding**: How to handle initial role-permission mappings?
4. **Email integration**: What email service are we using (or planning to)?
5. **File storage**: Document versions - same bucket, different prefix?

---

## 7. Coordination Plan

1. **Drew reviews this document** and confirms feasibility
2. **Drew provides timeline estimates** for each phase
3. **Beth documents frontend-backend contract** (request/response schemas)
4. **Both agree on phase 1 priorities** and start in parallel
5. **Daily sync** to resolve blockers

Once Drew confirms, we can create a shared spec document and begin implementation.
