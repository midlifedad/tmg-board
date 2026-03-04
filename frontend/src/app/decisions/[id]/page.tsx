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
  CheckCircle,
  XCircle,
  FileText,
  Users,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Loader2,
  Pencil,
  Lock,
  Unlock,
  Archive,
  Bell,
  PlayCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { decisionsApi, api, type Decision as ApiDecision, type Vote as ApiVote } from "@/lib/api";
import { EditDecisionModal } from "@/components/edit-decision-modal";

type VoteValue = "yes" | "no" | "abstain";

interface DecisionDetail {
  id: string;
  title: string;
  description: string;
  type: "vote" | "consent" | "resolution";
  status: "pending" | "open" | "closed";
  deadline: string | null;
  meetingId: string | null;
  meetingTitle: string | null;
  createdAt: string;
  createdBy: string;
  relatedDocuments: Array<{ id: string; title: string }>;
  votes: Array<{
    userId: string;
    userName: string;
    vote: VoteValue | null;
    votedAt: string | null;
  }>;
}

const voteConfig = {
  yes: { label: "Yes", icon: ThumbsUp, color: "text-green-500", bgColor: "bg-green-500/20 border-green-500" },
  no: { label: "No", icon: ThumbsDown, color: "text-red-500", bgColor: "bg-red-500/20 border-red-500" },
  abstain: { label: "Abstain", icon: Minus, color: "text-muted-foreground", bgColor: "bg-muted border-muted-foreground" },
};

export default function DecisionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session } = useSession();
  const [selectedVote, setSelectedVote] = useState<VoteValue | null>(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [decision, setDecision] = useState<DecisionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingVote, setSubmittingVote] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchDecision = useCallback(async () => {
    const email = session?.user?.email;
    if (!email) return;
    try {
      setLoading(true);
      api.setUserEmail(email);
      const detailData = await decisionsApi.get(id);
      const decisionData = detailData.decision;

      const votes = (decisionData as { votes?: Array<{ member_id: number; vote: string; cast_at: string }> }).votes?.map((v) => ({
        userId: String(v.member_id),
        userName: `User ${v.member_id}`,
        vote: v.vote as VoteValue,
        votedAt: v.cast_at,
      })) || [];

      if (detailData.user_vote) {
        setHasVoted(true);
        setSelectedVote(detailData.user_vote as VoteValue);
      }

      setDecision({
        id: String(decisionData.id),
        title: decisionData.title,
        description: decisionData.description || "",
        type: decisionData.type,
        status: decisionData.status,
        deadline: decisionData.deadline || null,
        meetingId: decisionData.meeting_id ? String(decisionData.meeting_id) : null,
        meetingTitle: null,
        createdAt: decisionData.created_at,
        createdBy: `User ${decisionData.created_by_id}`,
        relatedDocuments: [],
        votes: votes,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decision");
    } finally {
      setLoading(false);
    }
  }, [id, session?.user?.email]);

  useEffect(() => {
    fetchDecision();
  }, [fetchDecision]);

  const handleOpenVoting = async () => {
    if (!decision) return;
    setActionLoading("open");
    try {
      await decisionsApi.open(decision.id);
      await fetchDecision();
    } catch (err) {
      console.error("Failed to open voting:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCloseVoting = async () => {
    if (!decision) return;
    setActionLoading("close");
    try {
      await decisionsApi.close(decision.id);
      await fetchDecision();
    } catch (err) {
      console.error("Failed to close voting:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReopenVoting = async () => {
    if (!decision) return;
    setActionLoading("reopen");
    try {
      await decisionsApi.reopen(decision.id);
      await fetchDecision();
    } catch (err) {
      console.error("Failed to reopen voting:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleArchive = async () => {
    if (!decision) return;
    setActionLoading("archive");
    try {
      await decisionsApi.archive(decision.id);
      window.location.href = "/decisions";
    } catch (err) {
      console.error("Failed to archive decision:", err);
      setActionLoading(null);
    }
  };

  const handleSendReminders = async () => {
    if (!decision) return;
    setActionLoading("remind");
    try {
      const result = await decisionsApi.sendReminders(decision.id);
      alert(`Reminders sent to ${result.sent_count} pending voter(s).`);
    } catch (err) {
      console.error("Failed to send reminders:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const userRole = (session?.user as { role?: string })?.role;
  const isAdmin = userRole === "admin";

  // Calculate vote results
  const voteCounts = decision?.votes.reduce(
    (acc, v) => {
      if (v.vote === "yes") acc.yes++;
      else if (v.vote === "no") acc.no++;
      else if (v.vote === "abstain") acc.abstain++;
      else acc.pending++;
      return acc;
    },
    { yes: 0, no: 0, abstain: 0, pending: 0 }
  ) || { yes: 0, no: 0, abstain: 0, pending: 0 };

  const totalVotes = voteCounts.yes + voteCounts.no + voteCounts.abstain;
  const totalVoters = decision?.votes.length || 0;

  const handleVote = async () => {
    if (selectedVote && decision) {
      try {
        setSubmittingVote(true);
        await decisionsApi.castVote(decision.id, selectedVote);
        setHasVoted(true);
        // Refresh decision data to update vote results
        const detailData = await decisionsApi.get(decision.id);
        const decisionData = detailData.decision;
        const votes = (decisionData as { votes?: Array<{ member_id: number; vote: string; cast_at: string }> }).votes?.map((v) => ({
          userId: String(v.member_id),
          userName: `User ${v.member_id}`,
          vote: v.vote as VoteValue,
          votedAt: v.cast_at,
        })) || [];
        setDecision((prev) => prev ? { ...prev, votes } : null);
      } catch (err) {
        console.error("Failed to cast vote:", err);
      } finally {
        setSubmittingVote(false);
      }
    }
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

  if (error || !decision) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error || "Decision not found"}</p>
          <Button asChild>
            <Link href="/decisions">Back to Decisions</Link>
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
          href="/decisions"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Decisions
        </Link>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{decision.title}</h1>
              <span className="px-2 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400 capitalize">
                {decision.type}
              </span>
              <span className="px-2 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400 capitalize">
                {decision.status}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              {decision.deadline && (
                <div className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4" />
                  Deadline: {new Date(decision.deadline).toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                </div>
              )}
              {decision.meetingTitle && (
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-4 w-4" />
                  <Link href={`/meetings/${decision.meetingId}`} className="hover:text-primary">
                    {decision.meetingTitle}
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Admin Actions */}
          {isAdmin && (
            <div className="flex items-center gap-2 flex-shrink-0">
              {decision.status !== "closed" && (
                <Button variant="outline" size="sm" onClick={() => setShowEditModal(true)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              )}
              {decision.status === "pending" && (
                <Button
                  size="sm"
                  onClick={handleOpenVoting}
                  disabled={actionLoading === "open"}
                >
                  {actionLoading === "open" ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <PlayCircle className="h-4 w-4 mr-2" />
                  )}
                  Open Voting
                </Button>
              )}
              {decision.status === "open" && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSendReminders}
                    disabled={actionLoading === "remind"}
                  >
                    {actionLoading === "remind" ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Bell className="h-4 w-4 mr-2" />
                    )}
                    Send Reminders
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCloseVoting}
                    disabled={actionLoading === "close"}
                  >
                    {actionLoading === "close" ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Lock className="h-4 w-4 mr-2" />
                    )}
                    Close Voting
                  </Button>
                </>
              )}
              {decision.status === "closed" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReopenVoting}
                  disabled={actionLoading === "reopen"}
                >
                  {actionLoading === "reopen" ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Unlock className="h-4 w-4 mr-2" />
                  )}
                  Reopen
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleArchive}
                disabled={actionLoading === "archive"}
              >
                {actionLoading === "archive" ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Archive className="h-4 w-4 mr-2" />
                )}
                Archive
              </Button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-line">{decision.description}</p>
              </CardContent>
            </Card>

            {/* Vote Casting */}
            {decision.status === "open" && !hasVoted && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Cast Your Vote</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-3">
                    {(["yes", "no", "abstain"] as VoteValue[]).map((vote) => {
                      const config = voteConfig[vote];
                      const Icon = config.icon;
                      const isSelected = selectedVote === vote;

                      return (
                        <button
                          key={vote}
                          onClick={() => setSelectedVote(vote)}
                          className={cn(
                            "flex-1 flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all",
                            isSelected
                              ? config.bgColor
                              : "border-border hover:border-muted-foreground/50"
                          )}
                        >
                          <Icon className={cn("h-6 w-6", isSelected ? config.color : "text-muted-foreground")} />
                          <span className={cn("font-medium", isSelected ? config.color : "text-muted-foreground")}>
                            {config.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <Button
                    onClick={handleVote}
                    disabled={!selectedVote}
                    className="w-full"
                  >
                    Submit Vote
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Vote Confirmed */}
            {hasVoted && (
              <Card className="border-green-500/50 bg-green-500/10">
                <CardContent className="py-6 text-center">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                  <p className="font-medium text-green-500">Vote Submitted</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    You voted: {selectedVote && voteConfig[selectedVote].label}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Related Documents */}
            {decision.relatedDocuments.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Related Documents</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {decision.relatedDocuments.map((doc) => (
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
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Current Results */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Current Results</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex h-4 rounded-full overflow-hidden bg-muted">
                    {voteCounts.yes > 0 && (
                      <div
                        className="bg-green-500 transition-all"
                        style={{ width: `${(voteCounts.yes / totalVoters) * 100}%` }}
                      />
                    )}
                    {voteCounts.no > 0 && (
                      <div
                        className="bg-red-500 transition-all"
                        style={{ width: `${(voteCounts.no / totalVoters) * 100}%` }}
                      />
                    )}
                    {voteCounts.abstain > 0 && (
                      <div
                        className="bg-muted-foreground transition-all"
                        style={{ width: `${(voteCounts.abstain / totalVoters) * 100}%` }}
                      />
                    )}
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{totalVotes} of {totalVoters} voted</span>
                    <span>{voteCounts.pending} pending</span>
                  </div>
                </div>

                {/* Vote Counts */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-2 text-green-500">
                      <ThumbsUp className="h-4 w-4" />
                      <span>Yes</span>
                    </div>
                    <span className="font-medium">{voteCounts.yes}</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-2 text-red-500">
                      <ThumbsDown className="h-4 w-4" />
                      <span>No</span>
                    </div>
                    <span className="font-medium">{voteCounts.no}</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Minus className="h-4 w-4" />
                      <span>Abstain</span>
                    </div>
                    <span className="font-medium">{voteCounts.abstain}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Voters List (Admin only) */}
            {isAdmin && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    Voter Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {decision.votes.map((vote) => (
                    <div key={vote.userId} className="flex items-center justify-between py-1.5">
                      <span className="text-sm">{vote.userName}</span>
                      {vote.vote ? (
                        <span className={cn("text-xs font-medium", voteConfig[vote.vote].color)}>
                          {voteConfig[vote.vote].label}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">Pending</span>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Edit Decision Modal */}
      <EditDecisionModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={() => fetchDecision()}
        decision={decision ? {
          id: decision.id,
          title: decision.title,
          description: decision.description,
          type: decision.type,
          deadline: decision.deadline,
          status: decision.status,
        } : null}
      />
    </AppShell>
  );
}
