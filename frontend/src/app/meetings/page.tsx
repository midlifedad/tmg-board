"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Calendar,
  Plus,
  List,
  Grid3X3,
  MapPin,
  Clock,
  Video,
  FileText,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { meetingsApi, api, type Meeting as ApiMeeting } from "@/lib/api";
import { CreateMeetingModal } from "@/components/create-meeting-modal";

interface Meeting {
  id: string;
  title: string;
  date: string;
  time: string;
  location: string;
  isVirtual: boolean;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  hasMinutes?: boolean;
}

const statusColors = {
  scheduled: "bg-blue-500/20 text-blue-400",
  in_progress: "bg-green-500/20 text-green-400",
  completed: "bg-muted text-muted-foreground",
  cancelled: "bg-red-500/20 text-red-400",
};

export default function MeetingsPage() {
  const { data: session } = useSession();
  const [viewMode, setViewMode] = useState<"calendar" | "list">("list");
  const [currentMonth, setCurrentMonth] = useState(new Date(2026, 0, 1)); // January 2026
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const data = await meetingsApi.list();
        // Transform API response to match component interface
        const transformed: Meeting[] = data.map((meeting) => {
          // Parse date and time from scheduled_date
          const dateObj = new Date(meeting.scheduled_date);
          const time = dateObj.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
          const dateStr = dateObj.toISOString().split("T")[0];
          const isVirtual = meeting.meeting_link != null ||
                           meeting.location.toLowerCase().includes("virtual") ||
                           meeting.location.toLowerCase().includes("zoom");
          return {
            id: String(meeting.id),
            title: meeting.title,
            date: dateStr,
            time: time,
            location: meeting.location,
            isVirtual: isVirtual,
            status: meeting.status,
            hasMinutes: meeting.status === "completed",
          };
        });
        setMeetings(transformed);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load meetings");
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();
  }, [session?.user?.email]);

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin = userRole === "admin" || userRole === "chair" || !session;

  const refetchMeetings = async () => {
    try {
      const data = await meetingsApi.list();
      const transformed: Meeting[] = data.map((meeting) => {
        const dateObj = new Date(meeting.scheduled_date);
        const time = dateObj.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        const dateStr = dateObj.toISOString().split("T")[0];
        const isVirtual = meeting.meeting_link != null ||
                         meeting.location.toLowerCase().includes("virtual") ||
                         meeting.location.toLowerCase().includes("zoom");
        return {
          id: String(meeting.id),
          title: meeting.title,
          date: dateStr,
          time: time,
          location: meeting.location,
          isVirtual: isVirtual,
          status: meeting.status,
          hasMinutes: meeting.status === "completed",
        };
      });
      setMeetings(transformed);
    } catch (err) {
      console.error("Failed to refetch meetings:", err);
    }
  };

  const upcomingMeetings = meetings.filter(
    (m) => m.status === "scheduled" && new Date(m.date) >= new Date()
  );
  const pastMeetings = meetings.filter((m) => m.status === "completed");

  // Calendar helpers
  const daysInMonth = new Date(
    currentMonth.getFullYear(),
    currentMonth.getMonth() + 1,
    0
  ).getDate();
  const firstDayOfMonth = new Date(
    currentMonth.getFullYear(),
    currentMonth.getMonth(),
    1
  ).getDay();

  const monthMeetings = meetings.filter((m) => {
    const meetingDate = new Date(m.date);
    return (
      meetingDate.getMonth() === currentMonth.getMonth() &&
      meetingDate.getFullYear() === currentMonth.getFullYear()
    );
  });

  const getMeetingForDay = (day: number) => {
    return monthMeetings.find((m) => new Date(m.date).getDate() === day);
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
            <h1 className="text-3xl font-bold">Meetings</h1>
            <p className="text-muted-foreground mt-1">
              Board meetings, agendas, and minutes
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* View Toggle */}
            <div className="flex items-center border rounded-md">
              <button
                onClick={() => setViewMode("calendar")}
                className={cn(
                  "p-2 transition-colors",
                  viewMode === "calendar"
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                )}
              >
                <Grid3X3 className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={cn(
                  "p-2 transition-colors",
                  viewMode === "list"
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                )}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
            {isChairOrAdmin && (
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Schedule Meeting
              </Button>
            )}
          </div>
        </div>

        {viewMode === "calendar" ? (
          /* Calendar View */
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>
                {currentMonth.toLocaleDateString("en-US", {
                  month: "long",
                  year: "numeric",
                })}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() =>
                    setCurrentMonth(
                      new Date(
                        currentMonth.getFullYear(),
                        currentMonth.getMonth() - 1
                      )
                    )
                  }
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() =>
                    setCurrentMonth(
                      new Date(
                        currentMonth.getFullYear(),
                        currentMonth.getMonth() + 1
                      )
                    )
                  }
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Day headers */}
              <div className="grid grid-cols-7 gap-1 mb-2">
                {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                  <div
                    key={day}
                    className="text-center text-xs font-medium text-muted-foreground py-2"
                  >
                    {day}
                  </div>
                ))}
              </div>
              {/* Calendar grid */}
              <div className="grid grid-cols-7 gap-1">
                {/* Empty cells for days before month starts */}
                {Array.from({ length: firstDayOfMonth }).map((_, i) => (
                  <div key={`empty-${i}`} className="aspect-square" />
                ))}
                {/* Days of month */}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                  const day = i + 1;
                  const meeting = getMeetingForDay(day);
                  const isToday =
                    day === new Date().getDate() &&
                    currentMonth.getMonth() === new Date().getMonth() &&
                    currentMonth.getFullYear() === new Date().getFullYear();

                  return (
                    <div
                      key={day}
                      className={cn(
                        "aspect-square p-1 border rounded-md",
                        isToday && "border-primary",
                        meeting && "bg-primary/10"
                      )}
                    >
                      <div className="text-xs text-right mb-1">{day}</div>
                      {meeting && (
                        <Link href={`/meetings/${meeting.id}`}>
                          <div className="text-[10px] bg-primary text-primary-foreground rounded px-1 py-0.5 truncate">
                            {meeting.title}
                          </div>
                        </Link>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ) : (
          /* List View */
          <div className="space-y-6">
            {/* Upcoming Meetings */}
            <div>
              <h2 className="text-lg font-semibold mb-4">Upcoming Meetings</h2>
              {upcomingMeetings.length > 0 ? (
                <div className="space-y-3">
                  {upcomingMeetings.map((meeting) => (
                    <MeetingCard key={meeting.id} meeting={meeting} />
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
            <div>
              <h2 className="text-lg font-semibold mb-4">Past Meetings</h2>
              <div className="space-y-3">
                {pastMeetings.map((meeting) => (
                  <MeetingCard key={meeting.id} meeting={meeting} />
                ))}
              </div>
            </div>
          </div>
        )}
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

interface MeetingCardProps {
  meeting: {
    id: string;
    title: string;
    date: string;
    time: string;
    location: string;
    isVirtual: boolean;
    status: "scheduled" | "in_progress" | "completed" | "cancelled";
    hasMinutes?: boolean;
  };
}

function MeetingCard({ meeting }: MeetingCardProps) {
  return (
    <Card className="hover:bg-muted/20 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex-shrink-0 w-12 h-12 bg-primary/20 rounded-lg flex flex-col items-center justify-center">
              <span className="text-xs text-primary font-medium">
                {new Date(meeting.date).toLocaleDateString("en-US", {
                  month: "short",
                })}
              </span>
              <span className="text-lg font-bold text-primary">
                {new Date(meeting.date).getDate()}
              </span>
            </div>
            <div>
              <Link
                href={`/meetings/${meeting.id}`}
                className="font-medium hover:text-primary transition-colors"
              >
                {meeting.title}
              </Link>
              <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {meeting.time}
                </div>
                <div className="flex items-center gap-1">
                  {meeting.isVirtual ? (
                    <Video className="h-3 w-3" />
                  ) : (
                    <MapPin className="h-3 w-3" />
                  )}
                  {meeting.location}
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {meeting.status === "completed" && meeting.hasMinutes && (
              <Button variant="outline" size="sm" asChild>
                <Link href={`/documents?type=minutes`}>
                  <FileText className="h-3 w-3 mr-1" />
                  Minutes
                </Link>
              </Button>
            )}
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/meetings/${meeting.id}`}>
                {meeting.status === "scheduled" ? "View Agenda" : "View"}
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
