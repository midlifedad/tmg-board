/**
 * Shared TypeScript types for the agent SSE event protocol and stream state.
 *
 * These types mirror the backend SSE event format defined in
 * backend/app/services/agent_runner.py and consumed by the
 * useAgentStream hook.
 */

// ---------------------------------------------------------------------------
// SSE Event Types (wire protocol)
// ---------------------------------------------------------------------------

export type AgentEvent =
  | { type: "start"; agent_name: string }
  | { type: "text_delta"; content: string }
  | { type: "tool_start"; tool_name: string; tool_call_id: string }
  | {
      type: "tool_result";
      tool_name: string;
      tool_call_id: string;
      result: string;
      success: boolean;
    }
  | { type: "error"; message: string }
  | {
      type: "usage";
      prompt_tokens: number;
      completion_tokens: number;
      model: string;
    }
  | { type: "done" };

// ---------------------------------------------------------------------------
// Tool Call State (frontend tracking)
// ---------------------------------------------------------------------------

export interface ToolCallEvent {
  id: string;
  name: string;
  status: "executing" | "completed" | "failed";
  result?: string;
}

// ---------------------------------------------------------------------------
// Agent Stream State (hook state shape)
// ---------------------------------------------------------------------------

export interface AgentStreamState {
  status: "idle" | "streaming" | "done" | "error";
  agentName: string;
  text: string;
  toolCalls: ToolCallEvent[];
  error: string | null;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    model: string;
  } | null;
}
