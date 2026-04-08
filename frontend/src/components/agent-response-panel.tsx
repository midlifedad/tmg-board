"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { useAgentStream } from "@/hooks/use-agent-stream";
import { ToolCallIndicator } from "@/components/tool-call-indicator";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AgentResponsePanelProps {
  agentSlug: string;
  context?: Record<string, unknown>;
  onToolComplete?: () => void;
  title?: string;
  placeholder?: string;
  userEmail: string;
}

// ---------------------------------------------------------------------------
// AgentResponsePanel
// ---------------------------------------------------------------------------

export function AgentResponsePanel({
  agentSlug,
  context,
  onToolComplete,
  title = "AI Assistant",
  placeholder = "Ask the assistant...",
  userEmail,
}: AgentResponsePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    status,
    agentName,
    text,
    toolCalls,
    error,
    usage,
    run,
    cancel,
    reset,
  } = useAgentStream({ onToolComplete });

  // Auto-scroll during streaming
  useEffect(() => {
    if (status === "streaming") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [text, toolCalls, status]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  const handleRun = () => {
    if (!inputMessage.trim() || status === "streaming") return;
    run(agentSlug, inputMessage.trim(), userEmail, context);
    setInputMessage("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleRun();
    }
  };

  // -----------------------------------------------------------------------
  // Collapsed view
  // -----------------------------------------------------------------------

  if (!isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="w-full rounded-md border border-gray-800 bg-[#1a1a1a] px-4 py-3 flex items-center justify-between hover:border-gold/30 transition-colors group"
        aria-label={`Expand ${title} panel`}
      >
        <span className="flex items-center gap-2">
          {/* AI sparkle icon */}
          <svg
            className="h-4 w-4 text-gold"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3v2m0 14v2M5.6 5.6l1.4 1.4m10 10l1.4 1.4M3 12h2m14 0h2M5.6 18.4l1.4-1.4m10-10l1.4-1.4" />
            <circle cx="12" cy="12" r="4" />
          </svg>
          <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
            {title}
          </span>
        </span>

        {/* Expand chevron */}
        <svg
          className="h-4 w-4 text-gray-500 group-hover:text-gray-300 transition-colors"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    );
  }

  // -----------------------------------------------------------------------
  // Expanded view
  // -----------------------------------------------------------------------

  const displayName = agentName || title;
  const isStreaming = status === "streaming";
  const isDone = status === "done";
  const isError = status === "error";
  const hasOutput = status !== "idle";

  return (
    <Card className="border-gray-800 bg-[#1a1a1a] border-t-2 border-t-gold/40">
      {/* Header */}
      <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <svg
            className="h-4 w-4 text-gold"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3v2m0 14v2M5.6 5.6l1.4 1.4m10 10l1.4 1.4M3 12h2m14 0h2M5.6 18.4l1.4-1.4m10-10l1.4-1.4" />
            <circle cx="12" cy="12" r="4" />
          </svg>
          <span className="text-sm font-medium text-white">{displayName}</span>
        </div>
        <button
          onClick={() => setIsExpanded(false)}
          className="text-gray-500 hover:text-gray-300 transition-colors p-1"
          aria-label="Collapse panel"
        >
          <svg
            className="h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </CardHeader>

      <CardContent className="p-4 pt-2 space-y-3">
        {/* Input area */}
        <div className="flex gap-2">
          <textarea
            className="flex-1 resize-none rounded-md border border-gray-700 bg-[#0a0a0a] px-3 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-gold/50 focus:border-gold/30 disabled:opacity-50"
            rows={2}
            placeholder={placeholder}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            aria-label="Message to agent"
          />
          <Button
            size="sm"
            className="self-end bg-gold/20 text-gold hover:bg-gold/30 border border-gold/30"
            onClick={handleRun}
            disabled={isStreaming || !inputMessage.trim()}
            aria-label="Run agent"
          >
            Run
          </Button>
        </div>

        {/* Output area */}
        {hasOutput && (
          <div className="max-h-96 overflow-y-auto rounded-md border border-gray-800 bg-[#0a0a0a] p-3 space-y-3">
            {/* Thinking indicator before first text */}
            {isStreaming && !text && toolCalls.length === 0 && (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <svg
                  className="h-4 w-4 animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  />
                </svg>
                Thinking...
              </div>
            )}

            {/* Streaming text output with markdown rendering */}
            {text && (
              <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-white prose-strong:text-white prose-li:text-gray-300 prose-code:text-gold prose-code:bg-gray-800 prose-code:rounded prose-code:px-1">
                <ReactMarkdown>{text}</ReactMarkdown>
              </div>
            )}

            {/* Tool call indicators */}
            {toolCalls.length > 0 && (
              <div className="space-y-2" aria-live="polite">
                {toolCalls.map((tc) => (
                  <ToolCallIndicator key={tc.id} toolCall={tc} />
                ))}
              </div>
            )}

            {/* Error display */}
            {isError && error && (
              <div className="rounded-md border border-red-800/50 bg-red-900/20 px-3 py-2 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
          </div>
        )}
      </CardContent>

      {/* Footer: actions and usage */}
      {(isStreaming || isDone || isError) && (
        <CardFooter className="p-4 pt-0 flex items-center justify-between">
          <div className="flex gap-2">
            {isStreaming && (
              <Button
                size="sm"
                variant="outline"
                className="border-gray-700 text-gray-400 hover:text-white"
                onClick={cancel}
                aria-label="Cancel agent request"
              >
                Cancel
              </Button>
            )}
            {isDone && (
              <Button
                size="sm"
                variant="outline"
                className="border-gray-700 text-gray-400 hover:text-white"
                onClick={reset}
                aria-label="Clear agent response"
              >
                Clear
              </Button>
            )}
            {isError && (
              <Button
                size="sm"
                variant="outline"
                className="border-gray-700 text-gray-400 hover:text-white"
                onClick={() => {
                  reset();
                }}
                aria-label="Dismiss error"
              >
                Dismiss
              </Button>
            )}
          </div>

          {/* Usage info */}
          {isDone && usage && (
            <span className="text-xs text-gray-500">
              {usage.model.split("/").pop()} | {usage.prompt_tokens + usage.completion_tokens} tokens
            </span>
          )}
        </CardFooter>
      )}
    </Card>
  );
}
