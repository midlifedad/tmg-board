"use client";

import { useState } from "react";
import { Loader2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { generationApi, MeetingMinutesResponse, ApiError } from "@/lib/api";

interface GenerateMinutesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (minutes: MeetingMinutesResponse) => void;
  meetingId: string;
}

export function GenerateMinutesModal({
  isOpen,
  onClose,
  onSuccess,
  meetingId,
}: GenerateMinutesModalProps) {
  const [transcript, setTranscript] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!transcript.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generationApi.generateMinutes(meetingId, transcript);
      onSuccess(result);
      onClose();
      setTranscript("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => !generating && onClose()}
      />
      <Card className="relative z-10 w-full max-w-2xl mx-4 shadow-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-[var(--gold)]" />
            Generate Meeting Minutes
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Paste the full meeting transcript below. AI will generate formal board minutes.
          </p>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste your meeting transcript here..."
            rows={12}
            disabled={generating}
            className="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {error && (
            <p className="text-sm text-destructive border border-destructive/30 rounded-md px-3 py-2 bg-destructive/10">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={generating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={!transcript.trim() || generating}
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Minutes
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
