/**
 * Permission System for TMG Board
 *
 * Defines the permission matrix and provides utilities for checking permissions.
 * This is the frontend representation - backend enforces via middleware.
 */

// All available permissions in the system
export type Permission =
  // Documents
  | "documents.view"
  | "documents.upload"
  | "documents.edit"
  | "documents.delete"
  | "documents.archive"
  | "documents.send_for_signature"
  // Meetings
  | "meetings.view"
  | "meetings.create"
  | "meetings.edit"
  | "meetings.delete"
  | "meetings.manage_agenda"
  | "meetings.take_attendance"
  // Decisions
  | "decisions.view"
  | "decisions.create"
  | "decisions.vote"
  | "decisions.close"
  | "decisions.archive"
  // Ideas
  | "ideas.view"
  | "ideas.submit"
  | "ideas.comment"
  | "ideas.moderate"
  | "ideas.promote"
  // Admin
  | "admin.view_users"
  | "admin.invite_users"
  | "admin.edit_users"
  | "admin.manage_roles"
  | "admin.view_audit"
  | "admin.manage_settings";

// User roles
export type Role = "member" | "chair" | "admin";

// Default permission matrix (will be replaced by backend data once available)
const defaultPermissionMatrix: Record<Role, Permission[]> = {
  member: [
    "documents.view",
    "meetings.view",
    "decisions.view",
    "decisions.vote",
    "ideas.view",
    "ideas.submit",
    "ideas.comment",
  ],
  chair: [
    // All member permissions
    "documents.view",
    "documents.upload",
    "documents.edit",
    "documents.archive",
    "documents.send_for_signature",
    "meetings.view",
    "meetings.create",
    "meetings.edit",
    "meetings.manage_agenda",
    "meetings.take_attendance",
    "decisions.view",
    "decisions.create",
    "decisions.vote",
    "decisions.close",
    "ideas.view",
    "ideas.submit",
    "ideas.comment",
    "ideas.moderate",
    "ideas.promote",
  ],
  admin: [
    // All permissions
    "documents.view",
    "documents.upload",
    "documents.edit",
    "documents.delete",
    "documents.archive",
    "documents.send_for_signature",
    "meetings.view",
    "meetings.create",
    "meetings.edit",
    "meetings.delete",
    "meetings.manage_agenda",
    "meetings.take_attendance",
    "decisions.view",
    "decisions.create",
    "decisions.vote",
    "decisions.close",
    "decisions.archive",
    "ideas.view",
    "ideas.submit",
    "ideas.comment",
    "ideas.moderate",
    "ideas.promote",
    "admin.view_users",
    "admin.invite_users",
    "admin.edit_users",
    "admin.manage_roles",
    "admin.view_audit",
    "admin.manage_settings",
  ],
};

// Permission categories for UI grouping
export const permissionCategories = {
  documents: {
    label: "Documents",
    permissions: [
      { code: "documents.view", label: "View documents" },
      { code: "documents.upload", label: "Upload documents" },
      { code: "documents.edit", label: "Edit documents" },
      { code: "documents.delete", label: "Delete documents" },
      { code: "documents.archive", label: "Archive/unarchive documents" },
      { code: "documents.send_for_signature", label: "Send for signature" },
    ],
  },
  meetings: {
    label: "Meetings",
    permissions: [
      { code: "meetings.view", label: "View meetings" },
      { code: "meetings.create", label: "Create meetings" },
      { code: "meetings.edit", label: "Edit meetings" },
      { code: "meetings.delete", label: "Delete meetings" },
      { code: "meetings.manage_agenda", label: "Manage agenda items" },
      { code: "meetings.take_attendance", label: "Take attendance" },
    ],
  },
  decisions: {
    label: "Decisions",
    permissions: [
      { code: "decisions.view", label: "View decisions" },
      { code: "decisions.create", label: "Create decisions" },
      { code: "decisions.vote", label: "Cast votes" },
      { code: "decisions.close", label: "Close voting" },
      { code: "decisions.archive", label: "Archive decisions" },
    ],
  },
  ideas: {
    label: "Ideas",
    permissions: [
      { code: "ideas.view", label: "View ideas" },
      { code: "ideas.submit", label: "Submit ideas" },
      { code: "ideas.comment", label: "Comment on ideas" },
      { code: "ideas.moderate", label: "Moderate ideas" },
      { code: "ideas.promote", label: "Promote to decision" },
    ],
  },
  admin: {
    label: "Administration",
    permissions: [
      { code: "admin.view_users", label: "View users" },
      { code: "admin.invite_users", label: "Invite users" },
      { code: "admin.edit_users", label: "Edit users" },
      { code: "admin.manage_roles", label: "Manage role permissions" },
      { code: "admin.view_audit", label: "View audit log" },
      { code: "admin.manage_settings", label: "Manage settings" },
    ],
  },
};

/**
 * Check if a role has a specific permission
 */
export function hasPermission(role: Role | undefined, permission: Permission): boolean {
  if (!role) return false;
  return defaultPermissionMatrix[role]?.includes(permission) ?? false;
}

/**
 * Check if a role has any of the specified permissions
 */
export function hasAnyPermission(role: Role | undefined, permissions: Permission[]): boolean {
  if (!role) return false;
  return permissions.some((p) => hasPermission(role, p));
}

/**
 * Check if a role has all of the specified permissions
 */
export function hasAllPermissions(role: Role | undefined, permissions: Permission[]): boolean {
  if (!role) return false;
  return permissions.every((p) => hasPermission(role, p));
}

/**
 * Get all permissions for a role
 */
export function getPermissionsForRole(role: Role): Permission[] {
  return defaultPermissionMatrix[role] || [];
}

/**
 * Check if user is admin or chair (common pattern)
 */
export function isAdminOrChair(role: Role | undefined): boolean {
  return role === "admin" || role === "chair";
}
