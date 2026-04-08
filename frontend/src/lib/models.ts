/**
 * Supported LLM models — single source of truth.
 *
 * For dynamic (provider-aware) model lists, use the available-models API endpoint.
 * This static list is used as fallback for label lookups when the API isn't needed.
 */

export interface ModelInfo {
  value: string;
  label: string;
  provider: string;
}

export const SUPPORTED_MODELS: ModelInfo[] = [
  { value: "anthropic/claude-sonnet-4-5-20250929", label: "Claude Sonnet 4.5", provider: "anthropic" },
  { value: "anthropic/claude-haiku-3-5-20241022", label: "Claude Haiku 3.5", provider: "anthropic" },
  { value: "groq/llama-3.3-70b-versatile", label: "Llama 3.3 70B", provider: "groq" },
  { value: "groq/llama-3.1-8b-instant", label: "Llama 3.1 8B (Fast)", provider: "groq" },
];

/** Look up a human-readable label for a model ID. Falls back to the raw ID. */
export function getModelLabel(modelId: string): string {
  const model = SUPPORTED_MODELS.find((m) => m.value === modelId);
  return model ? model.label : modelId;
}
