"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Lightbulb,
  Plus,
  MessageSquare,
  ChevronRight,
  ArrowUpRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ideasApi, api, type Idea as ApiIdea } from "@/lib/api";
import { SubmitIdeaModal } from "@/components/submit-idea-modal";

type IdeaStatus = "new" | "under_review" | "approved" | "rejected" | "promoted";

interface Idea {
  id: string;
  title: string;
  description: string;
  submittedBy: string;
  submittedAt: string;
  status: IdeaStatus;
  commentCount: number;
}

const statusConfig: Record<IdeaStatus, { label: string; color: string }> = {
  new: { label: "New", color: "bg-blue-500/20 text-blue-400" },
  under_review: { label: "Under Review", color: "bg-amber-500/20 text-amber-400" },
  approved: { label: "Approved", color: "bg-green-500/20 text-green-400" },
  rejected: { label: "Rejected", color: "bg-red-500/20 text-red-400" },
  promoted: { label: "Promoted to Decision", color: "bg-purple-500/20 text-purple-400" },
};

export default function IdeasPage() {
  const { data: session } = useSession();
  const [filter, setFilter] = useState<IdeaStatus | "all">("all");
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchIdeas = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const data = await ideasApi.list();
        // Transform API response to match component interface
        const transformed: Idea[] = data.map((idea) => ({
          id: String(idea.id),
          title: idea.title,
          description: idea.description || "",
          submittedBy: `User ${idea.submitted_by_id}`, // TODO: Fetch user names
          submittedAt: idea.created_at,
          status: idea.status,
          commentCount: 0, // TODO: Get comment count from API
        }));
        setIdeas(transformed);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load ideas");
      } finally {
        setLoading(false);
      }
    };

    fetchIdeas();
  }, [session?.user?.email]);

  const refetchIdeas = async () => {
    try {
      const data = await ideasApi.list();
      const transformed: Idea[] = data.map((idea) => ({
        id: String(idea.id),
        title: idea.title,
        description: idea.description || "",
        submittedBy: `User ${idea.submitted_by_id}`,
        submittedAt: idea.created_at,
        status: idea.status,
        commentCount: 0,
      }));
      setIdeas(transformed);
    } catch (err) {
      console.error("Failed to refetch ideas:", err);
    }
  };

  const filteredIdeas = ideas.filter((idea) => {
    if (filter === "all") return true;
    return idea.status === filter;
  });

  const statusCounts = ideas.reduce((acc, idea) => {
    acc[idea.status] = (acc[idea.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

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
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3"><span>Idea Board</span><div className="flex-1 h-px bg-border" /></div>
            <h1 className="text-3xl font-light">Ideas</h1>
            <p className="text-sm font-light text-muted-foreground mt-1">
              Submit and discuss ideas for board consideration
            </p>
          </div>
          <Button onClick={() => setShowSubmitModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Submit Idea
          </Button>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter("all")}
            className={cn(
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              filter === "all"
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            )}
          >
            All ({ideas.length})
          </button>
          {(["new", "under_review", "approved", "rejected", "promoted"] as IdeaStatus[]).map(
            (status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  filter === status
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted hover:bg-muted/80"
                )}
              >
                {statusConfig[status].label} ({statusCounts[status] || 0})
              </button>
            )
          )}
        </div>

        {/* Ideas List */}
        <div className="space-y-3">
          {filteredIdeas.map((idea) => (
            <IdeaCard key={idea.id} idea={idea} />
          ))}
        </div>

        {filteredIdeas.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No ideas found matching your filter.
            </CardContent>
          </Card>
        )}
      </div>

      {/* Submit Idea Modal */}
      <SubmitIdeaModal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        onSuccess={refetchIdeas}
      />
    </AppShell>
  );
}

function IdeaCard({ idea }: { idea: Idea }) {
  const statusInfo = statusConfig[idea.status];

  return (
    <Card className="hover:bg-muted/20 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn("px-2 py-0.5 rounded text-xs font-medium", statusInfo.color)}>
                {statusInfo.label}
              </span>
            </div>
            <Link
              href={`/ideas/${idea.id}`}
              className="font-medium hover:text-primary transition-colors"
            >
              {idea.title}
            </Link>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {idea.description}
            </p>
            <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
              <span>Submitted by {idea.submittedBy}</span>
              <span>
                {new Date(idea.submittedAt).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </span>
              {idea.commentCount > 0 && (
                <span className="flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" />
                  {idea.commentCount} comments
                </span>
              )}
            </div>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/ideas/${idea.id}`}>
              <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
