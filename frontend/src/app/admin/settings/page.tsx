"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Settings,
  Building,
  Clock,
  Bell,
  Shield,
  Upload,
  Trash2,
  Save,
  Loader2,
  Check,
  History,
  Download,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { adminApi, api, type SystemSettings, type AuditLogEntry } from "@/lib/api";
import { usePermissions } from "@/hooks/use-permissions";
import { useBranding } from "@/contexts/branding-context";
import { permissionCategories } from "@/lib/permissions";

type SettingsTab = "general" | "permissions" | "audit";

export default function AdminSettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { isAdmin, isLoading: permissionsLoading } = usePermissions();
  const { refresh: refreshBranding } = useBranding();

  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // General Settings
  const [settings, setSettings] = useState<SystemSettings>({
    app_name: "Board Portal",
    organization_name: "",
    organization_logo_url: null,
    default_meeting_duration: 60,
    voting_reminder_days: 3,
    signature_reminder_days: 7,
  });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  // Audit Log
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFilters, setAuditFilters] = useState({
    entity_type: "",
    action: "",
    start_date: "",
    end_date: "",
  });

  useEffect(() => {
    if (!permissionsLoading && !isAdmin) {
      router.push("/");
    }
  }, [isAdmin, permissionsLoading, router]);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }

        const data = await adminApi.getSettings().catch(() => settings);
        setSettings(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    };

    if (isAdmin) {
      fetchSettings();
    }
  }, [session?.user?.email, isAdmin]);

  const fetchAuditLog = async () => {
    try {
      setAuditLoading(true);
      const data = await adminApi.listAuditLog({
        entity_type: auditFilters.entity_type || undefined,
        action: auditFilters.action || undefined,
        start_date: auditFilters.start_date || undefined,
        end_date: auditFilters.end_date || undefined,
        limit: 50,
      });
      setAuditLog(data);
    } catch (err) {
      console.error("Failed to fetch audit log:", err);
      setAuditLog([]);
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "audit" && isAdmin) {
      fetchAuditLog();
    }
  }, [activeTab, isAdmin, auditFilters]);

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Upload logo if selected
      if (logoFile) {
        await adminApi.uploadLogo(logoFile);
        setLogoFile(null);
      }

      // Save other settings
      await adminApi.updateSettings(settings);

      // Refresh branding so sidebar/title update immediately
      await refreshBranding();

      setSuccess("Settings saved successfully");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveLogo = async () => {
    if (!confirm("Are you sure you want to remove the logo?")) return;
    try {
      await adminApi.removeLogo();
      setSettings({ ...settings, organization_logo_url: null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove logo");
    }
  };

  const handleExportAuditLog = async () => {
    try {
      const blob = await adminApi.exportAuditLog({
        start_date: auditFilters.start_date || undefined,
        end_date: auditFilters.end_date || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().split("T")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export audit log");
    }
  };

  if (permissionsLoading || loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (!isAdmin) {
    return null;
  }

  const tabs = [
    { id: "general" as const, label: "General", icon: Building },
    { id: "permissions" as const, label: "Permissions", icon: Shield, adminOnly: true },
    { id: "audit" as const, label: "Audit Log", icon: History },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Configure your board portal
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 border-b">
          {tabs
            .filter((tab) => !tab.adminOnly || isAdmin)
            .map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                    activeTab === tab.id
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
        </div>

        {/* Error/Success */}
        {error && (
          <div className="p-4 rounded-md bg-destructive/10 text-destructive">
            {error}
          </div>
        )}
        {success && (
          <div className="p-4 rounded-md bg-green-500/10 text-green-500 flex items-center gap-2">
            <Check className="h-4 w-4" />
            {success}
          </div>
        )}

        {/* General Settings Tab */}
        {activeTab === "general" && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building className="h-5 w-5" />
                  Organization
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Portal Name */}
                <div>
                  <label className="text-sm font-medium">Portal Name</label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Shown in the sidebar, login page, and browser tab
                  </p>
                  <input
                    type="text"
                    value={settings.app_name}
                    onChange={(e) =>
                      setSettings({ ...settings, app_name: e.target.value })
                    }
                    className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Organization Name */}
                <div>
                  <label className="text-sm font-medium">Organization Name</label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Your company or organization name
                  </p>
                  <input
                    type="text"
                    value={settings.organization_name}
                    onChange={(e) =>
                      setSettings({ ...settings, organization_name: e.target.value })
                    }
                    className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Logo */}
                <div>
                  <label className="text-sm font-medium">Logo</label>
                  <div className="mt-2 flex items-center gap-4">
                    {settings.organization_logo_url ? (
                      <img
                        src={settings.organization_logo_url}
                        alt="Logo"
                        className="h-16 w-auto rounded"
                      />
                    ) : logoFile ? (
                      <img
                        src={URL.createObjectURL(logoFile)}
                        alt="New logo"
                        className="h-16 w-auto rounded"
                      />
                    ) : (
                      <div className="h-16 w-16 rounded bg-muted flex items-center justify-center">
                        <Building className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}
                    <div className="space-x-2">
                      <input
                        ref={logoInputRef}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) setLogoFile(file);
                        }}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => logoInputRef.current?.click()}
                      >
                        <Upload className="h-4 w-4 mr-2" />
                        Upload
                      </Button>
                      {settings.organization_logo_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRemoveLogo}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Remove
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Meeting Defaults
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div>
                  <label className="text-sm font-medium">Default Duration (minutes)</label>
                  <input
                    type="number"
                    value={settings.default_meeting_duration}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        default_meeting_duration: parseInt(e.target.value) || 60,
                      })
                    }
                    min={15}
                    max={480}
                    step={15}
                    className="w-32 mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Reminders
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">
                    Send voting reminders (days before deadline)
                  </label>
                  <input
                    type="number"
                    value={settings.voting_reminder_days}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        voting_reminder_days: parseInt(e.target.value) || 3,
                      })
                    }
                    min={1}
                    max={14}
                    className="w-32 mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">
                    Send signature reminders (days after sending)
                  </label>
                  <input
                    type="number"
                    value={settings.signature_reminder_days}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        signature_reminder_days: parseInt(e.target.value) || 7,
                      })
                    }
                    min={1}
                    max={30}
                    className="w-32 mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Save Button */}
            <div className="flex justify-end">
              <Button onClick={handleSaveSettings} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Permissions Tab */}
        {activeTab === "permissions" && isAdmin && (
          <div className="space-y-6">
            <p className="text-muted-foreground">
              Configure which permissions each role has access to. Changes take effect
              immediately.
            </p>

            {Object.entries(permissionCategories).map(([key, category]) => (
              <Card key={key}>
                <CardHeader>
                  <CardTitle className="text-lg">{category.label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2 pr-4 font-medium">Permission</th>
                          <th className="text-center py-2 px-4 font-medium">Shareholder</th>
                          <th className="text-center py-2 px-4 font-medium">Board</th>
                          <th className="text-center py-2 px-4 font-medium">Chair</th>
                          <th className="text-center py-2 px-4 font-medium">Admin</th>
                        </tr>
                      </thead>
                      <tbody>
                        {category.permissions.map((perm) => (
                          <tr key={perm.code} className="border-b last:border-0">
                            <td className="py-2 pr-4">{perm.label}</td>
                            <td className="text-center py-2 px-4">
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-gray-300"
                                disabled
                              />
                            </td>
                            <td className="text-center py-2 px-4">
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-gray-300"
                                disabled
                              />
                            </td>
                            <td className="text-center py-2 px-4">
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-gray-300"
                                disabled
                              />
                            </td>
                            <td className="text-center py-2 px-4">
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-gray-300"
                                checked
                                disabled
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            ))}

            <p className="text-sm text-muted-foreground">
              Note: Permission management will be fully functional once the backend
              permissions system is implemented.
            </p>
          </div>
        )}

        {/* Audit Log Tab */}
        {activeTab === "audit" && (
          <div className="space-y-6">
            {/* Filters */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-4">
                  <div>
                    <label className="text-sm font-medium">Entity Type</label>
                    <select
                      value={auditFilters.entity_type}
                      onChange={(e) =>
                        setAuditFilters({ ...auditFilters, entity_type: e.target.value })
                      }
                      className="mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">All Types</option>
                      <option value="document">Documents</option>
                      <option value="meeting">Meetings</option>
                      <option value="decision">Decisions</option>
                      <option value="idea">Ideas</option>
                      <option value="user">Users</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Action</label>
                    <select
                      value={auditFilters.action}
                      onChange={(e) =>
                        setAuditFilters({ ...auditFilters, action: e.target.value })
                      }
                      className="mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">All Actions</option>
                      <option value="create">Create</option>
                      <option value="update">Update</option>
                      <option value="delete">Delete</option>
                      <option value="vote">Vote</option>
                      <option value="sign">Sign</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Start Date</label>
                    <input
                      type="date"
                      value={auditFilters.start_date}
                      onChange={(e) =>
                        setAuditFilters({ ...auditFilters, start_date: e.target.value })
                      }
                      className="mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">End Date</label>
                    <input
                      type="date"
                      value={auditFilters.end_date}
                      onChange={(e) =>
                        setAuditFilters({ ...auditFilters, end_date: e.target.value })
                      }
                      className="mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button variant="outline" onClick={handleExportAuditLog}>
                      <Download className="h-4 w-4 mr-2" />
                      Export CSV
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Audit Log Table */}
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="text-left p-4 font-medium text-sm">Timestamp</th>
                        <th className="text-left p-4 font-medium text-sm">User</th>
                        <th className="text-left p-4 font-medium text-sm">Action</th>
                        <th className="text-left p-4 font-medium text-sm">Entity</th>
                        <th className="text-left p-4 font-medium text-sm">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLoading ? (
                        <tr>
                          <td colSpan={5} className="p-8 text-center">
                            <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                          </td>
                        </tr>
                      ) : auditLog.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="p-8 text-center text-muted-foreground">
                            No audit log entries found.
                          </td>
                        </tr>
                      ) : (
                        auditLog.map((entry) => (
                          <tr
                            key={entry.id}
                            className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                          >
                            <td className="p-4 text-sm text-muted-foreground">
                              {new Date(entry.changed_at).toLocaleString()}
                            </td>
                            <td className="p-4 text-sm">
                              {entry.changed_by_name || `User #${entry.changed_by_id}`}
                            </td>
                            <td className="p-4">
                              <span
                                className={cn(
                                  "inline-flex px-2 py-1 rounded text-xs font-medium",
                                  entry.action === "create" && "bg-green-500/20 text-green-400",
                                  entry.action === "update" && "bg-blue-500/20 text-blue-400",
                                  entry.action === "delete" && "bg-red-500/20 text-red-400",
                                  !["create", "update", "delete"].includes(entry.action) &&
                                    "bg-gray-500/20 text-gray-400"
                                )}
                              >
                                {entry.action}
                              </span>
                            </td>
                            <td className="p-4 text-sm">
                              <span className="capitalize">{entry.entity_type}</span>
                              {entry.entity_name && (
                                <span className="text-muted-foreground">
                                  {" "}
                                  - {entry.entity_name}
                                </span>
                              )}
                            </td>
                            <td className="p-4 text-sm text-muted-foreground">
                              {entry.ip_address && (
                                <span className="text-xs">{entry.ip_address}</span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
