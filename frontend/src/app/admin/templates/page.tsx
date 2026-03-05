"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Plus,
  Trash2,
  Pencil,
  Shield,
  Loader2,
  ChevronUp,
  ChevronDown,
  X,
  ClipboardList,
} from "lucide-react";
import {
  templatesApi,
  api,
  type MeetingTemplate,
  type TemplateDetail,
  type TemplateItem,
} from "@/lib/api";
import { isAdmin, type Role } from "@/lib/permissions";

// ---------------------------------------------------------------------------
// Types for local editing
// ---------------------------------------------------------------------------

interface LocalTemplateItem {
  id: string;
  title: string;
  description: string;
  item_type: string;
  duration_minutes: number;
  is_regulatory: boolean;
}

const ITEM_TYPE_OPTIONS = [
  { value: "information", label: "Information" },
  { value: "discussion", label: "Discussion" },
  { value: "decision_required", label: "Decision Required" },
  { value: "consent_agenda", label: "Consent Agenda" },
];

function itemTypeLabel(itemType: string): string {
  const opt = ITEM_TYPE_OPTIONS.find((o) => o.value === itemType);
  return opt?.label || itemType;
}

function itemTypeBadgeColor(itemType: string): string {
  switch (itemType) {
    case "decision_required":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "discussion":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    case "consent_agenda":
      return "bg-purple-500/20 text-purple-400 border-purple-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

let localIdCounter = 0;
function newLocalId(): string {
  localIdCounter += 1;
  return `tpl-local-${Date.now()}-${localIdCounter}`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminTemplatesPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const userRole = (session?.user as { role?: Role })?.role;
  const userEmail = session?.user?.email || "";

  const [templates, setTemplates] = useState<MeetingTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formDuration, setFormDuration] = useState("");
  const [formLocation, setFormLocation] = useState("");
  const [formItems, setFormItems] = useState<LocalTemplateItem[]>([]);
  const [formSaving, setFormSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // New item fields
  const [showNewItem, setShowNewItem] = useState(false);
  const [newItemTitle, setNewItemTitle] = useState("");
  const [newItemType, setNewItemType] = useState("discussion");
  const [newItemDuration, setNewItemDuration] = useState("10");
  const [newItemDescription, setNewItemDescription] = useState("");
  const [newItemRegulatory, setNewItemRegulatory] = useState(false);

  // Delete confirmation
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    try {
      setLoading(true);
      api.setUserEmail(userEmail);
      const data = await templatesApi.list();
      setTemplates(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, [userEmail]);

  useEffect(() => {
    if (userEmail) {
      fetchTemplates();
    }
  }, [userEmail, fetchTemplates]);

  // Auth check
  if (!isAdmin(userRole)) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive text-lg">Access Denied</p>
          <p className="text-muted-foreground">
            Only administrators can manage meeting templates.
          </p>
          <Button onClick={() => router.push("/")}>Go to Dashboard</Button>
        </div>
      </AppShell>
    );
  }

  // Form reset
  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setFormName("");
    setFormDescription("");
    setFormDuration("");
    setFormLocation("");
    setFormItems([]);
    setFormError(null);
    setShowNewItem(false);
    resetNewItemFields();
  };

  const resetNewItemFields = () => {
    setNewItemTitle("");
    setNewItemType("discussion");
    setNewItemDuration("10");
    setNewItemDescription("");
    setNewItemRegulatory(false);
  };

  // Open create form
  const handleCreate = () => {
    resetForm();
    setShowForm(true);
  };

  // Open edit form
  const handleEdit = async (id: number) => {
    try {
      api.setUserEmail(userEmail);
      const detail = await templatesApi.get(id);
      setEditingId(id);
      setFormName(detail.name);
      setFormDescription(detail.description || "");
      setFormDuration(detail.default_duration_minutes ? String(detail.default_duration_minutes) : "");
      setFormLocation(detail.default_location || "");
      setFormItems(
        detail.items.map((item) => ({
          id: newLocalId(),
          title: item.title,
          description: item.description || "",
          item_type: item.item_type,
          duration_minutes: item.duration_minutes || 10,
          is_regulatory: item.is_regulatory,
        }))
      );
      setFormError(null);
      setShowForm(true);
    } catch (err) {
      console.error("Failed to load template for editing:", err);
    }
  };

  // Save template
  const handleSave = async () => {
    if (!formName.trim()) {
      setFormError("Template name is required");
      return;
    }

    setFormSaving(true);
    setFormError(null);

    try {
      const payload = {
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        default_duration_minutes: formDuration ? parseInt(formDuration) : undefined,
        default_location: formLocation.trim() || undefined,
        items: formItems.map((item, index) => ({
          title: item.title,
          description: item.description || undefined,
          item_type: item.item_type,
          duration_minutes: item.duration_minutes,
          order_index: index,
          is_regulatory: item.is_regulatory,
        })),
      };

      if (editingId) {
        await templatesApi.update(editingId, payload);
      } else {
        await templatesApi.create(payload);
      }

      resetForm();
      await fetchTemplates();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save template");
    } finally {
      setFormSaving(false);
    }
  };

  // Delete template
  const handleDelete = async (id: number) => {
    setDeleting(true);
    try {
      await templatesApi.delete(id);
      setDeletingId(null);
      await fetchTemplates();
    } catch (err) {
      console.error("Failed to delete template:", err);
    } finally {
      setDeleting(false);
    }
  };

  // Agenda item actions
  const addFormItem = () => {
    if (!newItemTitle.trim()) return;
    setFormItems((prev) => [
      ...prev,
      {
        id: newLocalId(),
        title: newItemTitle.trim(),
        description: newItemDescription.trim(),
        item_type: newItemType,
        duration_minutes: parseInt(newItemDuration) || 10,
        is_regulatory: newItemRegulatory,
      },
    ]);
    resetNewItemFields();
    setShowNewItem(false);
  };

  const removeFormItem = (itemId: string) => {
    setFormItems((prev) => prev.filter((i) => i.id !== itemId));
  };

  const moveFormItem = (index: number, direction: "up" | "down") => {
    setFormItems((prev) => {
      const next = [...prev];
      const swapIndex = direction === "up" ? index - 1 : index + 1;
      if (swapIndex < 0 || swapIndex >= next.length) return prev;
      [next[index], next[swapIndex]] = [next[swapIndex], next[index]];
      return next;
    });
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
              <span>Admin</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            <h1 className="text-3xl font-light">Meeting Templates</h1>
            <p className="text-muted-foreground mt-1">
              Manage reusable meeting templates with standard agenda items.
            </p>
          </div>
          <Button onClick={handleCreate} className="min-h-[44px]">
            <Plus className="h-4 w-4 mr-2" />
            Create Template
          </Button>
        </div>

        {error && (
          <div className="rounded-md border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Template Form (Create/Edit) */}
        {showForm && (
          <Card className="border-gray-800 border-t-2 border-t-[var(--gold)]/40">
            <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between space-y-0">
              <div className="flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-[var(--gold)]" />
                <span className="text-sm font-medium text-white">
                  {editingId ? "Edit Template" : "Create Template"}
                </span>
              </div>
              <button
                onClick={resetForm}
                className="text-gray-500 hover:text-gray-300 transition-colors p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </CardHeader>
            <CardContent className="p-4 pt-2 space-y-4">
              {/* Template name */}
              <div>
                <label className="text-sm font-medium">Template Name *</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Board Meeting"
                  className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                />
              </div>

              {/* Description */}
              <div>
                <label className="text-sm font-medium">Description</label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Optional template description"
                  rows={2}
                  className="w-full mt-1 px-3 py-2 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30 resize-none"
                />
              </div>

              {/* Default duration and location */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">
                    Default Duration (min)
                  </label>
                  <input
                    type="number"
                    value={formDuration}
                    onChange={(e) => setFormDuration(e.target.value)}
                    min="15"
                    step="15"
                    placeholder="60"
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">
                    Default Location
                  </label>
                  <input
                    type="text"
                    value={formLocation}
                    onChange={(e) => setFormLocation(e.target.value)}
                    placeholder="Conference Room A"
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                  />
                </div>
              </div>

              {/* Agenda items */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] flex items-center gap-3">
                    <span>Agenda Items</span>
                    <div className="flex-1 h-px bg-border" />
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-gray-700 text-gray-300 hover:text-white"
                    onClick={() => setShowNewItem(true)}
                  >
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Add Item
                  </Button>
                </div>

                {formItems.length === 0 && !showNewItem && (
                  <p className="text-sm text-muted-foreground py-3 text-center">
                    No agenda items yet.
                  </p>
                )}

                <div className="space-y-2">
                  {formItems.map((item, index) => (
                    <div
                      key={item.id}
                      className={`rounded-md border p-3 ${
                        item.is_regulatory
                          ? "border-l-2 border-l-amber-500/70 border-gray-700 bg-amber-500/5"
                          : "border-gray-700"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-white">
                              {index + 1}. {item.title}
                            </span>
                            <span
                              className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono rounded border ${itemTypeBadgeColor(
                                item.item_type
                              )}`}
                            >
                              {itemTypeLabel(item.item_type)}
                            </span>
                            {item.is_regulatory && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                <Shield className="h-3 w-3" />
                                Regulatory
                              </span>
                            )}
                            {item.duration_minutes > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {item.duration_minutes} min
                              </span>
                            )}
                          </div>
                          {item.description && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {item.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => moveFormItem(index, "up")}
                            disabled={index === 0}
                            className="p-1 text-gray-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <ChevronUp className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => moveFormItem(index, "down")}
                            disabled={index === formItems.length - 1}
                            className="p-1 text-gray-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <ChevronDown className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => removeFormItem(item.id)}
                            className="p-1 text-gray-500 hover:text-red-400"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Add item inline form */}
                  {showNewItem && (
                    <div className="rounded-md border border-gray-700 border-dashed p-3 space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-gray-400">
                            Title
                          </label>
                          <input
                            type="text"
                            value={newItemTitle}
                            onChange={(e) => setNewItemTitle(e.target.value)}
                            placeholder="Agenda item title"
                            className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                            autoFocus
                          />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-gray-400">
                            Type
                          </label>
                          <select
                            value={newItemType}
                            onChange={(e) => setNewItemType(e.target.value)}
                            className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                          >
                            {ITEM_TYPE_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-xs font-medium text-gray-400">
                            Duration (min)
                          </label>
                          <input
                            type="number"
                            value={newItemDuration}
                            onChange={(e) => setNewItemDuration(e.target.value)}
                            min="1"
                            placeholder="10"
                            className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                          />
                        </div>
                        <div className="col-span-2">
                          <label className="text-xs font-medium text-gray-400">
                            Description (optional)
                          </label>
                          <textarea
                            value={newItemDescription}
                            onChange={(e) =>
                              setNewItemDescription(e.target.value)
                            }
                            placeholder="Optional description"
                            rows={2}
                            className="w-full mt-1 px-3 py-2 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 resize-none"
                          />
                        </div>
                        <div className="col-span-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={newItemRegulatory}
                              onChange={(e) =>
                                setNewItemRegulatory(e.target.checked)
                              }
                              className="rounded border-gray-600 bg-[#0d1117] text-[var(--gold)] focus:ring-[var(--gold)]/50"
                            />
                            <Shield className="h-3.5 w-3.5 text-amber-400" />
                            <span className="text-sm text-gray-300">
                              Required regulatory item
                            </span>
                          </label>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          onClick={addFormItem}
                          disabled={!newItemTitle.trim()}
                        >
                          <Plus className="h-3.5 w-3.5 mr-1" />
                          Add
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-gray-700 text-gray-400 hover:text-white"
                          onClick={() => {
                            setShowNewItem(false);
                            resetNewItemFields();
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Form error */}
              {formError && (
                <p className="text-sm text-destructive">{formError}</p>
              )}

              {/* Form actions */}
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={resetForm}
                  disabled={formSaving}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={formSaving || !formName.trim()}
                >
                  {formSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : editingId ? (
                    "Update Template"
                  ) : (
                    "Create Template"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Template List */}
        {templates.length === 0 && !showForm ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No templates created yet. Create one to get started.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {templates.map((tpl) => (
              <Card
                key={tpl.id}
                className="border-gray-800 hover:bg-muted/30 transition-colors"
              >
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-base font-medium text-white">
                          {tpl.name}
                        </h3>
                        {tpl.has_regulatory_items && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            <Shield className="h-3 w-3" />
                            Regulatory
                          </span>
                        )}
                      </div>
                      {tpl.description && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {tpl.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span>{tpl.items_count} agenda items</span>
                        <span>
                          Created{" "}
                          {new Date(tpl.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(tpl.id)}
                        className="min-h-[36px] min-w-[36px]"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {deletingId === tpl.id ? (
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 text-xs border-red-500/30 text-red-400 hover:bg-red-500/20"
                            onClick={() => handleDelete(tpl.id)}
                            disabled={deleting}
                          >
                            {deleting ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              "Confirm"
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 text-xs border-gray-700 text-gray-400"
                            onClick={() => setDeletingId(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingId(tpl.id)}
                          className="min-h-[36px] min-w-[36px] text-gray-500 hover:text-red-400"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
