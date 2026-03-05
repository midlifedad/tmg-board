"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, Bot, Loader2, AlertTriangle } from "lucide-react";
import { adminApi, type AdminAgentConfig, type ToolInfo } from "@/lib/api";

const SUPPORTED_MODELS = [
  { value: "anthropic/claude-sonnet-4-5-20250929", label: "Claude Sonnet 4.5" },
  { value: "anthropic/claude-haiku-3-5-20241022", label: "Claude Haiku 3.5" },
  { value: "gemini/gemini-2.0-flash", label: "Gemini 2.0 Flash" },
  { value: "gemini/gemini-2.0-flash-lite", label: "Gemini 2.0 Flash Lite" },
  { value: "groq/llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { value: "groq/llama-3.1-8b-instant", label: "Llama 3.1 8B (Fast)" },
];

interface EditAgentModalProps {
  isOpen: boolean;
  agent: AdminAgentConfig | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditAgentModal({ isOpen, agent, onClose, onSuccess }: EditAgentModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [model, setModel] = useState(SUPPORTED_MODELS[0].value);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [temperature, setTemperature] = useState(0.3);
  const [maxIterations, setMaxIterations] = useState(5);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [availableTools, setAvailableTools] = useState<ToolInfo[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && agent) {
      setName(agent.name);
      setDescription(agent.description || "");
      setModel(agent.model);
      setSystemPrompt(agent.system_prompt);
      setTemperature(agent.temperature);
      setMaxIterations(agent.max_iterations);
      setSelectedTools(agent.allowed_tool_names || []);
      setError(null);

      // Load available tools
      adminApi.listAvailableTools().then(setAvailableTools).catch(() => {});
    }
  }, [isOpen, agent]);

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      onClose();
    }
  };

  const toggleTool = (toolName: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolName) ? prev.filter((t) => t !== toolName) : [...prev, toolName]
    );
  };

  // Identify stale tool references (in agent config but not in registry)
  const availableToolNames = availableTools.map((t) => t.name);
  const staleTools = selectedTools.filter(
    (t) => availableTools.length > 0 && !availableToolNames.includes(t)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!agent) return;

    if (!name.trim()) {
      setError("Agent name is required");
      return;
    }
    if (!systemPrompt.trim()) {
      setError("System prompt is required");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // Build partial update with only changed fields
      const changes: Partial<AdminAgentConfig> = {};
      if (name.trim() !== agent.name) changes.name = name.trim();
      if ((description.trim() || null) !== (agent.description || null))
        changes.description = description.trim() || null;
      if (model !== agent.model) changes.model = model;
      if (systemPrompt !== agent.system_prompt) changes.system_prompt = systemPrompt;
      if (temperature !== agent.temperature) changes.temperature = temperature;
      if (maxIterations !== agent.max_iterations) changes.max_iterations = maxIterations;

      const sortedNew = [...selectedTools].sort();
      const sortedOld = [...(agent.allowed_tool_names || [])].sort();
      if (JSON.stringify(sortedNew) !== JSON.stringify(sortedOld))
        changes.allowed_tool_names = selectedTools;

      await adminApi.updateAgent(agent.id, changes);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update agent");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !agent) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <Card className="relative z-10 w-full max-w-lg mx-4 shadow-lg max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Edit Agent
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label className="text-sm font-medium">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Meeting Setup Agent"
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>

            {/* Description */}
            <div>
              <label className="text-sm font-medium">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of what this agent does"
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>

            {/* Model */}
            <div>
              <label className="text-sm font-medium">Model *</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              >
                {SUPPORTED_MODELS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* System Prompt */}
            <div>
              <label className="text-sm font-medium">System Prompt *</label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Enter the agent's system prompt..."
                rows={12}
                className="w-full mt-1 px-3 py-2 rounded-md border bg-background font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-y"
                disabled={submitting}
              />
            </div>

            {/* Temperature & Max Iterations */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Temperature</label>
                <input
                  type="number"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value) || 0)}
                  step={0.1}
                  min={0}
                  max={1}
                  className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Max Iterations</label>
                <input
                  type="number"
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(parseInt(e.target.value) || 1)}
                  min={1}
                  max={20}
                  className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
            </div>

            {/* Tool Assignment */}
            <div>
              <label className="text-sm font-medium">Allowed Tools</label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Select which tools this agent can use
              </p>

              {/* Stale tool warnings */}
              {staleTools.length > 0 && (
                <div className="mt-2 p-2 rounded bg-amber-500/10 border border-amber-500/30">
                  <div className="flex items-center gap-1.5 text-amber-500 text-xs font-medium mb-1">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Stale tool references
                  </div>
                  <p className="text-xs text-muted-foreground">
                    These tools are assigned but no longer in the registry:{" "}
                    {staleTools.map((t, i) => (
                      <span key={t}>
                        {i > 0 && ", "}
                        <span className="font-medium text-amber-400">{t}</span>
                      </span>
                    ))}
                  </p>
                </div>
              )}

              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                {availableTools.length === 0 && (
                  <p className="text-sm text-muted-foreground p-2">No tools available</p>
                )}
                {availableTools.map((tool) => (
                  <label
                    key={tool.name}
                    className="flex items-start gap-3 p-2 rounded hover:bg-muted/20 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTools.includes(tool.name)}
                      onChange={() => toggleTool(tool.name)}
                      className="mt-1 h-4 w-4 rounded border-gray-300"
                      disabled={submitting}
                    />
                    <div>
                      <p className="text-sm font-medium">{tool.name}</p>
                      <p className="text-xs text-muted-foreground">{tool.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Error */}
            {error && <p className="text-sm text-destructive">{error}</p>}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !name.trim() || !systemPrompt.trim()}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
