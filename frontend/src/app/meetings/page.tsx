"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus,
  MapPin,
  Clock,
  Video,
  FileText,
  Loader2,
  CheckCircle2,
  Scale,
} from "lucide-react";
import { meetingsApi, authApi, api, type Meeting as ApiMeeting } from "@/lib/api";
import { CreateMeetingModal } from "@/components/create-meeting-modal";
import { getTimezoneAbbr } from "@/lib/timezone";

interface Meeting {
  id: string;
  title: string;
  date: string;
  time: string;
  duration: string;
  durationMinutes: number | null;
  location: string;
  isVirtual: boolean;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  agendaItemsCount: number;
  hasMinutes: boolean;
  decisionsCount: number;
}

export default function MeetingsPage() {
  const { data: session } = useSession();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [tzAbbr, setTzAbbr] = useState("PT");
  const [ianaZone, setIanaZone] = useState("America/Los_Angeles");

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }

        // Fetch user's effective timezone
        try {
          const me = await authApi.getCurrentUser();
          const tz = me.effective_timezone || "America/Los_Angeles";
          setIanaZone(tz);
          setTzAbbr(getTimezoneAbbr(tz));
        } catch {
          // Fall back to default
        }

        const data = await meetingsApi.list();
        const transformed: Meeting[] = data.map((meeting) => {
          // Extract date and time from the raw string to avoid UTC conversion shifts
          const parts = meeting.scheduled_date.split("T");
          const dateStr = parts[0];
          const time = parts[1]?.slice(0, 5) || "00:00";
          const isVirtual =
            meeting.meeting_link != null ||
            meeting.location.toLowerCase().includes("virtual") ||
            meeting.location.toLowerCase().includes("zoom");
          return {
            id: String(meeting.id),
            title: meeting.title,
            date: dateStr,
            time: time,
            duration: meeting.duration_minutes
              ? meeting.duration_minutes >= 60
                ? `${Math.floor(meeting.duration_minutes / 60)}h${meeting.duration_minutes % 60 ? ` ${meeting.duration_minutes % 60}m` : ""}`
                : `${meeting.duration_minutes} min`
              : "",
            durationMinutes: meeting.duration_minutes ?? null,
            location: meeting.location,
            isVirtual: isVirtual,
            status: meeting.status,
            agendaItemsCount:
              (meeting as ApiMeeting & { agenda_items_count?: number })
                .agenda_items_count ?? 0,
            hasMinutes:
              (meeting as ApiMeeting & { has_minutes?: boolean })
                .has_minutes ?? false,
            decisionsCount:
              (meeting as ApiMeeting & { decisions_count?: number })
                .decisions_count ?? 0,
          };
        });
        setMeetings(transformed);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load meetings"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();
  }, [session?.user?.email]);

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin =
    userRole === "admin" || userRole === "chair" || !session;

  const refetchMeetings = async () => {
    try {
      const data = await meetingsApi.list();
      const transformed: Meeting[] = data.map((meeting) => {
        const parts = meeting.scheduled_date.split("T");
        const dateStr = parts[0];
        const time = parts[1]?.slice(0, 5) || "00:00";
        const isVirtual =
          meeting.meeting_link != null ||
          meeting.location.toLowerCase().includes("virtual") ||
          meeting.location.toLowerCase().includes("zoom");
        return {
          id: String(meeting.id),
          title: meeting.title,
          date: dateStr,
          time: time,
          duration: meeting.duration_minutes
            ? meeting.duration_minutes >= 60
              ? `${Math.floor(meeting.duration_minutes / 60)}h${meeting.duration_minutes % 60 ? ` ${meeting.duration_minutes % 60}m` : ""}`
              : `${meeting.duration_minutes} min`
            : "",
          durationMinutes: meeting.duration_minutes ?? null,
          location: meeting.location,
          isVirtual: isVirtual,
          status: meeting.status,
          agendaItemsCount:
            (meeting as ApiMeeting & { agenda_items_count?: number })
              .agenda_items_count ?? 0,
          hasMinutes:
            (meeting as ApiMeeting & { has_minutes?: boolean }).has_minutes ??
            false,
          decisionsCount:
            (meeting as ApiMeeting & { decisions_count?: number })
              .decisions_count ?? 0,
        };
      });
      setMeetings(transformed);
    } catch (err) {
      console.error("Failed to refetch meetings:", err);
    }
  };

  const upcomingMeetings = meetings
    .filter((m) => m.status === "scheduled" || m.status === "in_progress")
    .sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  const pastMeetings = meetings
    .filter((m) => m.status === "completed")
    .sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
              <span>Meetings</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            <h1 className="text-3xl font-light">Meetings</h1>
          </div>
          <div className="flex items-center gap-2">
            {isChairOrAdmin && (
              <Button
                onClick={() => setShowCreateModal(true)}
                className="min-h-[44px]"
              >
                <Plus className="h-4 w-4 mr-2" />
                Schedule Meeting
              </Button>
            )}
          </div>
        </div>

        {/* List View */}
        <div className="space-y-8">
          {/* Upcoming Meetings */}
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] flex items-center gap-3 mb-4">
              <span>Upcoming Meetings</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            {upcomingMeetings.length > 0 ? (
              <div className="space-y-3">
                {upcomingMeetings.map((meeting) => (
                  <UpcomingMeetingCard key={meeting.id} meeting={meeting} tzAbbr={tzAbbr} />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  No upcoming meetings scheduled.
                </CardContent>
              </Card>
            )}
          </div>

          {/* Past Meetings */}
          {pastMeetings.length > 0 && (
            <div>
              <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] flex items-center gap-3 mb-4">
                <span>Past Meetings</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              <div className="space-y-3">
                {pastMeetings.map((meeting) => (
                  <PastMeetingCard key={meeting.id} meeting={meeting} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Meeting Modal */}
      <CreateMeetingModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={refetchMeetings}
      />
    </AppShell>
  );
}

function formatMeetingDate(dateStr: string): string {
  // Parse the date string (YYYY-MM-DD) without timezone shifts
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function getMonthAbbrev(dateStr: string): string {
  const [year, month] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, 1);
  return date.toLocaleDateString("en-US", { month: "short" });
}

function getDayOfMonth(dateStr: string): string {
  const [, , day] = dateStr.split("-");
  return String(parseInt(day, 10));
}

// ---------- Upcoming Meeting Card ----------

interface UpcomingMeetingCardProps {
  meeting: Meeting;
  tzAbbr: string;
}

function UpcomingMeetingCard({ meeting, tzAbbr }: UpcomingMeetingCardProps) {
  const dateDisplay = formatMeetingDate(meeting.date);
  const timeAndDuration = meeting.duration
    ? `${dateDisplay} at ${meeting.time} ${tzAbbr} (${meeting.duration})`
    : `${dateDisplay} at ${meeting.time} ${tzAbbr}`;

  return (
    <Card className="hover:bg-muted/30 transition-colors">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            {/* Date badge */}
            <div className="flex-shrink-0 w-14 h-14 bg-[var(--gold)]/10 border border-[var(--gold)]/20 rounded-lg flex flex-col items-center justify-center">
              <span className="text-[10px] font-mono uppercase text-[var(--gold)]">
                {getMonthAbbrev(meeting.date)}
              </span>
              <span className="text-lg font-bold text-[var(--gold)]">
                {getDayOfMonth(meeting.date)}
              </span>
            </div>

            <div className="space-y-2">
              {/* Title */}
              <Link
                href={`/meetings/${meeting.id}`}
                className="text-base font-medium hover:text-[var(--gold)] transition-colors"
              >
                {meeting.title}
              </Link>

              {/* Date + time + duration */}
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-3.5 w-3.5 flex-shrink-0" />
                <span>{timeAndDuration}</span>
              </div>

              {/* Location */}
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                {meeting.isVirtual ? (
                  <Video className="h-3.5 w-3.5 flex-shrink-0" />
                ) : (
                  <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
                )}
                <span>{meeting.location}</span>
              </div>

              {/* Preparation indicators */}
              <div className="flex items-center gap-4 pt-1">
                {meeting.agendaItemsCount > 0 && (
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <FileText className="h-3.5 w-3.5" />
                    <span>
                      {meeting.agendaItemsCount} agenda item
                      {meeting.agendaItemsCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action button */}
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="min-h-[44px] min-w-[44px] flex-shrink-0"
          >
            <Link href={`/meetings/${meeting.id}`}>View Agenda</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------- Past Meeting Card ----------

interface PastMeetingCardProps {
  meeting: Meeting;
}

function PastMeetingCard({ meeting }: PastMeetingCardProps) {
  const dateDisplay = formatMeetingDate(meeting.date);

  return (
    <Card className="hover:bg-muted/30 transition-colors">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            {/* Date badge */}
            <div className="flex-shrink-0 w-14 h-14 bg-muted/50 border border-border rounded-lg flex flex-col items-center justify-center">
              <span className="text-[10px] font-mono uppercase text-muted-foreground">
                {getMonthAbbrev(meeting.date)}
              </span>
              <span className="text-lg font-bold text-muted-foreground">
                {getDayOfMonth(meeting.date)}
              </span>
            </div>

            <div className="space-y-2">
              {/* Title */}
              <Link
                href={`/meetings/${meeting.id}`}
                className="text-base font-medium hover:text-[var(--gold)] transition-colors"
              >
                {meeting.title}
              </Link>

              {/* Date */}
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-3.5 w-3.5 flex-shrink-0" />
                <span>{dateDisplay}</span>
              </div>

              {/* Outcome indicators */}
              <div className="flex items-center gap-3 pt-1">
                {meeting.hasMinutes && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md bg-[var(--gold)]/10 text-[var(--gold)] border border-[var(--gold)]/20">
                    <CheckCircle2 className="h-3 w-3" />
                    Minutes Available
                  </span>
                )}
                {meeting.decisionsCount > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md bg-[var(--gold)]/10 text-[var(--gold)] border border-[var(--gold)]/20">
                    <Scale className="h-3 w-3" />
                    {meeting.decisionsCount} decision
                    {meeting.decisionsCount !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Action button */}
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="min-h-[44px] min-w-[44px] flex-shrink-0"
          >
            <Link href={`/meetings/${meeting.id}`}>View</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
