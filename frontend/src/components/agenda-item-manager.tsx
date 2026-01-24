"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Plus,
  GripVertical,
  Trash2,
  Edit,
  Clock,
  FileText,
  Check,
  X,
  Loader2,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { meetingsApi } from "@/lib/api";

export interface AgendaItem {
  id: number;
  title: string;
  description?: string | null;
  duration_minutes: number;
  order_index: number;
  presenter?: string | null;
  status: "pending" | "in_progress" | "completed" | "skipped";
}

interface AgendaItemManagerProps {
  meetingId: string;
  items: AgendaItem[];
  onItemsChange: (items: AgendaItem[]) => void;
  canEdit: boolean;
  meetingStatus: "scheduled" | "in_progress" | "completed" | "cancelled";
}

const statusConfig = {
  pending: { label: "Pending", color: "bg-muted text-muted-foreground" },
  in_progress: { label: "In Progress", color: "bg-blue-500/20 text-blue-400" },
  completed: { label: "Completed", color: "bg-green-500/20 text-green-400" },
  skipped: { label: "Skipped", color: "bg-amber-500/20 text-amber-400" },
};

export function AgendaItemManager({
  meetingId,
  items,
  onItemsChange,
  canEdit,
  meetingStatus,
}: AgendaItemManagerProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState(15);
  const [presenter, setPresenter] = useState("");

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setDuration(15);
    setPresenter("");
    setEditingId(null);
    setShowAddForm(false);
  };

  const handleAdd = async () => {
    if (!title.trim()) return;

    setSaving(true);
    try {
      const newItem = await meetingsApi.addAgendaItem(meetingId, {
        title: title.trim(),
        description: description.trim() || undefined,
        duration_minutes: duration,
        presenter: presenter.trim() || undefined,
      });

      onItemsChange([...items, newItem]);
      resetForm();
    } catch (err) {
      console.error("Failed to add agenda item:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (item: AgendaItem) => {
    setEditingId(item.id);
    setTitle(item.title);
    setDescription(item.description || "");
    setDuration(item.duration_minutes);
    setPresenter(item.presenter || "");
    setShowAddForm(false);
  };

  const handleSaveEdit = async () => {
    if (!editingId || !title.trim()) return;

    setSaving(true);
    try {
      const updated = await meetingsApi.updateAgendaItem(meetingId, editingId, {
        title: title.trim(),
        description: description.trim() || undefined,
        duration_minutes: duration,
        presenter: presenter.trim() || undefined,
      });

      onItemsChange(items.map((item) => (item.id === editingId ? updated : item)));
      resetForm();
    } catch (err) {
      console.error("Failed to update agenda item:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (itemId: number) => {
    setSaving(true);
    try {
      await meetingsApi.deleteAgendaItem(meetingId, itemId);
      onItemsChange(items.filter((item) => item.id !== itemId));
    } catch (err) {
      console.error("Failed to delete agenda item:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleMoveUp = async (index: number) => {
    if (index === 0) return;
    const newItems = [...items];
    [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];

    // Update order indices
    const reordered = newItems.map((item, i) => ({ ...item, order_index: i }));
    onItemsChange(reordered);

    try {
      await meetingsApi.reorderAgendaItems(
        meetingId,
        reordered.map((item) => ({ id: item.id, order_index: item.order_index }))
      );
    } catch (err) {
      console.error("Failed to reorder items:", err);
      onItemsChange(items); // Revert on error
    }
  };

  const handleMoveDown = async (index: number) => {
    if (index === items.length - 1) return;
    const newItems = [...items];
    [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];

    const reordered = newItems.map((item, i) => ({ ...item, order_index: i }));
    onItemsChange(reordered);

    try {
      await meetingsApi.reorderAgendaItems(
        meetingId,
        reordered.map((item) => ({ id: item.id, order_index: item.order_index }))
      );
    } catch (err) {
      console.error("Failed to reorder items:", err);
      onItemsChange(items);
    }
  };

  const totalDuration = items.reduce((sum, item) => sum + item.duration_minutes, 0);
  const sortedItems = [...items].sort((a, b) => a.order_index - b.order_index);
  const isEditable = canEdit && meetingStatus === "scheduled";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Agenda
          <span className="text-sm font-normal text-muted-foreground">
            ({items.length} items, {totalDuration} min)
          </span>
        </CardTitle>
        {isEditable && !showAddForm && !editingId && (
          <Button variant="outline" size="sm" onClick={() => setShowAddForm(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Item
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Add/Edit Form */}
        {(showAddForm || editingId) && (
          <div className="p-3 border rounded-lg bg-muted/30 space-y-3">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Agenda item title"
              className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              autoFocus
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              rows={2}
              className="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Duration (min)</label>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  min={1}
                  max={180}
                  className="w-full mt-1 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Presenter</label>
                <input
                  type="text"
                  value={presenter}
                  onChange={(e) => setPresenter(e.target.value)}
                  placeholder="Optional"
                  className="w-full mt-1 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={resetForm} disabled={saving}>
                <X className="h-4 w-4 mr-1" />
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={editingId ? handleSaveEdit : handleAdd}
                disabled={saving || !title.trim()}
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <Check className="h-4 w-4 mr-1" />
                )}
                {editingId ? "Save" : "Add"}
              </Button>
            </div>
          </div>
        )}

        {/* Items List */}
        {sortedItems.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No agenda items yet.
            {isEditable && " Click 'Add Item' to create one."}
          </p>
        ) : (
          <div className="space-y-2">
            {sortedItems.map((item, index) => (
              <div
                key={item.id}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg border transition-colors",
                  item.status === "in_progress" && "border-blue-500/50 bg-blue-500/5",
                  item.status === "completed" && "opacity-60"
                )}
              >
                {/* Reorder Controls */}
                {isEditable && (
                  <div className="flex flex-col gap-0.5">
                    <button
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0 || saving}
                      className="p-0.5 rounded hover:bg-muted disabled:opacity-30"
                    >
                      <ChevronUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleMoveDown(index)}
                      disabled={index === items.length - 1 || saving}
                      className="p-0.5 rounded hover:bg-muted disabled:opacity-30"
                    >
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </div>
                )}

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{item.title}</span>
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-xs font-medium",
                        statusConfig[item.status].color
                      )}
                    >
                      {statusConfig[item.status].label}
                    </span>
                  </div>
                  {item.description && (
                    <p className="text-xs text-muted-foreground mb-1">{item.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {item.duration_minutes} min
                    </span>
                    {item.presenter && <span>Presenter: {item.presenter}</span>}
                  </div>
                </div>

                {/* Actions */}
                {isEditable && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEdit(item)}
                      className="p-1.5 rounded hover:bg-muted"
                      disabled={saving}
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-1.5 rounded hover:bg-destructive/10 text-destructive"
                      disabled={saving}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
