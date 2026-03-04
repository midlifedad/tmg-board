"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { AgentEvent, AgentStreamState, ToolCallEvent } from "@/lib/agent-types";

// ---------------------------------------------------------------------------
// Hook options
// ---------------------------------------------------------------------------

interface UseAgentStreamOptions {
  /** Called after each tool_result event -- use to refresh page data. */
  onToolComplete?: () => void;
}

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const INITIAL_STATE: AgentStreamState = {
  status: "idle",
  agentName: "",
  text: "",
  toolCalls: [],
  error: null,
  usage: null,
};

// ---------------------------------------------------------------------------
// useAgentStream hook
// ---------------------------------------------------------------------------

export function useAgentStream(options?: UseAgentStreamOptions) {
  const [state, setState] = useState<AgentStreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);
  const onToolCompleteRef = useRef(options?.onToolComplete);

  // Keep callback ref in sync without re-creating run()
  useEffect(() => {
    onToolCompleteRef.current = options?.onToolComplete;
  }, [options?.onToolComplete]);

  // -------------------------------------------------------------------------
  // Event handler
  // -------------------------------------------------------------------------

  const handleEvent = useCallback((event: AgentEvent) => {
    switch (event.type) {
      case "start":
        setState((prev) => ({ ...prev, agentName: event.agent_name }));
        break;

      case "text_delta":
        setState((prev) => ({ ...prev, text: prev.text + event.content }));
        break;

      case "tool_start": {
        const newTool: ToolCallEvent = {
          id: event.tool_call_id,
          name: event.tool_name,
          status: "executing",
        };
        setState((prev) => ({
          ...prev,
          toolCalls: [...prev.toolCalls, newTool],
        }));
        break;
      }

      case "tool_result":
        setState((prev) => ({
          ...prev,
          toolCalls: prev.toolCalls.map((tc) =>
            tc.id === event.tool_call_id
              ? {
                  ...tc,
                  status: event.success
                    ? ("completed" as const)
                    : ("failed" as const),
                  result: event.result,
                }
              : tc
          ),
        }));
        // Fire page-data-refresh callback
        onToolCompleteRef.current?.();
        break;

      case "error":
        setState((prev) => ({
          ...prev,
          status: "error",
          error: event.message,
        }));
        break;

      case "usage":
        setState((prev) => ({
          ...prev,
          usage: {
            prompt_tokens: event.prompt_tokens,
            completion_tokens: event.completion_tokens,
            model: event.model,
          },
        }));
        break;

      case "done":
        setState((prev) => ({ ...prev, status: "done" }));
        break;
    }
  }, []);

  // -------------------------------------------------------------------------
  // run() -- invoke an agent via SSE
  // -------------------------------------------------------------------------

  const run = useCallback(
    async (
      agentSlug: string,
      message: string,
      userEmail: string,
      context?: Record<string, unknown>
    ) => {
      // Abort any in-flight request
      abortRef.current?.abort();

      const controller = new AbortController();
      abortRef.current = controller;

      // Reset to streaming state
      setState({
        ...INITIAL_STATE,
        status: "streaming",
      });

      try {
        const response = await fetch("/api/proxy/agents/run", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-Email": userEmail,
          },
          body: JSON.stringify({ agent_slug: agentSlug, message, context }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => "");
          throw new Error(
            errorText || `Agent error: ${response.status} ${response.statusText}`
          );
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        // Buffer-based SSE parsing loop
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last (possibly incomplete) line in the buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const event: AgentEvent = JSON.parse(line.slice(6));
                handleEvent(event);
              } catch {
                // Skip malformed JSON lines
              }
            }
          }
        }

        // Stream ended normally -- mark as done (if not already via "done" event)
        setState((prev) =>
          prev.status === "streaming" ? { ...prev, status: "done" } : prev
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setState((prev) => ({
            ...prev,
            status: "error",
            error: (err as Error).message,
          }));
        }
      }
    },
    [handleEvent]
  );

  // -------------------------------------------------------------------------
  // cancel() -- abort in-flight request, return to idle
  // -------------------------------------------------------------------------

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => ({ ...prev, status: "idle" }));
  }, []);

  // -------------------------------------------------------------------------
  // reset() -- clear all state back to initial
  // -------------------------------------------------------------------------

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  // -------------------------------------------------------------------------
  // Cleanup on unmount
  // -------------------------------------------------------------------------

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { ...state, run, cancel, reset };
}
