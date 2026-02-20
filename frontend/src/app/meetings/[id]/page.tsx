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
  FileText,
  ExternalLink,
  User,
  Link as LinkIcon,
  Loader2,
  Pencil,
  XCircle,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { meetingsApi, api, type Meeting as ApiMeeting, type AgendaItem as ApiAgendaItem } from "@/lib/api";
import { EditMeetingModal } from "@/components/edit-meeting-modal";

type MeetingStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

interface MeetingDetail {
  id: string;
  title: string;
  date: string;
  time: string;
  duration: string;
  location: string;
  isVirtual: boolean;
  meetingLink: string;
  status: MeetingStatus;
  createdBy: string;
  agenda: Array<{
    id: string;
    order: number;
    title: string;
    duration: string;
    presenter: string | null;
    relatedDocument?: { id: string; title: string };
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
  const [addingAgenda, setAddingAgenda] = useState(false);
  const [deletingAgendaId, setDeletingAgendaId] = useState<string | null>(null);

  const fetchMeeting = useCallback(async () => {
    try {
      setLoading(true);
      const email = session?.user?.email;
      if (email) {
        api.setUserEmail(email);
      }
      const [meetingData, agendaData] = await Promise.all([
        meetingsApi.get(id),
        meetingsApi.getAgenda(id),
      ]);

      const dateObj = new Date(meetingData.scheduled_date);
      const time = dateObj.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      const dateStr = dateObj.toISOString().split("T")[0];
      const isVirtual = meetingData.meeting_link != null ||
                       meetingData.location.toLowerCase().includes("virtual") ||
                       meetingData.location.toLowerCase().includes("zoom");

      setMeeting({
        id: String(meetingData.id),
        title: meetingData.title,
        date: dateStr,
        time: time,
        duration: "2 hours",
        location: meetingData.location,
        isVirtual: isVirtual,
        meetingLink: meetingData.meeting_link || "",
        status: meetingData.status,
        createdBy: `User ${meetingData.created_by_id}`,
        agenda: agendaData.map((item, index) => ({
          id: String(item.id),
          order: item.order_index ?? index + 1,
          title: item.title,
          duration: item.duration_minutes ? `${item.duration_minutes} min` : "",
          presenter: item.presenter || null,
          relatedDecision: item.decision_id
            ? { id: String(item.decision_id), title: "Related Decision" }
            : undefined,
        })),
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
      setShowCancelConfirm(false);
    } catch (err) {
      console.error("Failed to cancel meeting:", err);
    } finally {
      setCancelling(false);
    }
  };

  const handleAddAgendaItem = async () => {
    if (!meeting || !newAgendaTitle.trim()) return;
    setAddingAgenda(true);
    try {
      await meetingsApi.addAgendaItem(meeting.id, {
        title: newAgendaTitle.trim(),
        duration_minutes: newAgendaDuration ? parseInt(newAgendaDuration) : undefined,
        presenter: newAgendaPresenter.trim() || undefined,
      });
      setNewAgendaTitle("");
      setNewAgendaDuration("");
      setNewAgendaPresenter("");
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

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin = userRole === "admin" || userRole === "chair";

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
                {meeting.time} ({meeting.duration})
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
                {meeting.agenda.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-4 p-3 rounded-md hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                      {item.order}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{item.title}</p>
                        {item.duration && (
                          <span className="text-xs text-muted-foreground">
                            ({item.duration})
                          </span>
                        )}
                      </div>
                      {item.presenter && (
                        <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                          <User className="h-3 w-3" />
                          {item.presenter}
                        </p>
                      )}
                      {(item.relatedDocument || item.relatedDecision) && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {item.relatedDocument && (
                            <Link
                              href={`/documents/${item.relatedDocument.id}`}
                              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                            >
                              <FileText className="h-3 w-3" />
                              {item.relatedDocument.title}
                            </Link>
                          )}
                          {item.relatedDecision && (
                            <Link
                              href={`/decisions/${item.relatedDecision.id}`}
                              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                            >
                              <LinkIcon className="h-3 w-3" />
                              {item.relatedDecision.title}
                            </Link>
                          )}
                        </div>
                      )}
                    </div>
                    {isChairOrAdmin && meeting.status === "scheduled" && (
                      <button
                        onClick={() => handleDeleteAgendaItem(item.id)}
                        disabled={deletingAgendaId === item.id}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive p-1"
                      >
                        {deletingAgendaId === item.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>
                ))}

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
                    <div className="flex gap-3">
                      <input
                        type="number"
                        value={newAgendaDuration}
                        onChange={(e) => setNewAgendaDuration(e.target.value)}
                        placeholder="Duration (min)"
                        className="w-32 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <input
                        type="text"
                        value={newAgendaPresenter}
                        onChange={(e) => setNewAgendaPresenter(e.target.value)}
                        placeholder="Presenter (optional)"
                        className="flex-1 h-9 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowAddAgenda(false);
                          setNewAgendaTitle("");
                          setNewAgendaDuration("");
                          setNewAgendaPresenter("");
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
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
            {/* Meeting Documents */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Meeting Documents</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {meeting.documents.map((doc) => (
                  <Link
                    key={doc.id}
                    href={`/documents/${doc.id}`}
                    className="flex items-center gap-2 py-2 text-sm hover:text-primary transition-colors"
                  >
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    {doc.title}
                  </Link>
                ))}
              </CardContent>
            </Card>

            {/* Add to Calendar */}
            {meeting.status === "scheduled" && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Add to Calendar</CardTitle>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" className="w-full" asChild>
                    <a
                      href={`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(meeting.title)}&dates=${meeting.date.replace(/-/g, "")}T${meeting.time.replace(":", "")}00/${meeting.date.replace(/-/g, "")}T${(parseInt(meeting.time.split(":")[0]) + 2).toString().padStart(2, "0")}${meeting.time.split(":")[1]}00&location=${encodeURIComponent(meeting.location)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Calendar className="h-4 w-4 mr-2" />
                      Add to Google Calendar
                    </a>
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
                  <Button variant="outline" className="w-full">
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
          location: meeting.isVirtual ? `Virtual - ${meeting.meetingLink}` : meeting.location,
        } : null}
      />
    </AppShell>
  );
}
