"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Bot,
  Plus,
  BarChart3,
  Pencil,
  Trash2,
  Loader2,
  Power,
  PowerOff,
  DollarSign,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  adminApi,
  api,
  type AdminAgentConfig,
  type AgentUsageStats,
} from "@/lib/api";
import { usePermissions } from "@/hooks/use-permissions";
import { CreateAgentModal } from "@/components/create-agent-modal";
import { EditAgentModal } from "@/components/edit-agent-modal";

const MODEL_LABELS: Record<string, string> = {
  "anthropic/claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
  "anthropic/claude-haiku-3-5-20241022": "Claude Haiku 3.5",
  "gemini/gemini-2.0-flash": "Gemini 2.0 Flash",
  "gemini/gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
  "groq/llama-3.3-70b-versatile": "Llama 3.3 70B",
  "groq/llama-3.1-8b-instant": "Llama 3.1 8B (Fast)",
};

function getModelLabel(modelId: string): string {
  return MODEL_LABELS[modelId] || modelId;
}

export default function AdminAgentsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { isAdmin, isLoading: permissionsLoading } = usePermissions();

  const [agents, setAgents] = useState<AdminAgentConfig[]>([]);
  const [usageStats, setUsageStats] = useState<AgentUsageStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"agents" | "usage">("agents");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AdminAgentConfig | null>(null);

  useEffect(() => {
    if (!permissionsLoading && !isAdmin) {
      router.push("/");
    }
  }, [isAdmin, permissionsLoading, router]);

  useEffect(() => {
    const email = session?.user?.email;
    if (!email) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        api.setUserEmail(email);

        const [agentsData, usageData] = await Promise.all([
          adminApi.listAgents(true).catch(() => []),
          adminApi.getAgentUsageStats().catch(() => []),
        ]);

        setAgents(agentsData);
        setUsageStats(usageData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    if (isAdmin) {
      fetchData();
    }
  }, [session?.user?.email, isAdmin]);

  const refetchData = async () => {
    try {
      const [agentsData, usageData] = await Promise.all([
        adminApi.listAgents(true).catch(() => []),
        adminApi.getAgentUsageStats().catch(() => []),
      ]);
      setAgents(agentsData);
      setUsageStats(usageData);
    } catch (err) {
      console.error("Failed to refetch data:", err);
    }
  };

  const handleEditAgent = (agent: AdminAgentConfig) => {
    setSelectedAgent(agent);
    setShowEditModal(true);
  };

  const handleDeleteAgent = async (agent: AdminAgentConfig) => {
    if (
      !window.confirm(
        `Are you sure you want to deactivate ${agent.name}? This will prevent users from invoking this agent.`
      )
    )
      return;

    try {
      await adminApi.deleteAgent(agent.id);
      refetchData();
    } catch (err) {
      console.error("Failed to deactivate agent:", err);
    }
  };

  // Computed stats
  const activeAgents = agents.filter((a) => a.is_active);
  const totalCalls = usageStats.reduce((sum, s) => sum + s.total_calls, 0);
  const totalCost = usageStats.reduce((sum, s) => sum + s.total_cost_usd, 0);

  if (permissionsLoading || loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
              <span>Administration</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            <h1 className="text-3xl font-light">Agent Management</h1>
            <p className="text-sm font-light text-muted-foreground mt-1">
              Configure AI agents, assign tools, and monitor usage
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Agent
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Agents</p>
                  <p className="text-2xl font-bold">{agents.length}</p>
                </div>
                <Bot className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Agents</p>
                  <p className="text-2xl font-bold">{activeAgents.length}</p>
                </div>
                <Power className="h-8 w-8 text-green-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total API Calls</p>
                  <p className="text-2xl font-bold">{totalCalls.toLocaleString()}</p>
                </div>
                <Activity className="h-8 w-8 text-blue-500/50" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Est. Total Cost</p>
                  <p className="text-2xl font-bold">${totalCost.toFixed(2)}</p>
                </div>
                <DollarSign className="h-8 w-8 text-amber-500/50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <Button
            variant={activeTab === "agents" ? "default" : "outline"}
            onClick={() => setActiveTab("agents")}
          >
            <Bot className="h-4 w-4 mr-2" />
            Agents ({agents.length})
          </Button>
          <Button
            variant={activeTab === "usage" ? "default" : "outline"}
            onClick={() => setActiveTab("usage")}
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Usage
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded-md bg-destructive/10 text-destructive">
            {error}
          </div>
        )}

        {/* Agents Tab */}
        {activeTab === "agents" && (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium text-sm">Name</th>
                      <th className="text-left p-4 font-medium text-sm">Model</th>
                      <th className="text-left p-4 font-medium text-sm">Tools</th>
                      <th className="text-left p-4 font-medium text-sm">Status</th>
                      <th className="text-right p-4 font-medium text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((agent) => (
                      <tr
                        key={agent.id}
                        className={cn(
                          "border-b last:border-0 hover:bg-muted/20 transition-colors",
                          !agent.is_active && "opacity-50"
                        )}
                      >
                        <td className="p-4">
                          <div>
                            <p className="font-medium">{agent.name}</p>
                            {agent.description && (
                              <p className="text-sm text-muted-foreground mt-0.5">
                                {agent.description}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <span className="text-sm">{getModelLabel(agent.model)}</span>
                        </td>
                        <td className="p-4">
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted">
                            {agent.allowed_tool_names?.length || 0} tools
                          </span>
                        </td>
                        <td className="p-4">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium",
                              agent.is_active
                                ? "bg-green-500/20 text-green-400"
                                : "bg-red-500/20 text-red-400"
                            )}
                          >
                            {agent.is_active ? (
                              <Power className="h-3 w-3" />
                            ) : (
                              <PowerOff className="h-3 w-3" />
                            )}
                            {agent.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditAgent(agent)}
                            >
                              <Pencil className="h-3.5 w-3.5 mr-1" />
                              Edit
                            </Button>
                            {agent.is_active && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive/80"
                                onClick={() => handleDeleteAgent(agent)}
                              >
                                <Trash2 className="h-3.5 w-3.5 mr-1" />
                                Deactivate
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {agents.length === 0 && (
                  <div className="p-8 text-center text-muted-foreground">
                    No agents configured yet. Click &quot;New Agent&quot; to create one.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Usage Tab */}
        {activeTab === "usage" && (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 font-medium text-sm">Agent</th>
                      <th className="text-right p-4 font-medium text-sm">Total Calls</th>
                      <th className="text-right p-4 font-medium text-sm">Prompt Tokens</th>
                      <th className="text-right p-4 font-medium text-sm">Completion Tokens</th>
                      <th className="text-right p-4 font-medium text-sm">Total Cost ($)</th>
                      <th className="text-right p-4 font-medium text-sm">Avg Duration (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usageStats.map((stat) => (
                      <tr
                        key={stat.agent_id}
                        className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                      >
                        <td className="p-4 font-medium text-sm">{stat.agent_name}</td>
                        <td className="p-4 text-right text-sm">
                          {stat.total_calls.toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {stat.total_prompt_tokens.toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {stat.total_completion_tokens.toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          ${stat.total_cost_usd.toFixed(4)}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {Math.round(stat.avg_duration_ms).toLocaleString()}
                        </td>
                      </tr>
                    ))}

                    {/* Totals row */}
                    {usageStats.length > 0 && (
                      <tr className="border-t-2 bg-muted/30 font-bold">
                        <td className="p-4 text-sm">Total</td>
                        <td className="p-4 text-right text-sm">
                          {usageStats
                            .reduce((sum, s) => sum + s.total_calls, 0)
                            .toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {usageStats
                            .reduce((sum, s) => sum + s.total_prompt_tokens, 0)
                            .toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {usageStats
                            .reduce((sum, s) => sum + s.total_completion_tokens, 0)
                            .toLocaleString()}
                        </td>
                        <td className="p-4 text-right text-sm">
                          $
                          {usageStats
                            .reduce((sum, s) => sum + s.total_cost_usd, 0)
                            .toFixed(4)}
                        </td>
                        <td className="p-4 text-right text-sm">-</td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {usageStats.length === 0 && (
                  <div className="p-8 text-center text-muted-foreground">
                    No usage data yet. Stats will appear after agents are invoked.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create Modal */}
      <CreateAgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={refetchData}
      />

      {/* Edit Modal */}
      <EditAgentModal
        isOpen={showEditModal}
        agent={selectedAgent}
        onClose={() => {
          setShowEditModal(false);
          setSelectedAgent(null);
        }}
        onSuccess={refetchData}
      />
    </AppShell>
  );
}
