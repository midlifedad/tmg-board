"use client";

import { use, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowLeft,
  User,
  Calendar,
  MessageSquare,
  ArrowUpRight,
  Send,
  Loader2,
  Pencil,
  Trash2,
  CheckCircle,
  XCircle,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ideasApi, api, type Idea as ApiIdea, type Comment as ApiComment } from "@/lib/api";
import { EditIdeaModal } from "@/components/edit-idea-modal";

type IdeaStatus = "new" | "under_review" | "approved" | "rejected" | "promoted";

const statusConfig: Record<IdeaStatus, { label: string; color: string }> = {
  new: { label: "New", color: "bg-blue-500/20 text-blue-400" },
  under_review: { label: "Under Review", color: "bg-amber-500/20 text-amber-400" },
  approved: { label: "Approved", color: "bg-green-500/20 text-green-400" },
  rejected: { label: "Rejected", color: "bg-red-500/20 text-red-400" },
  promoted: { label: "Promoted to Decision", color: "bg-purple-500/20 text-purple-400" },
};

interface IdeaDetail {
  id: string;
  title: string;
  description: string;
  submittedBy: string;
  submittedAt: string;
  status: IdeaStatus;
  comments: Array<{
    id: string;
    userId: string;
    userName: string;
    content: string;
    createdAt: string;
  }>;
}

export default function IdeaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session } = useSession();
  const [newComment, setNewComment] = useState("");
  const [idea, setIdea] = useState<IdeaDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [statusLoading, setStatusLoading] = useState<string | null>(null);

  const fetchIdea = useCallback(async () => {
    const email = session?.user?.email;
    if (!email) return;
    try {
      setLoading(true);
      api.setUserEmail(email);
      const [ideaData, commentsData] = await Promise.all([
        ideasApi.get(id),
        ideasApi.getComments(id),
      ]);
      setIdea({
        id: String(ideaData.id),
        title: ideaData.title,
        description: ideaData.description || "",
        submittedBy: `User ${ideaData.submitted_by_id}`,
        submittedAt: ideaData.created_at,
        status: ideaData.status,
        comments: commentsData.map((c) => ({
          id: String(c.id),
          userId: String(c.user_id),
          userName: c.user_name || `User ${c.user_id}`,
          content: c.content,
          createdAt: c.created_at,
        })),
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load idea");
    } finally {
      setLoading(false);
    }
  }, [id, session?.user?.email]);

  useEffect(() => {
    fetchIdea();
  }, [fetchIdea]);

  const handleDelete = async () => {
    if (!idea) return;
    setDeleting(true);
    try {
      await ideasApi.delete(idea.id);
      window.location.href = "/ideas";
    } catch (err) {
      console.error("Failed to delete idea:", err);
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleStatusChange = async (newStatus: ApiIdea["status"]) => {
    if (!idea) return;
    setStatusLoading(newStatus);
    try {
      await ideasApi.updateStatus(idea.id, newStatus);
      setIdea({ ...idea, status: newStatus });
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setStatusLoading(null);
    }
  };

  const userRole = (session?.user as { role?: string })?.role;
  const isChairOrAdmin = userRole === "admin" || userRole === "chair";
  const statusInfo = idea ? statusConfig[idea.status] : statusConfig.new;

  const handleSubmitComment = async () => {
    if (newComment.trim() && idea) {
      try {
        setSubmittingComment(true);
        const comment = await ideasApi.addComment(idea.id, newComment);
        setIdea({
          ...idea,
          comments: [
            ...idea.comments,
            {
              id: String(comment.id),
              userId: String(comment.author_id ?? comment.user_id),
              userName: comment.user_name || session?.user?.name || "You",
              content: comment.content,
              createdAt: comment.created_at,
            },
          ],
        });
        setNewComment("");
      } catch (err) {
        console.error("Failed to add comment:", err);
      } finally {
        setSubmittingComment(false);
      }
    }
  };

  const handlePromote = async () => {
    if (idea) {
      try {
        await ideasApi.promote(idea.id);
        setIdea({ ...idea, status: "promoted" });
      } catch (err) {
        console.error("Failed to promote idea:", err);
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

  if (error || !idea) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error || "Idea not found"}</p>
          <Button asChild>
            <Link href="/ideas">Back to Ideas</Link>
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
          href="/ideas"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Ideas
        </Link>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{idea.title}</h1>
              <span className={cn("px-2 py-1 rounded text-xs font-medium", statusInfo.color)}>
                {statusInfo.label}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <User className="h-4 w-4" />
                Submitted by {idea.submittedBy}
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                {new Date(idea.submittedAt).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {isChairOrAdmin && (
              <>
                <Button variant="outline" size="sm" onClick={() => setShowEditModal(true)}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                {idea.status === "new" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleStatusChange("under_review")}
                    disabled={statusLoading === "under_review"}
                  >
                    {statusLoading === "under_review" ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Eye className="h-4 w-4 mr-2" />
                    )}
                    Review
                  </Button>
                )}
                {(idea.status === "under_review" || idea.status === "new") && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange("approved")}
                      disabled={statusLoading === "approved"}
                    >
                      {statusLoading === "approved" ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                      )}
                      Approve
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleStatusChange("rejected")}
                      disabled={statusLoading === "rejected"}
                    >
                      {statusLoading === "rejected" ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <XCircle className="h-4 w-4 mr-2" />
                      )}
                      Reject
                    </Button>
                  </>
                )}
                {idea.status !== "promoted" && idea.status !== "rejected" && (
                  <Button size="sm" onClick={handlePromote}>
                    <ArrowUpRight className="h-4 w-4 mr-2" />
                    Promote to Decision
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </>
            )}
          </div>
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
                <p className="text-sm whitespace-pre-line">{idea.description}</p>
              </CardContent>
            </Card>

            {/* Comments */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Discussion ({idea.comments.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {idea.comments.map((comment) => (
                  <div key={comment.id} className="border-b border-border last:border-0 pb-4 last:pb-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <span className="text-xs font-medium">{comment.userName[0]}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium">{comment.userName}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(comment.createdAt).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground ml-10">{comment.content}</p>
                  </div>
                ))}

                {/* Add Comment */}
                <div className="pt-4 border-t border-border">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-medium text-primary">
                        {session?.user?.name?.[0] || "?"}
                      </span>
                    </div>
                    <div className="flex-1">
                      <textarea
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        placeholder="Add a comment..."
                        className="w-full min-h-[80px] p-3 rounded-md border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <div className="flex justify-end mt-2">
                        <Button
                          size="sm"
                          onClick={handleSubmitComment}
                          disabled={!newComment.trim()}
                        >
                          <Send className="h-4 w-4 mr-2" />
                          Comment
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={cn("inline-flex px-3 py-1.5 rounded-md text-sm font-medium", statusInfo.color)}>
                  {statusInfo.label}
                </div>
                {idea.status === "promoted" && (
                  <p className="text-sm text-muted-foreground mt-3">
                    This idea has been promoted to a board decision.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Activity Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Activity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Comments</span>
                  <span className="font-medium">{idea.comments.length}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Contributors</span>
                  <span className="font-medium">
                    {new Set(idea.comments.map((c) => c.userId)).size}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Days active</span>
                  <span className="font-medium">
                    {Math.ceil(
                      (Date.now() - new Date(idea.submittedAt).getTime()) /
                        (1000 * 60 * 60 * 24)
                    )}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => !deleting && setShowDeleteConfirm(false)}
          />
          <Card className="relative z-10 w-full max-w-sm mx-4 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Delete Idea</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete &ldquo;{idea.title}&rdquo;? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-2" />
                  )}
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit Idea Modal */}
      <EditIdeaModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={() => fetchIdea()}
        idea={idea ? {
          id: idea.id,
          title: idea.title,
          description: idea.description,
        } : null}
      />
    </AppShell>
  );
}
