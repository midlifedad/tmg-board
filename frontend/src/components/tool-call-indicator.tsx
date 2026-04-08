"use client";

import type { ToolCallEvent } from "@/lib/agent-types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert snake_case to Title Case (e.g. "create_agenda_item" -> "Create Agenda Item") */
function toTitleCase(snakeCase: string): string {
  return snakeCase
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

// ---------------------------------------------------------------------------
// ToolCallIndicator
// ---------------------------------------------------------------------------

interface ToolCallIndicatorProps {
  toolCall: ToolCallEvent;
}

export function ToolCallIndicator({ toolCall }: ToolCallIndicatorProps) {
  return (
    <div className="rounded-md px-3 py-2 bg-[#1a1a1a] border border-gray-800 text-sm">
      <div className="flex items-center gap-2">
        {/* Status icon */}
        {toolCall.status === "executing" && (
          <svg
            className="h-4 w-4 animate-spin text-blue-400"
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
        )}

        {toolCall.status === "completed" && (
          <svg
            className="h-4 w-4 text-green-400"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}

        {toolCall.status === "failed" && (
          <svg
            className="h-4 w-4 text-red-400"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        )}

        {/* Tool name */}
        <span className="font-medium text-gray-200">
          {toTitleCase(toolCall.name)}
        </span>

        {/* Status text */}
        {toolCall.status === "executing" && (
          <span className="text-blue-400 text-xs">Running...</span>
        )}
        {toolCall.status === "completed" && (
          <span className="text-green-400 text-xs">Done</span>
        )}
        {toolCall.status === "failed" && (
          <span className="text-red-400 text-xs">Failed</span>
        )}
      </div>

      {/* Truncated result for completed tool calls */}
      {toolCall.result && toolCall.status === "completed" && (
        <p className="mt-1 text-xs text-gray-500 truncate max-w-full">
          {toolCall.result.length > 100
            ? toolCall.result.slice(0, 100) + "..."
            : toolCall.result}
        </p>
      )}
    </div>
  );
}
