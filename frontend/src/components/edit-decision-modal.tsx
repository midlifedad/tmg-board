"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, CheckSquare, Loader2, Calendar, Eye, EyeOff, Users, Clock } from "lucide-react";
import { decisionsApi } from "@/lib/api";

interface EditDecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  decision: {
    id: string;
    title: string;
    description: string | null;
    type: "vote" | "consent" | "resolution";
    deadline: string | null;
    visibility?: "standard" | "anonymous" | "transparent";
    status?: "pending" | "open" | "closed";
  } | null;
}

const visibilityModes = [
  { value: "standard", label: "Standard", description: "Voters see their own vote, admins see all", icon: Eye },
  { value: "anonymous", label: "Anonymous", description: "Only final tally shown, no individual votes", icon: EyeOff },
  { value: "transparent", label: "Transparent", description: "All votes visible to all members", icon: Users },
];

const decisionTypes = [
  { value: "vote", label: "Vote", description: "Standard yes/no/abstain vote" },
  { value: "consent", label: "Consent", description: "Passes unless objection raised" },
  { value: "resolution", label: "Resolution", description: "Formal board resolution" },
];

export function EditDecisionModal({
  isOpen,
  onClose,
  onSuccess,
  decision,
}: EditDecisionModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<"vote" | "consent" | "resolution">("vote");
  const [visibility, setVisibility] = useState<"standard" | "anonymous" | "transparent">("standard");
  const [deadline, setDeadline] = useState("");
  const [extendingDeadline, setExtendingDeadline] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (decision) {
      setTitle(decision.title);
      setDescription(decision.description || "");
      setType(decision.type);
      setVisibility(decision.visibility || "standard");
      setDeadline(decision.deadline?.split("T")[0] || "");
    }
  }, [decision]);

  const handleExtendDeadline = async () => {
    if (!decision || !deadline) return;
    setExtendingDeadline(true);
    try {
      await decisionsApi.extendDeadline(decision.id, deadline);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extend deadline");
    } finally {
      setExtendingDeadline(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!decision) return;

    if (!title.trim()) {
      setError("Please provide a title");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await decisionsApi.update(decision.id, {
        title: title.trim(),
        description: description.trim() || null,
        type,
        deadline: deadline || null,
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update decision");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !decision) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <Card className="relative z-10 w-full max-w-lg mx-4 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="flex items-center gap-2">
            <CheckSquare className="h-5 w-5" />
            Edit Decision
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div>
              <label className="text-sm font-medium">Title *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Approve Q1 Budget"
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>

            {/* Type */}
            <div>
              <label className="text-sm font-medium">Type *</label>
              <div className="mt-2 space-y-2">
                {decisionTypes.map((dt) => (
                  <label
                    key={dt.value}
                    className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${
                      type === dt.value
                        ? "border-primary bg-primary/5"
                        : "border-muted hover:border-muted-foreground/50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="type"
                      value={dt.value}
                      checked={type === dt.value}
                      onChange={(e) => setType(e.target.value as typeof type)}
                      className="sr-only"
                      disabled={submitting}
                    />
                    <div
                      className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                        type === dt.value ? "border-primary" : "border-muted-foreground"
                      }`}
                    >
                      {type === dt.value && (
                        <div className="w-2 h-2 rounded-full bg-primary" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{dt.label}</p>
                      <p className="text-xs text-muted-foreground">{dt.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Deadline */}
            <div>
              <label className="text-sm font-medium">Voting Deadline</label>
              <div className="relative mt-1">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="date"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  className="w-full h-10 pl-10 pr-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Leave blank for no deadline
              </p>
            </div>

            {/* Description */}
            <div>
              <label className="text-sm font-medium">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide context for board members..."
                rows={4}
                className="w-full mt-1 px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                disabled={submitting}
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !title.trim()}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
