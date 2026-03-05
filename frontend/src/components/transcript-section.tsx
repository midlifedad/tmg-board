"use client";

import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { meetingsApi, type Transcript } from "@/lib/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TranscriptSectionProps {
  meetingId: string;
  meetingStatus: string;
  isChairOrAdmin: boolean;
  transcript: Transcript | null;
  onTranscriptChanged: () => void;
}

// ---------------------------------------------------------------------------
// TranscriptSection
// ---------------------------------------------------------------------------

export function TranscriptSection({
  meetingId,
  meetingStatus,
  isChairOrAdmin,
  transcript,
  onTranscriptChanged,
}: TranscriptSectionProps) {
  // UI states
  const [showPaste, setShowPaste] = useState(false);
  const [pasteContent, setPasteContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [showReplace, setShowReplace] = useState(false);
  const [replaceContent, setReplaceContent] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Only show for completed meetings
  if (meetingStatus !== "completed") return null;

  const showFeedback = (message: string) => {
    setFeedback(message);
    setTimeout(() => setFeedback(null), 3000);
  };

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const handleSavePaste = async () => {
    if (!pasteContent.trim()) return;
    setSaving(true);
    try {
      await meetingsApi.addTranscript(meetingId, pasteContent);
      setPasteContent("");
      setShowPaste(false);
      showFeedback("Transcript saved successfully");
      onTranscriptChanged();
    } catch (err) {
      showFeedback(
        err instanceof Error ? err.message : "Failed to save transcript"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await meetingsApi.uploadTranscript(meetingId, file);
      showFeedback("Transcript uploaded successfully");
      onTranscriptChanged();
    } catch (err) {
      showFeedback(
        err instanceof Error ? err.message : "Failed to upload transcript"
      );
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleReplace = async () => {
    if (!replaceContent.trim()) return;
    setSaving(true);
    try {
      await meetingsApi.replaceTranscript(meetingId, replaceContent);
      setReplaceContent("");
      setShowReplace(false);
      showFeedback("Transcript replaced successfully");
      onTranscriptChanged();
    } catch (err) {
      showFeedback(
        err instanceof Error ? err.message : "Failed to replace transcript"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await meetingsApi.deleteTranscript(meetingId);
      setShowDeleteConfirm(false);
      showFeedback("Transcript deleted");
      onTranscriptChanged();
    } catch (err) {
      showFeedback(
        err instanceof Error ? err.message : "Failed to delete transcript"
      );
    } finally {
      setDeleting(false);
    }
  };

  // -------------------------------------------------------------------------
  // No transcript state
  // -------------------------------------------------------------------------

  if (!transcript) {
    if (!isChairOrAdmin) {
      return (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Transcript
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground text-center py-2">
              No transcript available
            </p>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Add Transcript
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {feedback && (
            <div className="text-xs text-[var(--gold)] bg-[var(--gold)]/10 border border-[var(--gold)]/20 rounded px-3 py-2">
              {feedback}
            </div>
          )}

          {!showPaste && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 min-h-[44px]"
                onClick={() => setShowPaste(true)}
              >
                <FileText className="h-4 w-4 mr-2" />
                Paste Text
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="flex-1 min-h-[44px]"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Upload File
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                className="hidden"
                onChange={handleFileUpload}
              />
            </div>
          )}

          {showPaste && (
            <div className="space-y-2">
              <textarea
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring min-h-[120px] resize-y"
                placeholder="Paste transcript text here..."
                value={pasteContent}
                onChange={(e) => setPasteContent(e.target.value)}
                autoFocus
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  {pasteContent.length.toLocaleString()} characters
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowPaste(false);
                      setPasteContent("");
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSavePaste}
                    disabled={saving || !pasteContent.trim()}
                    className="bg-[var(--gold)]/20 text-[var(--gold)] hover:bg-[var(--gold)]/30 border border-[var(--gold)]/30"
                  >
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    ) : null}
                    Save Transcript
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // -------------------------------------------------------------------------
  // Transcript exists state
  // -------------------------------------------------------------------------

  return (
    <Card>
      <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Transcript
            <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded">
              {transcript.char_count.toLocaleString()} chars
            </span>
          </CardTitle>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-3">
          {feedback && (
            <div className="text-xs text-[var(--gold)] bg-[var(--gold)]/10 border border-[var(--gold)]/20 rounded px-3 py-2">
              {feedback}
            </div>
          )}

          {/* Transcript content */}
          <div className="max-h-64 overflow-auto rounded-md border bg-muted/30 p-3">
            <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono leading-relaxed">
              {transcript.content}
            </pre>
          </div>

          <div className="text-xs text-muted-foreground">
            Source: {transcript.source}
            {transcript.original_filename && ` (${transcript.original_filename})`}
          </div>

          {/* Chair/admin actions */}
          {isChairOrAdmin && !showReplace && !showDeleteConfirm && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => {
                  setReplaceContent(transcript.content);
                  setShowReplace(true);
                }}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Replace
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Delete
              </Button>
            </div>
          )}

          {/* Replace form */}
          {showReplace && (
            <div className="space-y-2">
              <textarea
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring min-h-[120px] resize-y"
                value={replaceContent}
                onChange={(e) => setReplaceContent(e.target.value)}
                autoFocus
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  {replaceContent.length.toLocaleString()} characters
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowReplace(false);
                      setReplaceContent("");
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleReplace}
                    disabled={saving || !replaceContent.trim()}
                  >
                    {saving && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                    Save
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Delete confirmation */}
          {showDeleteConfirm && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 space-y-2">
              <p className="text-sm text-destructive">
                Delete this transcript? This cannot be undone.
              </p>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Keep
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  Delete
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
