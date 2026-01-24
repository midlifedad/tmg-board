"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, CheckSquare, Loader2, Calendar, Eye, EyeOff, Users } from "lucide-react";
import { decisionsApi } from "@/lib/api";

interface CreateDecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const decisionTypes = [
  { value: "vote", label: "Vote", description: "Standard yes/no/abstain vote" },
  { value: "consent", label: "Consent", description: "Passes unless objection raised" },
  { value: "resolution", label: "Resolution", description: "Formal board resolution" },
];

const visibilityModes = [
  { value: "standard", label: "Standard", description: "Voters see their own vote, admins see all", icon: Eye },
  { value: "anonymous", label: "Anonymous", description: "Only final tally shown, no individual votes", icon: EyeOff },
  { value: "transparent", label: "Transparent", description: "All votes visible to all members", icon: Users },
];

export function CreateDecisionModal({ isOpen, onClose, onSuccess }: CreateDecisionModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("vote");
  const [visibility, setVisibility] = useState<"standard" | "anonymous" | "transparent">("standard");
  const [deadline, setDeadline] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setType("vote");
    setVisibility("standard");
    setDeadline("");
    setError(null);
  };

  const handleClose = () => {
    if (!submitting) {
      resetForm();
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim()) {
      setError("Please provide a title");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await decisionsApi.create({
        title: title.trim(),
        description: description.trim() || null,
        type: type as "vote" | "consent" | "resolution",
        deadline: deadline || null,
        visibility,
      });

      resetForm();
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create decision");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  // Calculate minimum date (today)
  const today = new Date().toISOString().split("T")[0];

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
            New Decision
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
                      onChange={(e) => setType(e.target.value)}
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

            {/* Visibility Mode */}
            <div>
              <label className="text-sm font-medium">Voting Visibility</label>
              <div className="mt-2 grid grid-cols-3 gap-2">
                {visibilityModes.map((vm) => {
                  const Icon = vm.icon;
                  return (
                    <button
                      key={vm.value}
                      type="button"
                      onClick={() => setVisibility(vm.value as typeof visibility)}
                      className={`flex flex-col items-center gap-1 p-3 rounded-md border transition-colors ${
                        visibility === vm.value
                          ? "border-primary bg-primary/5"
                          : "border-muted hover:border-muted-foreground/50"
                      }`}
                      disabled={submitting}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-xs font-medium">{vm.label}</span>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {visibilityModes.find((v) => v.value === visibility)?.description}
              </p>
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
                  min={today}
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
                    Creating...
                  </>
                ) : (
                  <>
                    <CheckSquare className="h-4 w-4 mr-2" />
                    Open for Voting
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
