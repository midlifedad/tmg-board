"use client";

import { use, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowLeft,
  Calendar,
  Clock,
  MapPin,
  Video,
  Plus,
  ExternalLink,
  User,
  Link as LinkIcon,
  Loader2,
  Pencil,
  XCircle,
  Trash2,
  GripVertical,
  Check,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { meetingsApi, authApi, api, type Meeting as ApiMeeting, type AgendaItem as ApiAgendaItem } from "@/lib/api";
import { EditMeetingModal } from "@/components/edit-meeting-modal";
import { getTimezoneAbbr } from "@/lib/timezone";

type MeetingStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

interface MeetingDetail {
  id: string;
  title: string;
  date: string;
  time: string;
  duration: string;
  durationMinutes?: number | null;
  location: string;
  isVirtual: boolean;
  meetingLink: string;
  status: MeetingStatus;
  description: string;
  createdBy: string;
  agenda: Array<{
    id: string;
    order: number;
    title: string;
    description: string | null;
    duration: string;
    durationMinutes: number;
    presenter: string | null;
    itemType: "information" | "discussion" | "decision_required" | "consent_agenda";
    timeSlot: string;
    relatedDecision?: { id: string; title: string };
  }>;
  documents: Array<{ id: string; title: string; type: string }>;
  recording: string | null;
}

const statusColors = {
  scheduled: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  in_progress: "bg-green-500/20 text-green-400 border-green-500/30",
  completed: "bg-muted text-muted-foreground border-border",
  cancelled: "bg-red-500/20 text-red-400 border-red-500/30",
};

const typeColors: Record<string, string> = {
  information: "border-l-blue-500",
  discussion: "border-l-amber-500",
  decision_required: "border-l-orange-600",
  consent_agenda: "border-l-green-500",
};

const typeLabels: Record<string, string> = {
  information: "Information",
  discussion: "Discussion",
  decision_required: "Decision Required",
  consent_agenda: "Consent Agenda",
};

export default function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session } = useSession();
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [showAddAgenda, setShowAddAgenda] = useState(false);
  const [newAgendaTitle, setNewAgendaTitle] = useState("");
  const [newAgendaDuration, setNewAgendaDuration] = useState("");
  const [newAgendaPresenter, setNewAgendaPresenter] = useState("");
  const [newAgendaType, setNewAgendaType] = useState("information");
  const [addingAgenda, setAddingAgenda] = useState(false);
  const [deletingAgendaId, setDeletingAgendaId] = useState<string | null>(null);

  // Inline editing state
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDuration, setEditDuration] = useState("");
  const [editType, setEditType] = useState<string>("information");
  const [editPresenter, setEditPresenter] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // Drag-to-reorder state
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  const [dragOverItemId, setDragOverItemId] = useState<string | null>(null);

  // Timezone
  const [tzAbbr, setTzAbbr] = useState("PT");
  const [ianaZone, setIanaZone] = useState("America/Los_Angeles");

  const fetchMeeting = useCallback(async () => {
    try {
      setLoading(true);
      const email = session?.user?.email;
      if (email) {
        api.setUserEmail(email);
      }
      // Fetch timezone in parallel with meeting data
      const [meetingData, agendaData] = await Promise.all([
        meetingsApi.get(id),
        meetingsApi.getAgenda(id),
      ]);

      try {
        const me = await authApi.getCurrentUser();
        const tz = me.effective_timezone || "America/Los_Angeles";
        setIanaZone(tz);
        setTzAbbr(getTimezoneAbbr(tz));
      } catch {
        // Fall back to default
      }

      // Extract date and time from the raw string to avoid UTC conversion shifts
      const parts = meetingData.scheduled_date.split("T");
      const dateStr = parts[0];
      const time = parts[1]?.slice(0, 5) || "00:00";
      const isVirtual = meetingData.meeting_link != null ||
                       meetingData.location.toLowerCase().includes("virtual") ||
                       meetingData.location.toLowerCase().includes("zoom");

      // Calculate time slots from meeting start time + cumulative durations
      let cumulativeMinutes = 0;
      const startTimeParts = time.split(":");
      const startTotalMinutes = parseInt(startTimeParts[0]) * 60 + parseInt(startTimeParts[1]);

      const agendaWithSlots = agendaData.map((item, index) => {
        const slotStart = startTotalMinutes + cumulativeMinutes;
        const itemDuration = item.duration_minutes || 0;
        const slotEnd = slotStart + itemDuration;
        cumulativeMinutes += itemDuration;

        const formatTime = (totalMin: number) => {
          const h = Math.floor(totalMin / 60) % 24;
          const m = totalMin % 60;
          return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
        };

        return {
          id: String(item.id),
          order: item.order_index ?? index + 1,
          title: item.title,
          description: item.description || null,
          duration: item.duration_minutes ? `${item.duration_minutes} min` : "",
          durationMinutes: item.duration_minutes || 0,
          presenter: item.presenter || null,
          itemType: (item.item_type || "information") as "information" | "discussion" | "decision_required" | "consent_agenda",
          timeSlot: itemDuration > 0 ? `${formatTime(slotStart)}-${formatTime(slotEnd)}` : "",
          relatedDecision: item.decision_id
            ? { id: String(item.decision_id), title: "Related Decision" }
            : undefined,
        };
      });

      setMeeting({
        id: String(meetingData.id),
        title: meetingData.title,
        date: dateStr,
        time: time,
        duration: meetingData.duration_minutes
          ? meetingData.duration_minutes >= 60
            ? `${Math.floor(meetingData.duration_minutes / 60)}h${meetingData.duration_minutes % 60 ? ` ${meetingData.duration_minutes % 60}m` : ""}`
            : `${meetingData.duration_minutes} min`
          : "Not set",
        durationMinutes: meetingData.duration_minutes,
        location: meetingData.location,
        isVirtual: isVirtual,
        meetingLink: meetingData.meeting_link || "",
        status: meetingData.status,
        description: meetingData.description || "",
        createdBy: `User ${meetingData.created_by_id}`,
        agenda: agendaWithSlots,
        documents: [],
        recording: null,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load meeting");
    } finally {
      setLoading(false);
    }
  }, [id, session?.user?.email]);

  useEffect(() => {
    fetchMeeting();
  }, [fetchMeeting]);

  const handleCancelMeeting = async () => {
    if (!meeting) return;
    setCancelling(true);
    try {
      await meetingsApi.cancel(meeting.id);
      await fetchMeeting();
    } catch (err) {
      console.error("Failed to cancel meeting:", err);
    } finally {
      setCancelling(false);
      setShowCancelConfirm(false);
    }
  };

  const handleAddAgendaItem = async () => {
    if (!meeting || !newAgendaTitle.trim()) return;
    setAddingAgenda(true);
    try {
      await meetingsApi.addAgendaItem(String(meeting.id), {
        title: newAgendaTitle.trim(),
        duration_minutes: newAgendaDuration ? parseInt(newAgendaDuration) : undefined,
        item_type: newAgendaType as "information" | "discussion" | "decision_required" | "consent_agenda",
      });
      setNewAgendaTitle("");
      setNewAgendaDuration("");
      setNewAgendaPresenter("");
      setNewAgendaType("information");
      setShowAddAgenda(false);
      await fetchMeeting();
    } catch (err) {
      console.error("Failed to add agenda item:", err);
    } finally {
      setAddingAgenda(false);
    }
  };

  const handleDeleteAgendaItem = async (itemId: string) => {
    if (!meeting) return;
    setDeletingAgendaId(itemId);
    try {
      await meetingsApi.deleteAgendaItem(meeting.id, parseInt(itemId));
      await fetchMeeting();
    } catch (err) {
      console.error("Failed to delete agenda item:", err);
    } finally {
      setDeletingAgendaId(null);
    }
  };

  // Inline editing handlers
  const handleStartEdit = (item: MeetingDetail["agenda"][0]) => {
    setEditingItemId(item.id);
    setEditTitle(item.title);
    setEditDuration(String(item.durationMinutes || ""));
    setEditType(item.itemType);
    setEditPresenter(item.presenter || "");
  };

  const handleCancelEdit = () => {
    setEditingItemId(null);
    setEditTitle("");
    setEditDuration("");
    setEditType("information");
    setEditPresenter("");
  };

  const handleSaveEdit = async () => {
    if (!meeting || !editingItemId) return;
    setSavingEdit(true);
    try {
      await meetingsApi.updateAgendaItem(meeting.id, parseInt(editingItemId), {
        title: editTitle.trim(),
        duration_minutes: editDuration ? parseInt(editDuration) : undefined,
        item_type: editType as "information" | "discussion" | "decision_required" | "consent_agenda",
      });
      setEditingItemId(null);
      await fetchMeeting();
    } catch (err) {
      console.error("Failed to update agenda item:", err);
    } finally {
      setSavingEdit(false);
    }
  };

  // Drag-to-reorder handlers
  const handleDragStart = (e: React.DragEvent, itemId: string) => {
    setDraggedItemId(itemId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, itemId: string) => {
    e.preventDefault();
    setDragOverItemId(itemId);
  };

  const handleDragEnd = () => {
    setDraggedItemId(null);
    setDragOverItemId(null);
  };

  const handleDrop = async (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (!meeting || !draggedItemId || draggedItemId === targetId) {
      setDraggedItemId(null);
      setDragOverItemId(null);
      return;
    }

    const items = [...meeting.agenda];
    const draggedIndex = items.findIndex(i => i.id === draggedItemId);
    const targetIndex = items.findIndex(i => i.id === targetId);

    const [removed] = items.splice(draggedIndex, 1);
    items.splice(targetIndex, 0, removed);

    // Optimistic update
    setMeeting({ ...meeting, agenda: items.map((item, i) => ({ ...item, order: i + 1 })) });

    try {
      await meetingsApi.reorderAgendaItems(meeting.id, items.map((item, i) => ({
        id: parseInt(item.id),
        order_index: i
      })));
      await fetchMeeting();
    } catch (err) {
      console.error("Failed to reorder:", err);
      await fetchMeeting(); // Rollback
    }

    setDraggedItemId(null);
    setDragOverItemId(null);
  };

  // .ics download helper
  const downloadIcs = (mtg: MeetingDetail) => {
    const pad = (n: number) => String(n).padStart(2, "0");
    const dateParts = mtg.date.split("-");
    const timeParts = mtg.time.split(":");
    const startDate = `${dateParts[0]}${dateParts[1]}${dateParts[2]}T${timeParts[0]}${timeParts[1]}00`;

    const dur = mtg.durationMinutes || 60;
    const endTotalMin = parseInt(timeParts[0]) * 60 + parseInt(timeParts[1]) + dur;
    const endH = Math.floor(endTotalMin / 60) % 24;
    const endM = endTotalMin % 60;
    const endDate = `${dateParts[0]}${dateParts[1]}${dateParts[2]}T${pad(endH)}${pad(endM)}00`;

    const ics = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//TMG Board//EN",
      "BEGIN:VEVENT",
      `DTSTART;TZID=${ianaZone}:${startDate}`,
      `DTEND;TZID=${ianaZone}:${endDate}`,
      `SUMMARY:${mtg.title}`,
      `LOCATION:${mtg.location}`,
      mtg.description ? `DESCRIPTION:${mtg.description.replace(/\n/g, "\\n")}` : "",
      "END:VEVENT",
      "END:VCALENDAR",
    ].filter(Boolean).join("\r\n");

    const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${mtg.title.replace(/[^a-zA-Z0-9]/g, "_")}.ics`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin = userRole === "admin" || userRole === "chair";

  // Google Calendar URL
  const googleCalendarUrl = (() => {
    if (!meeting) return "#";
    const dur = meeting.durationMinutes || 60;
    const startH = parseInt(meeting.time.split(":")[0]);
    const startM = parseInt(meeting.time.split(":")[1]);
    const endTotalM = startH * 60 + startM + dur;
    const endH = Math.floor(endTotalM / 60) % 24;
    const endM = endTotalM % 60;
    const dateCompact = meeting.date.replace(/-/g, "");
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(meeting.title)}&dates=${dateCompact}T${meeting.time.replace(":", "")}00/${dateCompact}T${String(endH).padStart(2, "0")}${String(endM).padStart(2, "0")}00&location=${encodeURIComponent(meeting.location)}&ctz=${encodeURIComponent(ianaZone)}`;
  })();

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error || !meeting) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error || "Meeting not found"}</p>
          <Button asChild>
            <Link href="/meetings">Back to Meetings</Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Back Link */}
        <Link
          href="/meetings"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Meetings
        </Link>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{meeting.title}</h1>
              <span
                className={cn(
                  "inline-flex px-2 py-1 rounded text-xs font-medium capitalize border",
                  statusColors[meeting.status]
                )}
              >
                {meeting.status.replace("_", " ")}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                {new Date(meeting.date).toLocaleDateString("en-US", {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                {meeting.time} {tzAbbr} ({meeting.duration})
              </div>
              <div className="flex items-center gap-1.5">
                {meeting.isVirtual ? (
                  <Video className="h-4 w-4" />
                ) : (
                  <MapPin className="h-4 w-4" />
                )}
                {meeting.location}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isChairOrAdmin && meeting.status === "scheduled" && (
              <>
                <Button variant="outline" size="sm" onClick={() => setShowEditModal(true)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setShowCancelConfirm(true)}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Cancel Meeting
                </Button>
              </>
            )}
            {meeting.status === "scheduled" && meeting.meetingLink && (
              <Button asChild>
                <a
                  href={meeting.meetingLink}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Video className="h-4 w-4 mr-2" />
                  Join Meeting
                  <ExternalLink className="h-3 w-3 ml-1" />
                </a>
              </Button>
            )}
          </div>
        </div>

        {/* Description */}
        {meeting.description && (
          <Card>
            <CardContent className="py-4">
              <p className="text-sm text-muted-foreground whitespace-pre-line">{meeting.description}</p>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agenda */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Agenda</CardTitle>
                {isChairOrAdmin && meeting.status === "scheduled" && (
                  <Button variant="outline" size="sm" onClick={() => setShowAddAgenda(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Item
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-1">
                {meeting.agenda.map((item) => {
                  const isEditing = editingItemId === item.id;
                  const isDragging = draggedItemId === item.id;
                  const isDragOver = dragOverItemId === item.id && draggedItemId !== item.id;

                  if (isEditing) {
                    // Inline edit mode
                    return (
                      <div
                        key={item.id}
                        className={cn(
                          "p-4 rounded-md border-l-[3px] border border-[var(--gold)]",
                          typeColors[item.itemType] || "border-l-blue-500"
                        )}
                      >
                        <div className="space-y-3">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            placeholder="Item title"
                            className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === "Escape") handleCancelEdit();
                              if (e.key === "Enter") handleSaveEdit();
                            }}
                          />
                          <div className="flex gap-3 flex-wrap">
                            <input
                              type="number"
                              value={editDuration}
                              onChange={(e) => setEditDuration(e.target.value)}
                              placeholder="Duration (min)"
                              className="w-32 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                            <select
                              value={editType}
                              onChange={(e) => setEditType(e.target.value)}
                              className="h-9 px-2 rounded-md border bg-background text-sm"
                            >
                              <option value="information">Information</option>
                              <option value="discussion">Discussion</option>
                              <option value="decision_required">Decision Required</option>
                              <option value="consent_agenda">Consent Agenda</option>
                            </select>
                            <input
                              type="text"
                              value={editPresenter}
                              onChange={(e) => setEditPresenter(e.target.value)}
                              placeholder="Presenter (display only)"
                              className="flex-1 min-w-[140px] h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                          </div>
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="min-h-[44px]"
                              onClick={handleCancelEdit}
                              disabled={savingEdit}
                            >
                              <X className="h-4 w-4 mr-1" />
                              Cancel
                            </Button>
                            <Button
                              size="sm"
                              className="min-h-[44px]"
                              onClick={handleSaveEdit}
                              disabled={savingEdit || !editTitle.trim()}
                            >
                              {savingEdit ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-1" />
                              ) : (
                                <Check className="h-4 w-4 mr-1" />
                              )}
                              Save
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  }

                  // Display mode
                  return (
                    <div
                      key={item.id}
                      className={cn(
                        "flex items-start gap-4 p-4 rounded-md border-l-[3px] hover:bg-muted/30 transition-colors group",
                        typeColors[item.itemType] || "border-l-blue-500",
                        isDragging && "opacity-50",
                        isDragOver && "border-t-2 border-t-[var(--gold)]"
                      )}
                      draggable={isChairOrAdmin && meeting.status === "scheduled"}
                      onDragStart={(e) => handleDragStart(e, item.id)}
                      onDragOver={(e) => handleDragOver(e, item.id)}
                      onDrop={(e) => handleDrop(e, item.id)}
                      onDragEnd={handleDragEnd}
                    >
                      {/* Drag handle (chair/admin only, scheduled meetings) */}
                      {isChairOrAdmin && meeting.status === "scheduled" && (
                        <div className="flex-shrink-0 cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground p-1 min-h-[44px] min-w-[44px] flex items-center justify-center">
                          <GripVertical className="h-4 w-4" />
                        </div>
                      )}

                      {/* Time slot column */}
                      <div className="flex-shrink-0 w-24 text-right">
                        {item.timeSlot && (
                          <span className="text-xs font-mono text-muted-foreground">{item.timeSlot}</span>
                        )}
                        <div className="text-xs text-muted-foreground mt-0.5">{item.duration}</div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.order}.</span>
                          {isChairOrAdmin && meeting.status === "scheduled" ? (
                            <p
                              className="font-medium cursor-pointer hover:text-[var(--gold)] transition-colors"
                              onClick={() => handleStartEdit(item)}
                            >
                              {item.title}
                            </p>
                          ) : (
                            <p className="font-medium">{item.title}</p>
                          )}
                        </div>
                        {item.presenter && (
                          <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                            <User className="h-3 w-3" />
                            {item.presenter}
                          </p>
                        )}
                        {item.relatedDecision && (
                          <Link
                            href={`/decisions/${item.relatedDecision.id}`}
                            className="inline-flex items-center gap-1 text-xs text-[var(--gold)] hover:underline mt-1"
                          >
                            <LinkIcon className="h-3 w-3" />
                            {item.relatedDecision.title}
                          </Link>
                        )}
                      </div>

                      {/* Type badge (small, subtle) */}
                      <span className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground">
                        {typeLabels[item.itemType]}
                      </span>

                      {/* Post-meeting status badge */}
                      {meeting.status === "completed" && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                          Discussed
                        </span>
                      )}

                      {/* Chair controls: delete button */}
                      {isChairOrAdmin && meeting.status === "scheduled" && (
                        <button
                          onClick={() => handleDeleteAgendaItem(item.id)}
                          disabled={deletingAgendaId === item.id}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                        >
                          {deletingAgendaId === item.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </div>
                  );
                })}

                {meeting.agenda.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No agenda items yet.
                  </p>
                )}

                {/* Inline Add Agenda Item Form */}
                {showAddAgenda && (
                  <div className="border rounded-md p-4 mt-3 space-y-3">
                    <input
                      type="text"
                      value={newAgendaTitle}
                      onChange={(e) => setNewAgendaTitle(e.target.value)}
                      placeholder="Agenda item title"
                      className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      autoFocus
                    />
                    <div className="flex gap-3 flex-wrap">
                      <input
                        type="number"
                        value={newAgendaDuration}
                        onChange={(e) => setNewAgendaDuration(e.target.value)}
                        placeholder="Duration (min)"
                        className="w-32 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <select
                        value={newAgendaType}
                        onChange={(e) => setNewAgendaType(e.target.value)}
                        className="h-9 px-2 rounded-md border bg-background text-sm"
                      >
                        <option value="information">Information</option>
                        <option value="discussion">Discussion</option>
                        <option value="decision_required">Decision Required</option>
                        <option value="consent_agenda">Consent Agenda</option>
                      </select>
                      <input
                        type="text"
                        value={newAgendaPresenter}
                        onChange={(e) => setNewAgendaPresenter(e.target.value)}
                        placeholder="Presenter (optional)"
                        className="flex-1 min-w-[140px] h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="min-h-[44px]"
                        onClick={() => {
                          setShowAddAgenda(false);
                          setNewAgendaTitle("");
                          setNewAgendaDuration("");
                          setNewAgendaPresenter("");
                          setNewAgendaType("information");
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="min-h-[44px]"
                        onClick={handleAddAgendaItem}
                        disabled={addingAgenda || !newAgendaTitle.trim()}
                      >
                        {addingAgenda ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-1" />
                        ) : (
                          <Plus className="h-4 w-4 mr-1" />
                        )}
                        Add
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Add to Calendar */}
            {meeting.status === "scheduled" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Add to Calendar</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {/* Google Calendar */}
                  <Button variant="outline" className="w-full min-h-[44px]" asChild>
                    <a href={googleCalendarUrl} target="_blank" rel="noopener noreferrer">
                      <Calendar className="h-4 w-4 mr-2" />
                      Google Calendar
                    </a>
                  </Button>
                  {/* Apple Calendar .ics download */}
                  <Button
                    variant="outline"
                    className="w-full min-h-[44px]"
                    onClick={() => downloadIcs(meeting)}
                  >
                    <Calendar className="h-4 w-4 mr-2" />
                    Apple Calendar (.ics)
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Recording */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recording</CardTitle>
              </CardHeader>
              <CardContent>
                {meeting.recording ? (
                  <Button variant="outline" className="w-full min-h-[44px]">
                    <Video className="h-4 w-4 mr-2" />
                    Watch Recording
                  </Button>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    {meeting.status === "completed"
                      ? "No recording available"
                      : "Recording will be available after the meeting"}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Dialog */}
      {showCancelConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => !cancelling && setShowCancelConfirm(false)}
          />
          <Card className="relative z-10 w-full max-w-sm mx-4 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Cancel Meeting</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Are you sure you want to cancel &ldquo;{meeting.title}&rdquo;? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowCancelConfirm(false)}
                  disabled={cancelling}
                >
                  Keep Meeting
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleCancelMeeting}
                  disabled={cancelling}
                >
                  {cancelling ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <XCircle className="h-4 w-4 mr-2" />
                  )}
                  Cancel Meeting
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit Meeting Modal */}
      <EditMeetingModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={() => fetchMeeting()}
        meeting={meeting ? {
          id: meeting.id,
          title: meeting.title,
          scheduled_date: `${meeting.date}T${meeting.time}`,
          duration_minutes: meeting.durationMinutes,
          location: meeting.isVirtual ? `Virtual - ${meeting.meetingLink}` : meeting.location,
        } : null}
      />
    </AppShell>
  );
}
