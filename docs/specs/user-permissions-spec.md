# User Permissions Feature Specification

## Overview

Implement email whitelist and role-based access control for TMG Board Portal. Only approved email addresses can access the site after Google Auth, and users have different permission levels based on their assigned role.

**Reference Implementation:** themany-forecasting project (same pattern)

## Status: MOSTLY IMPLEMENTED

Per Drew's analysis, most of this already exists:

### Already Implemented (Backend)
- `board_members` table - acts as email whitelist with roles
- `permissions` table - 16 granular permissions
- `role_permissions` table - maps roles to permissions
- `invitations` table - for inviting new users
- Auth dependencies: `require_member`, `require_chair`, `require_admin`

### Already Implemented (Frontend)
- `src/lib/auth.ts` - NextAuth with email whitelist verification
- `src/lib/permissions.ts` - Full permission system with role matrix
- `src/app/admin/users/page.tsx` - User management UI
- `src/lib/api.ts` - adminApi with all user management methods

### Remaining Work
- **Backend**: Confirm/add endpoints: `/api/auth/user/{email}`, `/api/admin/users`, etc.
- **Frontend**: Add Edit User modal for changing roles

## Requirements

### 1. Email Whitelist
- Only users with emails in the `users` table can access the application
- After Google OAuth, verify the email exists in the whitelist
- If not whitelisted → reject sign-in with "Contact an administrator" message

### 2. Role-Based Permissions

| Role | Can View | Can Edit/Create | Can Manage Users |
|------|----------|-----------------|------------------|
| **Admin** | All pages | All data | Yes (add/edit/remove users) |
| **Manager** | All pages | All data | No |
| **Viewer** | All pages | Nothing | No |

**Permission Matrix by Feature:**

| Feature | Admin | Manager | Viewer |
|---------|-------|---------|--------|
| View Dashboard | ✅ | ✅ | ✅ |
| View Documents | ✅ | ✅ | ✅ |
| Upload Documents | ✅ | ✅ | ❌ |
| View Meetings | ✅ | ✅ | ✅ |
| Create/Edit Meetings | ✅ | ✅ | ❌ |
| View Decisions | ✅ | ✅ | ✅ |
| Create/Open/Close Decisions | ✅ | ✅ | ❌ |
| Cast Vote | ✅ | ✅ | ✅ |
| View Ideas | ✅ | ✅ | ✅ |
| Create/Edit Ideas | ✅ | ✅ | ❌ |
| Add Comments | ✅ | ✅ | ❌ |
| Admin Settings | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |

---

## Backend Implementation (Drew)

### Database Schema

#### New Table: `user_roles`
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE,  -- 'admin', 'manager', 'viewer'
    description TEXT
);

-- Seed data
INSERT INTO user_roles (id, name, description) VALUES
    (1, 'admin', 'Full access - can manage users and all data'),
    (2, 'manager', 'Can create and edit all data'),
    (3, 'viewer', 'Read-only access');
```

#### New Table: `allowed_users`
```sql
CREATE TABLE allowed_users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL DEFAULT 3,  -- Default to viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES user_roles(id),
    FOREIGN KEY (created_by_id) REFERENCES allowed_users(id)
);

CREATE INDEX idx_allowed_users_email ON allowed_users(email);
```

### API Endpoints

#### Auth Verification (for NextAuth callback)

```
POST /api/auth/verify
Request: { "email": "user@example.com", "name": "User Name" }
Response (200): { "id": 1, "email": "...", "name": "...", "role": "admin", "is_active": true }
Response (401): { "detail": "User not authorized. Contact an administrator." }
```

```
GET /api/auth/user/{email}
Response: { "id": 1, "email": "...", "name": "...", "role": "admin" }
```

#### User Management (Admin only)

```
GET /api/admin/users
Response: [{ "id": 1, "email": "...", "name": "...", "role": "admin", "is_active": true, "last_login_at": "..." }, ...]

POST /api/admin/users
Request: { "email": "newuser@example.com", "name": "New User", "role": "viewer" }
Response (201): { "id": 2, ... }
Response (400): { "detail": "Email already exists" }

PUT /api/admin/users/{id}
Request: { "name": "Updated Name", "role": "manager" }
Response (200): { ... }

DELETE /api/admin/users/{id}
Response (200): { "status": "deleted", "id": 1 }
Response (403): { "detail": "Cannot delete yourself" }
```

#### Roles Reference

```
GET /api/admin/roles
Response: [
    { "id": 1, "name": "admin", "description": "..." },
    { "id": 2, "name": "manager", "description": "..." },
    { "id": 3, "name": "viewer", "description": "..." }
]
```

### Auth Dependencies

Create reusable dependencies for endpoint protection:

```python
# app/api/deps.py

async def get_current_user(
    x_user_email: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[AllowedUser]:
    """Get current user from X-User-Email header."""
    if not x_user_email:
        return None
    return db.query(AllowedUser).filter(
        AllowedUser.email == x_user_email,
        AllowedUser.is_active == True
    ).first()


async def require_user(
    current_user: Optional[AllowedUser] = Depends(get_current_user)
) -> AllowedUser:
    """Require authenticated user. Returns 401 if not found."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


async def require_manager(
    current_user: AllowedUser = Depends(require_user)
) -> AllowedUser:
    """Require manager or admin role. Returns 403 if viewer."""
    if current_user.role.name == "viewer":
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user


async def require_admin(
    current_user: AllowedUser = Depends(require_user)
) -> AllowedUser:
    """Require admin role. Returns 403 if not admin."""
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

### Endpoint Protection

Update existing endpoints to use the new dependencies:

| Endpoint Pattern | Current Auth | New Auth |
|------------------|--------------|----------|
| `GET /api/*` (list/view) | `require_user` | `require_user` |
| `POST /api/*` (create) | `require_user` | `require_manager` |
| `PUT /api/*` (update) | `require_user` | `require_manager` |
| `DELETE /api/*` (delete) | `require_user` | `require_manager` |
| `POST /api/decisions/*/vote` | `require_user` | `require_user` (viewers can vote) |
| `/api/admin/*` | N/A | `require_admin` |

---

## Frontend Implementation (Beth)

### NextAuth Configuration Updates

Update `/src/app/api/auth/[...nextauth]/route.ts`:

```typescript
callbacks: {
  async signIn({ user }) {
    // Verify user exists in whitelist
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: user.email, name: user.name }),
      });
      if (!res.ok) {
        return false; // Reject sign-in
      }
      return true;
    } catch {
      return false;
    }
  },

  async jwt({ token, user }) {
    if (user?.email) {
      const res = await fetch(`${BACKEND_URL}/api/auth/user/${encodeURIComponent(user.email)}`);
      if (res.ok) {
        const userData = await res.json();
        token.userId = userData.id;
        token.role = userData.role;
      }
    }
    return token;
  },

  async session({ session, token }) {
    if (session.user) {
      (session.user as any).id = token.userId;
      (session.user as any).role = token.role;
    }
    return session;
  },
}
```

### Permission Hook Updates

Update `/src/lib/permissions.ts`:

```typescript
export type UserRole = "admin" | "manager" | "viewer";

export const PERMISSIONS = {
  // Documents
  "documents:view": ["admin", "manager", "viewer"],
  "documents:upload": ["admin", "manager"],
  "documents:delete": ["admin", "manager"],

  // Meetings
  "meetings:view": ["admin", "manager", "viewer"],
  "meetings:create": ["admin", "manager"],
  "meetings:edit": ["admin", "manager"],

  // Decisions
  "decisions:view": ["admin", "manager", "viewer"],
  "decisions:create": ["admin", "manager"],
  "decisions:vote": ["admin", "manager", "viewer"],

  // Ideas
  "ideas:view": ["admin", "manager", "viewer"],
  "ideas:create": ["admin", "manager"],
  "ideas:comment": ["admin", "manager"],

  // Admin
  "admin:access": ["admin"],
  "users:manage": ["admin"],
} as const;

export function hasPermission(role: UserRole, permission: keyof typeof PERMISSIONS): boolean {
  return PERMISSIONS[permission].includes(role);
}
```

### Admin Users Page

Update `/src/app/admin/users/page.tsx` to:

1. List all allowed users with their roles
2. Add new users (email + name + role)
3. Edit user roles
4. Deactivate/delete users
5. Show last login timestamp

### UI Components

- **User Table**: Sortable by name, email, role, last login
- **Add User Modal**: Email, name, role dropdown
- **Edit User Modal**: Update name and role
- **Delete Confirmation**: Prevent self-deletion

---

## Implementation Phases

### Phase 1: Backend (Drew)
1. Create `user_roles` and `allowed_users` tables
2. Implement auth verification endpoints
3. Add auth dependencies (`require_user`, `require_manager`, `require_admin`)
4. Protect existing endpoints with appropriate dependencies
5. Implement user management endpoints

### Phase 2: Frontend (Beth)
1. Update NextAuth to verify against whitelist
2. Store role in session
3. Update permission system to use actual role from session
4. Build user management UI in admin settings
5. Hide/disable UI elements based on role

### Phase 3: Testing
1. Test sign-in rejection for non-whitelisted emails
2. Test role-based endpoint access
3. Test UI conditional rendering
4. Test user management CRUD

---

## Seed Data

Initial users to add:

```sql
-- Admin user (for initial setup)
INSERT INTO allowed_users (email, name, role_id) VALUES
    ('admin@example.com', 'Admin User', 1);
```

The first admin will need to be added manually or via migration. After that, they can add other users through the UI.

---

## Questions for Drew

1. **Migration strategy**: Add new tables alongside existing `board_members`? Or migrate data?
2. **Relationship to board_members**: Should `allowed_users` replace or supplement `board_members`?
3. **Audit logging**: Track user management actions in audit_log?
4. **Rate limiting**: Add rate limits to auth verification endpoint?

---

## Notes

- This implementation mirrors themany-forecasting for consistency
- Viewers can still vote on decisions (per business requirement)
- Comments restricted to admin/manager (viewers can't comment)
- All pages visible to all roles (no page-level restrictions, only action restrictions)
