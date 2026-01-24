"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, Loader2 } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  isLoading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  isLoading = false,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  const handleConfirm = async () => {
    await onConfirm();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={isLoading ? undefined : onClose}
      />

      {/* Dialog */}
      <Card className="relative z-10 w-full max-w-md mx-4 shadow-lg">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2">
            {variant === "destructive" && (
              <AlertTriangle className="h-5 w-5 text-destructive" />
            )}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">{message}</p>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose} disabled={isLoading}>
              {cancelLabel}
            </Button>
            <Button
              variant={variant === "destructive" ? "destructive" : "default"}
              onClick={handleConfirm}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                confirmLabel
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
