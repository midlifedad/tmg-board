"use client";

import { useSession } from "next-auth/react";
import {
  type Permission,
  type Role,
  hasPermission,
  hasAnyPermission,
  hasAllPermissions,
  isBoardOrAbove,
  isAdmin,
} from "@/lib/permissions";

/**
 * Hook to check user permissions based on their session role
 */
export function usePermissions() {
  const { data: session, status } = useSession();

  const role = (session?.user as { role?: Role })?.role;
  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";

  return {
    // Session info
    role,
    isLoading,
    isAuthenticated,
    user: session?.user,

    // Permission checks
    can: (permission: Permission) => hasPermission(role, permission),
    canAny: (permissions: Permission[]) => hasAnyPermission(role, permissions),
    canAll: (permissions: Permission[]) => hasAllPermissions(role, permissions),

    // Role checks
    isAdmin: isAdmin(role),
    isBoard: isBoardOrAbove(role),
    isShareholder: role === "shareholder",
    isBoardOrAbove: isBoardOrAbove(role),
  };
}

/**
 * Component that conditionally renders children based on permission
 */
export function RequirePermission({
  permission,
  children,
  fallback = null,
}: {
  permission: Permission | Permission[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { can, canAny, isLoading } = usePermissions();

  if (isLoading) {
    return null;
  }

  const hasAccess = Array.isArray(permission) ? canAny(permission) : can(permission);

  return hasAccess ? <>{children}</> : <>{fallback}</>;
}

/**
 * Component that conditionally renders children for admin only
 */
export function AdminOnly({
  children,
  fallback = null,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { isAdmin, isLoading } = usePermissions();

  if (isLoading) {
    return null;
  }

  return isAdmin ? <>{children}</> : <>{fallback}</>;
}
