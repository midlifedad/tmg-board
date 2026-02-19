"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar, FileText, CheckSquare, Lightbulb, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  documentsApi,
  meetingsApi,
  decisionsApi,
  ideasApi,
  api,
  type Document,
  type Meeting,
  type Decision,
  type Idea,
} from "@/lib/api";

interface DashboardData {
  documents: Document[];
  meetings: Meeting[];
  decisions: Decision[];
  ideas: Idea[];
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }

        const [documents, meetings, decisions, ideas] = await Promise.all([
          documentsApi.list(),
          meetingsApi.list(),
          decisionsApi.list(),
          ideasApi.list(),
        ]);

        setData({ documents, meetings, decisions, ideas });
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session?.user?.email]);

  // Calculate dashboard metrics
  const nextMeeting = data?.meetings
    .filter((m) => new Date(m.scheduled_date) > new Date())
    .sort((a, b) => new Date(a.scheduled_date).getTime() - new Date(b.scheduled_date).getTime())[0];

  const pendingSignatures = data?.documents.filter(
    (d) => d.signing_status === "pending" || d.signing_status === "sent"
  ).length || 0;

  const openVotes = data?.decisions.filter((d) => d.status === "open").length || 0;

  const newIdeas = data?.ideas.filter((i) => i.status === "new").length || 0;

  const recentDocuments = data?.documents
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3) || [];

  const upcomingMeetings = data?.meetings
    .filter((m) => new Date(m.scheduled_date) > new Date())
    .sort((a, b) => new Date(a.scheduled_date).getTime() - new Date(b.scheduled_date).getTime())
    .slice(0, 2) || [];

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  // Format next meeting date
  const nextMeetingDate = nextMeeting
    ? new Date(nextMeeting.scheduled_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "None";
  const nextMeetingTime = nextMeeting
    ? new Date(nextMeeting.scheduled_date).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
      })
    : "scheduled";

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Welcome Header */}
        <div>
          <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-gold mb-3 flex items-center gap-3">
            <span>Board Portal</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <h1 className="text-4xl font-light">
            Welcome, <em className="text-gold-light italic">{session?.user?.name?.split(" ")[0] || "Board Member"}</em>
          </h1>
          <p className="text-muted-foreground mt-2 text-sm font-light">
            The Many Group — Board Management Dashboard
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Next Meeting"
            value={nextMeetingDate}
            subtitle={nextMeetingTime}
            icon={Calendar}
            color="text-blue-500"
            href="/meetings"
          />
          <KPICard
            title="Pending Signatures"
            value={String(pendingSignatures)}
            subtitle="documents"
            icon={FileText}
            color="text-amber-500"
            href="/documents"
          />
          <KPICard
            title="Open Votes"
            value={String(openVotes)}
            subtitle="awaiting your vote"
            icon={CheckSquare}
            color="text-green-500"
            href="/decisions"
          />
          <KPICard
            title="New Ideas"
            value={String(newIdeas)}
            subtitle="submitted"
            icon={Lightbulb}
            color="text-purple-500"
            href="/ideas"
          />
        </div>

        {/* Recent Documents */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-serif text-xl font-light">Recent Documents</CardTitle>
            <Link href="/documents" className="font-mono text-[10px] tracking-wider uppercase text-gold hover:text-gold-light transition-colors">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {recentDocuments.length > 0 ? (
              <div className="space-y-3">
                {recentDocuments.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    id={doc.id}
                    title={doc.title}
                    type={doc.type}
                    date={new Date(doc.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                    status={
                      doc.signing_status === "completed"
                        ? "Signed"
                        : doc.signing_status === "pending" || doc.signing_status === "sent"
                        ? "Sign"
                        : "View"
                    }
                    statusColor={
                      doc.signing_status === "completed"
                        ? "text-green-500"
                        : doc.signing_status === "pending" || doc.signing_status === "sent"
                        ? "text-amber-500"
                        : "text-muted-foreground"
                    }
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No documents yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Upcoming Meetings */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-serif text-xl font-light">Upcoming Meetings</CardTitle>
            <Link href="/meetings" className="font-mono text-[10px] tracking-wider uppercase text-gold hover:text-gold-light transition-colors">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {upcomingMeetings.length > 0 ? (
              <div className="space-y-3">
                {upcomingMeetings.map((meeting) => (
                  <MeetingRow
                    key={meeting.id}
                    id={meeting.id}
                    title={meeting.title}
                    date={new Date(meeting.scheduled_date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                    time={new Date(meeting.scheduled_date).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                    location={meeting.location}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No upcoming meetings.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

interface KPICardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  href?: string;
}

function KPICard({ title, value, subtitle, icon: Icon, color, href }: KPICardProps) {
  const content = (
    <Card className={cn("card-hover transition-all", href ? "cursor-pointer" : "")}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-mono text-[9px] tracking-[0.2em] uppercase text-muted-foreground">{title}</p>
            <p className="font-serif text-3xl font-light mt-2 text-foreground">{value}</p>
            <p className="text-xs text-muted-foreground mt-1 font-light">{subtitle}</p>
          </div>
          <div className="w-9 h-9 rounded bg-gold/5 flex items-center justify-center">
            <Icon className={`h-4 w-4 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}

interface DocumentRowProps {
  id: number;
  title: string;
  type: string;
  date: string;
  status: string;
  statusColor?: string;
}

function DocumentRow({
  id,
  title,
  type,
  date,
  status,
  statusColor = "text-muted-foreground",
}: DocumentRowProps) {
  return (
    <Link
      href={`/documents/${id}`}
      className="flex items-center justify-between py-2 border-b border-border last:border-0 hover:bg-muted/20 transition-colors -mx-2 px-2 rounded"
    >
      <div className="flex items-center gap-3">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-muted-foreground capitalize">
            {type} - {date}
          </p>
        </div>
      </div>
      <span className={`text-sm font-medium ${statusColor}`}>{status}</span>
    </Link>
  );
}

interface MeetingRowProps {
  id: number;
  title: string;
  date: string;
  time: string;
  location: string;
}

function MeetingRow({ id, title, date, time, location }: MeetingRowProps) {
  return (
    <Link
      href={`/meetings/${id}`}
      className="flex items-center justify-between py-2 border-b border-border last:border-0 hover:bg-muted/20 transition-colors -mx-2 px-2 rounded"
    >
      <div className="flex items-center gap-3">
        <Calendar className="h-4 w-4 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-muted-foreground">
            {date} at {time}
          </p>
        </div>
      </div>
      <span className="text-xs text-muted-foreground">{location}</span>
    </Link>
  );
}
