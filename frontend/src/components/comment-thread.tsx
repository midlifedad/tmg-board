"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  ThumbsUp,
  Lightbulb,
  Heart,
  AlertTriangle,
  Pin,
  Reply,
  Edit,
  MoreVertical,
  Send,
  X,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ideasApi, type Comment, type ReactionType } from "@/lib/api";

const reactionConfig: Record<ReactionType, { icon: typeof ThumbsUp; label: string }> = {
  thumbs_up: { icon: ThumbsUp, label: "Like" },
  lightbulb: { icon: Lightbulb, label: "Insightful" },
  heart: { icon: Heart, label: "Love" },
  warning: { icon: AlertTriangle, label: "Concern" },
};

function formatDate(dateString: string | undefined | null): string {
  if (!dateString) return "Just now";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "Just now";
  return date.toLocaleDateString();
}

interface CommentThreadProps {
  comments: Comment[];
  onCommentsChange: (comments: Comment[]) => void;
  ideaId: string;
  canModerate: boolean;
  currentUserId?: number;
}

export function CommentThread({
  comments,
  onCommentsChange,
  ideaId,
  canModerate,
  currentUserId,
}: CommentThreadProps) {
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [editContent, setEditContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Organize comments into threads
  const rootComments = comments.filter((c) => !c.parent_id);
  const getReplies = (parentId: number) => comments.filter((c) => c.parent_id === parentId);

  const handleReaction = async (commentId: number, reactionType: ReactionType) => {
    try {
      await ideasApi.toggleReaction(commentId, reactionType);
      // Update local state
      onCommentsChange(
        comments.map((c) => {
          if (c.id !== commentId) return c;
          const reactions = { ...c.reactions } as Record<ReactionType, number>;
          const wasSelected = c.user_reaction === reactionType;

          if (wasSelected) {
            reactions[reactionType] = (reactions[reactionType] || 1) - 1;
            return { ...c, reactions, user_reaction: null };
          } else {
            if (c.user_reaction) {
              reactions[c.user_reaction] = (reactions[c.user_reaction] || 1) - 1;
            }
            reactions[reactionType] = (reactions[reactionType] || 0) + 1;
            return { ...c, reactions, user_reaction: reactionType };
          }
        })
      );
    } catch (err) {
      console.error("Failed to toggle reaction:", err);
    }
  };

  const handlePin = async (commentId: number) => {
    try {
      await ideasApi.togglePinComment(commentId);
      onCommentsChange(
        comments.map((c) =>
          c.id === commentId ? { ...c, is_pinned: !c.is_pinned } : c
        )
      );
    } catch (err) {
      console.error("Failed to toggle pin:", err);
    }
  };

  const handleReply = async (parentId: number) => {
    if (!replyContent.trim()) return;
    setSubmitting(true);
    try {
      const newComment = await ideasApi.addComment(ideaId, replyContent.trim());
      // Note: Backend should handle parent_id, this is simplified
      onCommentsChange([...comments, { ...newComment, parent_id: parentId }]);
      setReplyContent("");
      setReplyingTo(null);
    } catch (err) {
      console.error("Failed to add reply:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async (commentId: number) => {
    if (!editContent.trim()) return;
    setSubmitting(true);
    try {
      const updated = await ideasApi.editComment(commentId, editContent.trim());
      onCommentsChange(comments.map((c) => (c.id === commentId ? updated : c)));
      setEditingId(null);
      setEditContent("");
    } catch (err) {
      console.error("Failed to edit comment:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const startEdit = (comment: Comment) => {
    setEditingId(comment.id);
    setEditContent(comment.content);
    setReplyingTo(null);
  };

  const renderComment = (comment: Comment, depth = 0) => {
    const replies = getReplies(comment.id);
    const isEditing = editingId === comment.id;
    const isReplying = replyingTo === comment.id;
    const canEdit = comment.user_id === currentUserId;

    return (
      <div key={comment.id} className={cn("space-y-2", depth > 0 && "ml-6 pl-4 border-l border-border/50")}>
        <div className={cn(
          "p-3 rounded-lg",
          comment.is_pinned ? "bg-amber-500/10 border border-amber-500/30" : "bg-muted/30"
        )}>
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{comment.user_name || `User ${comment.user_id}`}</span>
              <span className="text-xs text-muted-foreground">
                {formatDate(comment.created_at)}
              </span>
              {comment.edited_at && (
                <span className="text-xs text-muted-foreground">(edited)</span>
              )}
              {comment.is_pinned && (
                <span className="flex items-center gap-1 text-xs text-amber-500">
                  <Pin className="h-3 w-3" /> Pinned
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {canModerate && (
                <button
                  onClick={() => handlePin(comment.id)}
                  className={cn(
                    "p-1 rounded hover:bg-muted",
                    comment.is_pinned && "text-amber-500"
                  )}
                  title={comment.is_pinned ? "Unpin" : "Pin"}
                >
                  <Pin className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Content */}
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full px-3 py-2 rounded-md border bg-background text-sm resize-none"
                rows={3}
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>
                  <X className="h-3 w-3 mr-1" /> Cancel
                </Button>
                <Button size="sm" onClick={() => handleEdit(comment.id)} disabled={submitting}>
                  {submitting ? <Loader2 className="h-3 w-3 animate-spin" /> : "Save"}
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm">{comment.content}</p>
          )}

          {/* Actions */}
          {!isEditing && (
            <div className="flex items-center gap-3 mt-3">
              {/* Reactions */}
              <div className="flex items-center gap-1">
                {(Object.keys(reactionConfig) as ReactionType[]).map((type) => {
                  const config = reactionConfig[type];
                  const Icon = config.icon;
                  const count = comment.reactions?.[type] || 0;
                  const isSelected = comment.user_reaction === type;

                  return (
                    <button
                      key={type}
                      onClick={() => handleReaction(comment.id, type)}
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors",
                        isSelected
                          ? "bg-primary/20 text-primary"
                          : "hover:bg-muted text-muted-foreground"
                      )}
                      title={config.label}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {count > 0 && <span>{count}</span>}
                    </button>
                  );
                })}
              </div>

              <div className="flex-1" />

              {/* Reply & Edit */}
              {depth < 2 && (
                <button
                  onClick={() => {
                    setReplyingTo(comment.id);
                    setEditingId(null);
                  }}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <Reply className="h-3.5 w-3.5" /> Reply
                </button>
              )}
              {canEdit && (
                <button
                  onClick={() => startEdit(comment)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <Edit className="h-3.5 w-3.5" /> Edit
                </button>
              )}
            </div>
          )}
        </div>

        {/* Reply Form */}
        {isReplying && (
          <div className="ml-6 p-3 rounded-lg bg-muted/20 space-y-2">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="w-full px-3 py-2 rounded-md border bg-background text-sm resize-none"
              rows={2}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setReplyingTo(null)}>
                Cancel
              </Button>
              <Button size="sm" onClick={() => handleReply(comment.id)} disabled={submitting || !replyContent.trim()}>
                {submitting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3 mr-1" />}
                Reply
              </Button>
            </div>
          </div>
        )}

        {/* Nested Replies */}
        {replies.length > 0 && (
          <div className="space-y-2">
            {replies.map((reply) => renderComment(reply, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Sort: pinned first, then by date
  const sortedRootComments = [...rootComments].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="space-y-4">
      {sortedRootComments.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4">
          No comments yet. Be the first to share your thoughts!
        </p>
      ) : (
        sortedRootComments.map((comment) => renderComment(comment))
      )}
    </div>
  );
}
