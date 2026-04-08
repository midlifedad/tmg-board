"use client";

import { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import { useAgentStream } from "@/hooks/use-agent-stream";
import ReactMarkdown from "react-markdown";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MinutesGeneratorProps {
  meetingId: string;
  meetingTitle: string;
  userEmail: string;
  hasTranscript: boolean;
  onMinutesGenerated?: () => void;
}

// ---------------------------------------------------------------------------
// MinutesGenerator
// ---------------------------------------------------------------------------

export function MinutesGenerator({
  meetingId,
  meetingTitle,
  userEmail,
  hasTranscript,
  onMinutesGenerated,
}: MinutesGeneratorProps) {
  const { status, text, toolCalls, error, run, reset } = useAgentStream();
  const calledRef = useRef(false);

  // Notify parent when generation completes so it can re-fetch minutes
  useEffect(() => {
    if (status === "done" && onMinutesGenerated && !calledRef.current) {
      calledRef.current = true;
      onMinutesGenerated();
    }
    if (status === "idle" || status === "streaming") {
      calledRef.current = false;
    }
  }, [status, onMinutesGenerated]);

  const isStreaming = status === "streaming";
  const isDone = status === "done";
  const isError = status === "error";
  const hasOutput = status !== "idle";

  const handleGenerate = () => {
    run(
      "minutes-generator",
      `Generate formal meeting minutes from the transcript for meeting ${meetingId} ("${meetingTitle}")`,
      userEmail,
      { meeting_id: meetingId }
    );
  };

  // -------------------------------------------------------------------------
  // No transcript
  // -------------------------------------------------------------------------

  if (!hasTranscript) {
    return (
      <Card>
        <CardContent className="py-4">
          <Button
            variant="outline"
            className="w-full min-h-[44px]"
            disabled
            title="Add a transcript first"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Generate Minutes
          </Button>
          <p className="text-xs text-muted-foreground text-center mt-2">
            Add a transcript first
          </p>
        </CardContent>
      </Card>
    );
  }

  // -------------------------------------------------------------------------
  // Has transcript
  // -------------------------------------------------------------------------

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--gold)]" />
          Minutes Generator
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Trigger button */}
        {!hasOutput && (
          <Button
            className="w-full min-h-[44px] bg-[var(--gold)]/20 text-[var(--gold)] hover:bg-[var(--gold)]/30 border border-[var(--gold)]/30"
            onClick={handleGenerate}
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Generate Minutes
          </Button>
        )}

        {/* Streaming / output */}
        {hasOutput && (
          <div className="max-h-96 overflow-y-auto rounded-md border border-gray-800 bg-[#0a0a0a] p-3 space-y-3">
            {/* Thinking indicator */}
            {isStreaming && !text && toolCalls.length === 0 && (
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating minutes...
              </div>
            )}

            {/* Tool calls */}
            {toolCalls.length > 0 && (
              <div className="space-y-1">
                {toolCalls.map((tc) => (
                  <div
                    key={tc.id}
                    className="flex items-center gap-2 text-xs text-muted-foreground"
                  >
                    {tc.status === "executing" ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : tc.status === "completed" ? (
                      <span className="text-green-400">ok</span>
                    ) : (
                      <span className="text-red-400">err</span>
                    )}
                    <span className="font-mono">{tc.name}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Markdown output */}
            {text && (
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-white prose-strong:text-white prose-li:text-gray-300">
                <ReactMarkdown>{text}</ReactMarkdown>
              </div>
            )}

            {/* Error */}
            {isError && error && (
              <div className="rounded-md border border-red-800/50 bg-red-900/20 px-3 py-2 text-sm text-red-400">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {(isDone || isError) && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => {
                reset();
                handleGenerate();
              }}
            >
              <Sparkles className="h-4 w-4 mr-1" />
              Generate Again
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={reset}
            >
              Dismiss
            </Button>
          </div>
        )}

        {/* Cancel during streaming */}
        {isStreaming && (
          <Button variant="outline" size="sm" onClick={reset}>
            Cancel
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
