"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckSquare,
  Plus,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { decisionsApi, api, type Decision as ApiDecision } from "@/lib/api";
import { CreateDecisionModal } from "@/components/create-decision-modal";

type DecisionStatus = "draft" | "pending" | "open" | "closed";
type VoteValue = "yes" | "no" | "abstain" | null;

interface Decision {
  id: string;
  title: string;
  description: string;
  type: string;
  status: DecisionStatus;
  deadline: string | null;
  meetingId: string | null;
  meetingTitle: string | null;
  userVote: VoteValue;
  results?: {
    yes: number;
    no: number;
    abstain: number;
    pending: number;
  };
  outcome?: "passed" | "failed" | null;
}

const statusConfig = {
  draft: { label: "Draft", color: "bg-muted text-muted-foreground", icon: Clock },
  pending: { label: "Pending", color: "bg-muted text-muted-foreground", icon: Clock },
  open: { label: "Open", color: "bg-blue-500/20 text-blue-400", icon: CheckSquare },
  closed: { label: "Closed", color: "bg-muted text-muted-foreground", icon: CheckCircle },
};

const typeConfig: Record<string, { label: string; color: string }> = {
  vote: { label: "Vote", color: "bg-purple-500/20 text-purple-400" },
  consent: { label: "Consent", color: "bg-green-500/20 text-green-400" },
  resolution: { label: "Resolution", color: "bg-blue-500/20 text-blue-400" },
  budget: { label: "Budget", color: "bg-amber-500/20 text-amber-400" },
};

const defaultTypeInfo = { label: "Decision", color: "bg-gray-500/20 text-gray-400" };

export default function DecisionsPage() {
  const { data: session } = useSession();
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const data = await decisionsApi.list();
        // Transform decisions - fetch details for each to get results
        const transformed: Decision[] = await Promise.all(
          data.map(async (decision) => {
            let results = { yes: 0, no: 0, abstain: 0, pending: 0 };
            let userVote: VoteValue = null;
            try {
              const detail = await decisionsApi.get(String(decision.id));
              results = detail.results;
              userVote = detail.user_vote as VoteValue;
            } catch {
              // Ignore errors for results fetch
            }
            return {
              id: String(decision.id),
              title: decision.title,
              description: decision.description || "",
              type: decision.type,
              status: decision.status,
              deadline: decision.deadline || null,
              meetingId: decision.meeting_id ? String(decision.meeting_id) : null,
              meetingTitle: null, // TODO: Fetch meeting title if needed
              userVote: userVote,
              results: results,
              outcome: decision.status === "closed"
                ? (results.yes > results.no ? "passed" : "failed")
                : null,
            };
          })
        );
        setDecisions(transformed);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load decisions");
      } finally {
        setLoading(false);
      }
    };

    fetchDecisions();
  }, [session?.user?.email]);

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin = userRole === "admin" || userRole === "chair" || !session;

  const refetchDecisions = async () => {
    try {
      const data = await decisionsApi.list();
      const transformed: Decision[] = await Promise.all(
        data.map(async (decision) => {
          let results = { yes: 0, no: 0, abstain: 0, pending: 0 };
          let userVote: VoteValue = null;
          try {
            const detail = await decisionsApi.get(String(decision.id));
            results = detail.results;
            userVote = detail.user_vote as VoteValue;
          } catch {
            // Ignore errors for results fetch
          }
          return {
            id: String(decision.id),
            title: decision.title,
            description: decision.description || "",
            type: decision.type,
            status: decision.status,
            deadline: decision.deadline || null,
            meetingId: decision.meeting_id ? String(decision.meeting_id) : null,
            meetingTitle: null,
            userVote: userVote,
            results: results,
            outcome: decision.status === "closed"
              ? (results.yes > results.no ? "passed" : "failed")
              : null,
          };
        })
      );
      setDecisions(transformed);
    } catch (err) {
      console.error("Failed to refetch decisions:", err);
    }
  };

  const filteredDecisions = decisions.filter((d) => {
    if (filter === "all") return true;
    return d.status === filter;
  });

  const pendingDecisions = decisions.filter((d) => d.status === "pending" || d.status === "draft");
  const openDecisions = decisions.filter((d) => d.status === "open");
  const closedDecisions = decisions.filter((d) => d.status === "closed");

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
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3"><span>Governance</span><div className="flex-1 h-px bg-border" /></div>
            <h1 className="text-3xl font-light">Decisions</h1>
            <p className="text-sm font-light text-muted-foreground mt-1">
              Board votes, resolutions, and consent items
            </p>
          </div>
          {isChairOrAdmin && (
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Decision
            </Button>
          )}
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2">
          {[
            { key: "all", label: `All (${decisions.length})` },
            { key: "open", label: `Open (${openDecisions.length})` },
            { key: "closed", label: `Closed (${closedDecisions.length})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key as typeof filter)}
              className={cn(
                "px-4 py-2 rounded-md text-sm font-medium transition-colors",
                filter === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Pending Decisions Section */}
        {filter === "all" && pendingDecisions.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">
              Pending ({pendingDecisions.length})
            </h2>
            <div className="space-y-3">
              {pendingDecisions.map((decision) => (
                <DecisionCard key={decision.id} decision={decision} />
              ))}
            </div>
          </div>
        )}

        {/* Open Votes Section */}
        {filter !== "closed" && openDecisions.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">
              Open Votes ({openDecisions.length})
            </h2>
            <div className="space-y-3">
              {openDecisions.map((decision) => (
                <DecisionCard key={decision.id} decision={decision} />
              ))}
            </div>
          </div>
        )}

        {/* Closed Decisions Section */}
        {filter !== "open" && closedDecisions.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">
              Recent Decisions ({closedDecisions.length})
            </h2>
            <div className="space-y-3">
              {closedDecisions.map((decision) => (
                <DecisionCard key={decision.id} decision={decision} />
              ))}
            </div>
          </div>
        )}

        {filteredDecisions.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No decisions found.
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create Decision Modal */}
      <CreateDecisionModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={refetchDecisions}
      />
    </AppShell>
  );
}

function DecisionCard({ decision }: { decision: Decision }) {
  const statusInfo = statusConfig[decision.status];
  const typeInfo = typeConfig[decision.type] || defaultTypeInfo;
  const StatusIcon = statusInfo.icon;

  return (
    <Card className="hover:bg-muted/20 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn("px-2 py-0.5 rounded text-xs font-medium", typeInfo.color)}>
                {typeInfo.label}
              </span>
              {decision.deadline && decision.status === "open" && (
                <span className="text-xs text-muted-foreground">
                  Closes {new Date(decision.deadline).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              )}
            </div>
            <Link
              href={`/decisions/${decision.id}`}
              className="font-medium hover:text-primary transition-colors"
            >
              {decision.title}
            </Link>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
              {decision.description}
            </p>

            {/* Vote Status */}
            {decision.status === "open" && (
              <div className="flex items-center gap-4 mt-3">
                <div className="flex items-center gap-1.5 text-sm">
                  {decision.userVote ? (
                    <>
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-green-500">Vote cast</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-amber-500" />
                      <span className="text-amber-500">Vote pending</span>
                    </>
                  )}
                </div>
                {decision.results && (
                  <div className="text-xs text-muted-foreground">
                    {decision.results.yes + decision.results.no + decision.results.abstain} of{" "}
                    {decision.results.yes + decision.results.no + decision.results.abstain + decision.results.pending} voted
                  </div>
                )}
              </div>
            )}

            {/* Closed Results */}
            {decision.status === "closed" && decision.results && (
              <div className="flex items-center gap-4 mt-3">
                <div className={cn(
                  "flex items-center gap-1.5 text-sm font-medium",
                  decision.outcome === "passed" ? "text-green-500" : "text-red-500"
                )}>
                  {decision.outcome === "passed" ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  {decision.outcome === "passed" ? "Passed" : "Failed"}
                </div>
                <div className="text-xs text-muted-foreground">
                  ({decision.results.yes}-{decision.results.no}
                  {decision.results.abstain > 0 && `-${decision.results.abstain}`})
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {decision.status === "open" && !decision.userVote && (
              <Button size="sm" asChild>
                <Link href={`/decisions/${decision.id}`}>Cast Vote</Link>
              </Button>
            )}
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/decisions/${decision.id}`}>
                <ChevronRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
