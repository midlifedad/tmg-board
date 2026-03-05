"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  ArrowLeft,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Shield,
  Plus,
  Trash2,
  Loader2,
  FileText,
} from "lucide-react";
import {
  meetingsApi,
  templatesApi,
  api,
  type MeetingTemplate,
  type TemplateDetail,
} from "@/lib/api";
import { useAgentStream } from "@/hooks/use-agent-stream";
import { ToolCallIndicator } from "@/components/tool-call-indicator";
import ReactMarkdown from "react-markdown";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LocalAgendaItem {
  id: string; // local UUID
  title: string;
  description: string;
  item_type: string;
  duration_minutes: number;
  is_regulatory: boolean;
}

const ITEM_TYPE_OPTIONS = [
  { value: "information", label: "Information" },
  { value: "discussion", label: "Discussion" },
  { value: "decision_required", label: "Decision Required" },
  { value: "consent_agenda", label: "Consent Agenda" },
];

function itemTypeBadgeColor(itemType: string): string {
  switch (itemType) {
    case "decision_required":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "discussion":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    case "consent_agenda":
      return "bg-purple-500/20 text-purple-400 border-purple-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

function itemTypeLabel(itemType: string): string {
  const opt = ITEM_TYPE_OPTIONS.find((o) => o.value === itemType);
  return opt?.label || itemType;
}

let localIdCounter = 0;
function newLocalId(): string {
  localIdCounter += 1;
  return `local-${Date.now()}-${localIdCounter}`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CreateMeetingPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const userEmail = session?.user?.email || "";

  // AI section
  const [aiExpanded, setAiExpanded] = useState(true);
  const [aiDescription, setAiDescription] = useState("");
  const {
    status: agentStatus,
    text: agentText,
    toolCalls,
    error: agentError,
    usage: agentUsage,
    run: runAgent,
    cancel: cancelAgent,
    reset: resetAgent,
  } = useAgentStream({
    onToolComplete: () => {
      // Check the latest tool result for create_meeting_with_agenda success
    },
  });

  // Watch for successful meeting creation from agent
  useEffect(() => {
    const createTool = toolCalls.find(
      (tc) =>
        tc.name === "create_meeting_with_agenda" && tc.status === "completed"
    );
    if (createTool?.result) {
      try {
        const parsed = JSON.parse(createTool.result);
        if (parsed.id) {
          // Short delay to let user see the success state
          setTimeout(() => {
            router.push(`/meetings/${parsed.id}`);
          }, 1500);
        }
      } catch {
        // result not JSON, ignore
      }
    }
  }, [toolCalls, router]);

  // Template selector
  const [templates, setTemplates] = useState<MeetingTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [selectedTemplate, setSelectedTemplate] =
    useState<TemplateDetail | null>(null);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  // Form fields
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [duration, setDuration] = useState("60");
  const [location, setLocation] = useState("");
  const [meetingLink, setMeetingLink] = useState("");
  const [description, setDescription] = useState("");

  // Agenda items
  const [agendaItems, setAgendaItems] = useState<LocalAgendaItem[]>([]);
  const [showAddItem, setShowAddItem] = useState(false);
  const [newItemTitle, setNewItemTitle] = useState("");
  const [newItemType, setNewItemType] = useState("discussion");
  const [newItemDuration, setNewItemDuration] = useState("10");
  const [newItemDescription, setNewItemDescription] = useState("");

  // Submission
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Regulatory removal confirmation
  const [removingItemId, setRemovingItemId] = useState<string | null>(null);

  // Fetch templates on mount
  useEffect(() => {
    if (userEmail) {
      api.setUserEmail(userEmail);
      templatesApi.list().then(setTemplates).catch(console.error);
    }
  }, [userEmail]);

  // Load template when selected
  useEffect(() => {
    if (!selectedTemplateId) {
      setSelectedTemplate(null);
      return;
    }
    const id = parseInt(selectedTemplateId);
    if (isNaN(id)) return;

    setLoadingTemplate(true);
    templatesApi
      .get(id)
      .then((tpl) => {
        setSelectedTemplate(tpl);
        // Pre-fill form defaults
        if (tpl.default_duration_minutes) {
          setDuration(String(tpl.default_duration_minutes));
        }
        if (tpl.default_location) {
          setLocation(tpl.default_location);
        }
        // Populate agenda items from template
        setAgendaItems(
          tpl.items.map((item) => ({
            id: newLocalId(),
            title: item.title,
            description: item.description || "",
            item_type: item.item_type,
            duration_minutes: item.duration_minutes || 10,
            is_regulatory: item.is_regulatory,
          }))
        );
      })
      .catch(console.error)
      .finally(() => setLoadingTemplate(false));
  }, [selectedTemplateId]);

  // Agenda item actions
  const addAgendaItem = useCallback(() => {
    if (!newItemTitle.trim()) return;
    setAgendaItems((prev) => [
      ...prev,
      {
        id: newLocalId(),
        title: newItemTitle.trim(),
        description: newItemDescription.trim(),
        item_type: newItemType,
        duration_minutes: parseInt(newItemDuration) || 10,
        is_regulatory: false,
      },
    ]);
    setNewItemTitle("");
    setNewItemDescription("");
    setNewItemType("discussion");
    setNewItemDuration("10");
    setShowAddItem(false);
  }, [newItemTitle, newItemDescription, newItemType, newItemDuration]);

  const removeAgendaItem = useCallback(
    (itemId: string) => {
      const item = agendaItems.find((i) => i.id === itemId);
      if (item?.is_regulatory && removingItemId !== itemId) {
        setRemovingItemId(itemId);
        return;
      }
      setAgendaItems((prev) => prev.filter((i) => i.id !== itemId));
      setRemovingItemId(null);
    },
    [agendaItems, removingItemId]
  );

  const moveItem = useCallback((index: number, direction: "up" | "down") => {
    setAgendaItems((prev) => {
      const next = [...prev];
      const swapIndex = direction === "up" ? index - 1 : index + 1;
      if (swapIndex < 0 || swapIndex >= next.length) return prev;
      [next[index], next[swapIndex]] = [next[swapIndex], next[index]];
      return next;
    });
  }, []);

  // Parse with AI
  const handleParseWithAI = () => {
    if (!aiDescription.trim() || agentStatus === "streaming") return;
    runAgent("meeting-setup", aiDescription.trim(), userEmail);
  };

  // Submit manual form
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setFormError("Title is required");
      return;
    }
    if (!date) {
      setFormError("Date is required");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const meeting = await meetingsApi.createWithAgenda({
        title: title.trim(),
        date: date,
        duration_minutes: parseInt(duration) || undefined,
        location: location.trim() || undefined,
        meeting_link: meetingLink.trim() || undefined,
        description: description.trim() || undefined,
        template_id: selectedTemplateId
          ? parseInt(selectedTemplateId)
          : undefined,
        agenda_items: agendaItems.map((item) => ({
          title: item.title,
          description: item.description || undefined,
          item_type: item.item_type,
          duration_minutes: item.duration_minutes,
        })),
      });
      router.push(`/meetings/${meeting.id}`);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create meeting"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const isAgentStreaming = agentStatus === "streaming";
  const isAgentDone = agentStatus === "done";
  const isAgentError = agentStatus === "error";
  const hasAgentOutput = agentStatus !== "idle";

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <Link
            href="/meetings"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-white transition-colors mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Meetings
          </Link>
          <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
            <span>Create Meeting</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <h1 className="text-3xl font-light">Create Meeting</h1>
        </div>

        {/* AI-Assisted Section */}
        <Card className="border-gray-800 bg-[#1a1a2e] border-t-2 border-t-[var(--gold)]/40">
          <CardHeader
            className="p-4 pb-2 cursor-pointer"
            onClick={() => setAiExpanded(!aiExpanded)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[var(--gold)]" />
                <span className="text-sm font-medium text-white">
                  AI-Assisted Setup
                </span>
              </div>
              {aiExpanded ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </div>
          </CardHeader>
          {aiExpanded && (
            <CardContent className="p-4 pt-2 space-y-3">
              <p className="text-sm text-muted-foreground">
                Paste a meeting description and let AI create the agenda for
                you.
              </p>
              <textarea
                className="w-full resize-none rounded-md border border-gray-700 bg-[#0d1117] px-3 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30 disabled:opacity-50"
                rows={5}
                placeholder='e.g. "Q2 Board Meeting on April 15 at 10am in the Main Boardroom. Agenda: 1. Call to Order, 2. Financial Review - discuss Q1 results, 3. Vote on new office lease..."'
                value={aiDescription}
                onChange={(e) => setAiDescription(e.target.value)}
                disabled={isAgentStreaming}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-[var(--gold)]/20 text-[var(--gold)] hover:bg-[var(--gold)]/30 border border-[var(--gold)]/30"
                  onClick={handleParseWithAI}
                  disabled={isAgentStreaming || !aiDescription.trim()}
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                  Parse with AI
                </Button>
                {isAgentStreaming && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-gray-700 text-gray-400 hover:text-white"
                    onClick={cancelAgent}
                  >
                    Cancel
                  </Button>
                )}
                {(isAgentDone || isAgentError) && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-gray-700 text-gray-400 hover:text-white"
                    onClick={resetAgent}
                  >
                    Clear
                  </Button>
                )}
              </div>

              {/* Agent output */}
              {hasAgentOutput && (
                <div className="max-h-80 overflow-y-auto rounded-md border border-gray-800 bg-[#0d1117] p-3 space-y-3">
                  {isAgentStreaming && !agentText && toolCalls.length === 0 && (
                    <div className="flex items-center gap-2 text-gray-400 text-sm">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Thinking...
                    </div>
                  )}

                  {agentText && (
                    <div className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-white prose-strong:text-white prose-li:text-gray-300 prose-code:text-[var(--gold)] prose-code:bg-gray-800 prose-code:rounded prose-code:px-1">
                      <ReactMarkdown>{agentText}</ReactMarkdown>
                    </div>
                  )}

                  {toolCalls.length > 0 && (
                    <div className="space-y-2">
                      {toolCalls.map((tc) => (
                        <ToolCallIndicator key={tc.id} toolCall={tc} />
                      ))}
                    </div>
                  )}

                  {isAgentError && agentError && (
                    <div className="rounded-md border border-red-800/50 bg-red-900/20 px-3 py-2 text-sm text-red-400">
                      {agentError}
                    </div>
                  )}

                  {isAgentDone && agentUsage && (
                    <div className="text-xs text-gray-500 pt-1">
                      {agentUsage.model.split("/").pop()} |{" "}
                      {agentUsage.prompt_tokens + agentUsage.completion_tokens}{" "}
                      tokens
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          )}
        </Card>

        {/* Template Selector */}
        <div>
          <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Or start from a template
          </label>
          <select
            value={selectedTemplateId}
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            className="w-full mt-2 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
          >
            <option value="">Select a template...</option>
            {templates.map((tpl) => (
              <option key={tpl.id} value={String(tpl.id)}>
                {tpl.name}
                {tpl.has_regulatory_items ? " (includes regulatory items)" : ""}
              </option>
            ))}
          </select>
          {loadingTemplate && (
            <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading template...
            </div>
          )}
          {selectedTemplate?.description && (
            <p className="text-sm text-muted-foreground mt-2">
              {selectedTemplate.description}
            </p>
          )}
        </div>

        {/* Manual Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="border-gray-800">
            <CardHeader className="p-4 pb-2">
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] flex items-center gap-3">
                <span>Meeting Details</span>
                <div className="flex-1 h-px bg-border" />
              </span>
            </CardHeader>
            <CardContent className="p-4 pt-2 space-y-4">
              {/* Title */}
              <div>
                <label className="text-sm font-medium">Title *</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Q2 Board Meeting"
                  className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                  disabled={submitting}
                />
              </div>

              {/* Date and Duration */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Date & Time *</label>
                  <input
                    type="datetime-local"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                    disabled={submitting}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Duration (min)</label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    min="15"
                    step="15"
                    placeholder="60"
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                    disabled={submitting}
                  />
                </div>
              </div>

              {/* Location and Meeting Link */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Location</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Conference Room A"
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                    disabled={submitting}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Meeting Link</label>
                  <input
                    type="url"
                    value={meetingLink}
                    onChange={(e) => setMeetingLink(e.target.value)}
                    placeholder="https://zoom.us/j/..."
                    className="w-full mt-1 h-10 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30"
                    disabled={submitting}
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-sm font-medium">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional meeting description"
                  rows={3}
                  className="w-full mt-1 px-3 py-2 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 focus:border-[var(--gold)]/30 resize-none"
                  disabled={submitting}
                />
              </div>
            </CardContent>
          </Card>

          {/* Agenda Items */}
          <Card className="border-gray-800">
            <CardHeader className="p-4 pb-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] flex items-center gap-3">
                  <span>Agenda Items</span>
                  <div className="flex-1 h-px bg-border" />
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="border-gray-700 text-gray-300 hover:text-white"
                  onClick={() => setShowAddItem(true)}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add Item
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-2 space-y-2">
              {agendaItems.length === 0 && !showAddItem && (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No agenda items yet. Add items manually or select a template
                  above.
                </p>
              )}

              {agendaItems.map((item, index) => (
                <div
                  key={item.id}
                  className={`rounded-md border p-3 ${
                    item.is_regulatory
                      ? "border-l-2 border-l-amber-500/70 border-gray-700 bg-amber-500/5"
                      : "border-gray-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-white">
                          {index + 1}. {item.title}
                        </span>
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono rounded border ${itemTypeBadgeColor(
                            item.item_type
                          )}`}
                        >
                          {itemTypeLabel(item.item_type)}
                        </span>
                        {item.is_regulatory && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            <Shield className="h-3 w-3" />
                            Regulatory
                          </span>
                        )}
                        {item.duration_minutes > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {item.duration_minutes} min
                          </span>
                        )}
                      </div>
                      {item.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {item.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => moveItem(index, "up")}
                        disabled={index === 0}
                        className="p-1 text-gray-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                        aria-label="Move up"
                      >
                        <ChevronUp className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => moveItem(index, "down")}
                        disabled={index === agendaItems.length - 1}
                        className="p-1 text-gray-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                        aria-label="Move down"
                      >
                        <ChevronDown className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeAgendaItem(item.id)}
                        className="p-1 text-gray-500 hover:text-red-400"
                        aria-label="Remove item"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Regulatory removal warning */}
                  {removingItemId === item.id && item.is_regulatory && (
                    <div className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-2">
                      <p className="text-xs text-amber-400 mb-2">
                        This is a required regulatory item. Are you sure you
                        want to remove it?
                      </p>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
                          onClick={() => {
                            setAgendaItems((prev) =>
                              prev.filter((i) => i.id !== item.id)
                            );
                            setRemovingItemId(null);
                          }}
                        >
                          Yes, remove
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs border-gray-700 text-gray-400 hover:text-white"
                          onClick={() => setRemovingItemId(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Add item inline form */}
              {showAddItem && (
                <div className="rounded-md border border-gray-700 border-dashed p-3 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <label className="text-xs font-medium text-gray-400">
                        Title
                      </label>
                      <input
                        type="text"
                        value={newItemTitle}
                        onChange={(e) => setNewItemTitle(e.target.value)}
                        placeholder="Agenda item title"
                        className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                        autoFocus
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-400">
                        Type
                      </label>
                      <select
                        value={newItemType}
                        onChange={(e) => setNewItemType(e.target.value)}
                        className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                      >
                        {ITEM_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-400">
                        Duration (min)
                      </label>
                      <input
                        type="number"
                        value={newItemDuration}
                        onChange={(e) => setNewItemDuration(e.target.value)}
                        min="1"
                        placeholder="10"
                        className="w-full mt-1 h-9 px-3 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="text-xs font-medium text-gray-400">
                        Description (optional)
                      </label>
                      <textarea
                        value={newItemDescription}
                        onChange={(e) => setNewItemDescription(e.target.value)}
                        placeholder="Optional description"
                        rows={2}
                        className="w-full mt-1 px-3 py-2 rounded-md border border-gray-700 bg-[#0d1117] text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-[var(--gold)]/50 resize-none"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      onClick={addAgendaItem}
                      disabled={!newItemTitle.trim()}
                    >
                      <Plus className="h-3.5 w-3.5 mr-1" />
                      Add
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="border-gray-700 text-gray-400 hover:text-white"
                      onClick={() => {
                        setShowAddItem(false);
                        setNewItemTitle("");
                        setNewItemDescription("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Submit */}
          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/meetings")}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !title.trim() || !date}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Meeting"
              )}
            </Button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
