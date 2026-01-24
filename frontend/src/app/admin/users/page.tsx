"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Users,
  UserPlus,
  Mail,
  MoreVertical,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Search,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { adminApi, api, type BoardMember, type Invitation } from "@/lib/api";
import { usePermissions } from "@/hooks/use-permissions";
import { InviteUserModal } from "@/components/invite-user-modal";

const roleConfig: Record<string, { label: string; icon: typeof Shield; color: string }> = {
  admin: { label: "Admin", icon: ShieldAlert, color: "text-red-500" },
  chair: { label: "Chair", icon: ShieldCheck, color: "text-amber-500" },
  member: { label: "Member", icon: Shield, color: "text-blue-500" },
};

export default function AdminUsersPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { isAdminOrChair, isLoading: permissionsLoading } = usePermissions();

  const [users, setUsers] = useState<BoardMember[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [activeTab, setActiveTab] = useState<"users" | "invitations">("users");

  useEffect(() => {
    // Redirect if not admin/chair
    if (!permissionsLoading && !isAdminOrChair) {
      router.push("/");
    }
  }, [isAdminOrChair, permissionsLoading, router]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }

        const [usersData, invitationsData] = await Promise.all([
          adminApi.listUsers().catch(() => []),
          adminApi.listInvitations().catch(() => []),
        ]);

        setUsers(usersData);
        setInvitations(invitationsData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    if (isAdminOrChair) {
      fetchData();
    }
  }, [session?.user?.email, isAdminOrChair]);

  const refetchData = async () => {
    try {
      const [usersData, invitationsData] = await Promise.all([
        adminApi.listUsers().catch(() => []),
        adminApi.listInvitations().catch(() => []),
      ]);
      setUsers(usersData);
      setInvitations(invitationsData);
    } catch (err) {
      console.error("Failed to refetch data:", err);
    }
  };

  const handleResendInvite = async (id: number) => {
    try {
      await adminApi.resendInvitation(String(id));
      refetchData();
    } catch (err) {
      console.error("Failed to resend invite:", err);
    }
  };

  const handleCancelInvite = async (id: number) => {
    if (!confirm("Are you sure you want to cancel this invitation?")) return;
    try {
      await adminApi.cancelInvitation(String(id));
      refetchData();
    } catch (err) {
      console.error("Failed to cancel invite:", err);
    }
  };

  // Filter users by search
  const filteredUsers = users.filter((user) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      user.name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query)
    );
  });

  const filteredInvitations = invitations.filter((inv) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      inv.name.toLowerCase().includes(query) ||
      inv.email.toLowerCase().includes(query)
    );
  });

  if (permissionsLoading || loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (!isAdminOrChair) {
    return null;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">User Management</h1>
            <p className="text-muted-foreground mt-1">
              Manage board members and invitations
            </p>
          </div>
          <Button onClick={() => setShowInviteModal(true)}>
            <UserPlus className="h-4 w-4 mr-2" />
            Invite User
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Users</p>
                  <p className="text-2xl font-bold">{users.length}</p>
                </div>
                <Users className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Admins</p>
                  <p className="text-2xl font-bold">
                    {users.filter((u) => u.role === "admin").length}
                  </p>
                </div>
                <ShieldAlert className="h-8 w-8 text-red-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Chairs</p>
                  <p className="text-2xl font-bold">
                    {users.filter((u) => u.role === "chair").length}
                  </p>
                </div>
                <ShieldCheck className="h-8 w-8 text-amber-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Invites</p>
                  <p className="text-2xl font-bold">{invitations.length}</p>
                </div>
                <Mail className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs & Search */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-2">
            <Button
              variant={activeTab === "users" ? "default" : "outline"}
              onClick={() => setActiveTab("users")}
            >
              <Users className="h-4 w-4 mr-2" />
              Users ({users.length})
            </Button>
            <Button
              variant={activeTab === "invitations" ? "default" : "outline"}
              onClick={() => setActiveTab("invitations")}
            >
              <Mail className="h-4 w-4 mr-2" />
              Invitations ({invitations.length})
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64 h-10 pl-9 pr-4 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <Button variant="outline" size="icon" onClick={refetchData}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded-md bg-destructive/10 text-destructive">
            {error}
          </div>
        )}

        {/* Users Table */}
        {activeTab === "users" && (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium text-sm">User</th>
                      <th className="text-left p-4 font-medium text-sm">Role</th>
                      <th className="text-left p-4 font-medium text-sm">Status</th>
                      <th className="text-left p-4 font-medium text-sm">Last Login</th>
                      <th className="text-right p-4 font-medium text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((user) => {
                      const role = roleConfig[user.role] || roleConfig.member;
                      const RoleIcon = role.icon;

                      return (
                        <tr
                          key={user.id}
                          className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                        >
                          <td className="p-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                                <span className="text-sm font-medium">
                                  {user.name?.[0]?.toUpperCase() || "?"}
                                </span>
                              </div>
                              <div>
                                <p className="font-medium">{user.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  {user.email}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="p-4">
                            <div className={cn("flex items-center gap-1.5", role.color)}>
                              <RoleIcon className="h-4 w-4" />
                              <span className="text-sm font-medium">{role.label}</span>
                            </div>
                          </td>
                          <td className="p-4">
                            <span
                              className={cn(
                                "inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium",
                                user.status === "inactive"
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-green-500/20 text-green-400"
                              )}
                            >
                              {user.status === "inactive" ? (
                                <XCircle className="h-3 w-3" />
                              ) : (
                                <CheckCircle className="h-3 w-3" />
                              )}
                              {user.status === "inactive" ? "Inactive" : "Active"}
                            </span>
                          </td>
                          <td className="p-4 text-sm text-muted-foreground">
                            {user.last_login_at
                              ? new Date(user.last_login_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  year: "numeric",
                                })
                              : "Never"}
                          </td>
                          <td className="p-4">
                            <div className="flex items-center justify-end">
                              <Button variant="ghost" size="sm">
                                Edit
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {filteredUsers.length === 0 && (
                  <div className="p-8 text-center text-muted-foreground">
                    No users found matching your criteria.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Invitations Table */}
        {activeTab === "invitations" && (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium text-sm">Invitee</th>
                      <th className="text-left p-4 font-medium text-sm">Role</th>
                      <th className="text-left p-4 font-medium text-sm">Status</th>
                      <th className="text-left p-4 font-medium text-sm">Expires</th>
                      <th className="text-right p-4 font-medium text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInvitations.map((invite) => {
                      const role = roleConfig[invite.role] || roleConfig.member;
                      const RoleIcon = role.icon;
                      const isExpired = new Date(invite.expires_at) < new Date();

                      return (
                        <tr
                          key={invite.id}
                          className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                        >
                          <td className="p-4">
                            <div>
                              <p className="font-medium">{invite.name}</p>
                              <p className="text-sm text-muted-foreground">
                                {invite.email}
                              </p>
                            </div>
                          </td>
                          <td className="p-4">
                            <div className={cn("flex items-center gap-1.5", role.color)}>
                              <RoleIcon className="h-4 w-4" />
                              <span className="text-sm font-medium">{role.label}</span>
                            </div>
                          </td>
                          <td className="p-4">
                            <span
                              className={cn(
                                "inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium",
                                isExpired
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-amber-500/20 text-amber-400"
                              )}
                            >
                              <Clock className="h-3 w-3" />
                              {isExpired ? "Expired" : "Pending"}
                            </span>
                          </td>
                          <td className="p-4 text-sm text-muted-foreground">
                            {new Date(invite.expires_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </td>
                          <td className="p-4">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleResendInvite(invite.id)}
                              >
                                Resend
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive"
                                onClick={() => handleCancelInvite(invite.id)}
                              >
                                Cancel
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {filteredInvitations.length === 0 && (
                  <div className="p-8 text-center text-muted-foreground">
                    No pending invitations.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Invite Modal */}
      <InviteUserModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        onSuccess={refetchData}
      />
    </AppShell>
  );
}
