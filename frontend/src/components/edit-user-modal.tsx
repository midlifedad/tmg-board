"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, UserCog, Loader2 } from "lucide-react";
import { adminApi, type BoardMember } from "@/lib/api";

interface EditUserModalProps {
  isOpen: boolean;
  user: BoardMember | null;
  onClose: () => void;
  onSuccess: () => void;
}

const roles = [
  { value: "member", label: "Member", description: "View-only access to board content" },
  { value: "chair", label: "Chair", description: "Can create and edit content" },
  { value: "admin", label: "Admin", description: "Full access including user management" },
];

export function EditUserModal({ isOpen, user, onClose, onSuccess }: EditUserModalProps) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update form when user changes
  useEffect(() => {
    if (user) {
      setName(user.name);
      setRole(user.role);
      setError(null);
    }
  }, [user]);

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

    if (!name.trim()) {
      setError("Please provide a name");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await adminApi.updateUser(String(user.id), {
        name: name.trim(),
        role,
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !user) return null;

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
          <CardTitle className="flex items-center gap-2">
            <UserCog className="h-5 w-5" />
            Edit User
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email (read-only) */}
            <div>
              <label className="text-sm font-medium">Email Address</label>
              <input
                type="email"
                value={user.email}
                className="w-full mt-1 h-10 px-3 rounded-md border bg-muted text-sm text-muted-foreground cursor-not-allowed"
                disabled
              />
              <p className="text-xs text-muted-foreground mt-1">
                Email cannot be changed
              </p>
            </div>

            {/* Name */}
            <div>
              <label className="text-sm font-medium">Full Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Doe"
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>

            {/* Role */}
            <div>
              <label className="text-sm font-medium">Role *</label>
              <div className="mt-2 space-y-2">
                {roles.map((r) => (
                  <label
                    key={r.value}
                    className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${
                      role === r.value
                        ? "border-primary bg-primary/5"
                        : "border-muted hover:border-muted-foreground/50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="role"
                      value={r.value}
                      checked={role === r.value}
                      onChange={(e) => setRole(e.target.value)}
                      className="sr-only"
                      disabled={submitting}
                    />
                    <div
                      className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                        role === r.value ? "border-primary" : "border-muted-foreground"
                      }`}
                    >
                      {role === r.value && (
                        <div className="w-2 h-2 rounded-full bg-primary" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{r.label}</p>
                      <p className="text-xs text-muted-foreground">{r.description}</p>
                    </div>
                  </label>
                ))}
              </div>
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
              <Button type="submit" disabled={submitting || !name.trim()}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <UserCog className="h-4 w-4 mr-2" />
                    Save Changes
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
