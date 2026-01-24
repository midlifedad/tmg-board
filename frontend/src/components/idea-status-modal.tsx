"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, Loader2, CheckCircle, XCircle, Clock, ArrowUpRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { ideasApi, type Idea } from "@/lib/api";

type IdeaStatus = Idea["status"];

interface IdeaStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  idea: {
    id: string;
    title: string;
    status: IdeaStatus;
  } | null;
}

const statusOptions: Array<{
  value: IdeaStatus;
  label: string;
  description: string;
  icon: typeof CheckCircle;
  color: string;
}> = [
  {
    value: "new",
    label: "New",
    description: "Recently submitted, awaiting review",
    icon: Sparkles,
    color: "text-blue-400",
  },
  {
    value: "under_review",
    label: "Under Review",
    description: "Being evaluated by the board",
    icon: Clock,
    color: "text-amber-400",
  },
  {
    value: "approved",
    label: "Approved",
    description: "Accepted for further action",
    icon: CheckCircle,
    color: "text-green-400",
  },
  {
    value: "rejected",
    label: "Rejected",
    description: "Not accepted at this time",
    icon: XCircle,
    color: "text-red-400",
  },
  {
    value: "promoted",
    label: "Promoted",
    description: "Converted to a board decision",
    icon: ArrowUpRight,
    color: "text-purple-400",
  },
];

export function IdeaStatusModal({
  isOpen,
  onClose,
  onSuccess,
  idea,
}: IdeaStatusModalProps) {
  const [selectedStatus, setSelectedStatus] = useState<IdeaStatus | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    if (!submitting) {
      setSelectedStatus(null);
      setReason("");
      setError(null);
      onClose();
    }
  };

  const handleSubmit = async () => {
    if (!idea || !selectedStatus) return;

    // Require reason for rejection
    if (selectedStatus === "rejected" && !reason.trim()) {
      setError("Please provide a reason for rejection");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      if (selectedStatus === "promoted") {
        // Use promote endpoint which creates a decision
        await ideasApi.promote(idea.id);
      } else {
        await ideasApi.updateStatusWithReason(idea.id, selectedStatus, reason.trim() || undefined);
      }

      handleClose();
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !idea) return null;

  const currentOption = statusOptions.find((s) => s.value === idea.status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <Card className="relative z-10 w-full max-w-md mx-4 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-base">Update Idea Status</CardTitle>
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Idea Title */}
          <div className="p-3 rounded-lg bg-muted/50">
            <p className="text-sm font-medium">{idea.title}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Current status: <span className={currentOption?.color}>{currentOption?.label}</span>
            </p>
          </div>

          {/* Status Options */}
          <div className="space-y-2">
            <label className="text-sm font-medium">New Status</label>
            <div className="grid gap-2">
              {statusOptions
                .filter((s) => s.value !== idea.status)
                .map((option) => {
                  const Icon = option.icon;
                  const isSelected = selectedStatus === option.value;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedStatus(option.value)}
                      className={cn(
                        "flex items-center gap-3 p-3 rounded-lg border text-left transition-colors",
                        isSelected
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-muted-foreground/50"
                      )}
                      disabled={submitting}
                    >
                      <Icon className={cn("h-5 w-5", option.color)} />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{option.label}</p>
                        <p className="text-xs text-muted-foreground">{option.description}</p>
                      </div>
                      {isSelected && (
                        <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                          <CheckCircle className="h-3 w-3 text-primary-foreground" />
                        </div>
                      )}
                    </button>
                  );
                })}
            </div>
          </div>

          {/* Reason (shown for rejection, optional for others) */}
          {selectedStatus && (
            <div>
              <label className="text-sm font-medium">
                Reason {selectedStatus === "rejected" ? "*" : "(optional)"}
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={
                  selectedStatus === "rejected"
                    ? "Please explain why this idea was rejected..."
                    : "Add a note about this status change..."
                }
                rows={3}
                className="w-full mt-1 px-3 py-2 rounded-md border bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>
          )}

          {/* Promote Warning */}
          {selectedStatus === "promoted" && (
            <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <p className="text-xs text-purple-400">
                This will create a new board decision from this idea. The idea will be marked as "Promoted" and linked to the decision.
              </p>
            </div>
          )}

          {/* Error */}
          {error && <p className="text-sm text-destructive">{error}</p>}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={handleClose} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || !selectedStatus}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Updating...
                </>
              ) : selectedStatus === "promoted" ? (
                "Promote to Decision"
              ) : (
                "Update Status"
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
