# Phase 05: Admin Agent Management - Research

**Researched:** 2026-03-04 (updated 2026-03-04)
**Domain:** Admin CRUD UI for agent configurations, tool assignment, prompt editing, and usage statistics
**Confidence:** HIGH

## Summary

Phase 05 builds the admin-facing management interface for the AI agents created in Phase 01. The core challenge is not technical novelty -- it is a standard CRUD admin interface -- but rather maintaining consistency with the existing admin section patterns (Users page, Settings page) and providing good UX for the three distinct editing concerns: agent configuration (name, model, description), system prompt editing (multi-line text with potential for long prompts), and tool assignment (selecting from a registry of available tools).

The existing codebase provides strong, verified patterns to follow. The admin Users page (`frontend/src/app/admin/users/page.tsx`, 541 lines) demonstrates the established layout: `AppShell` wrapper, gold-accent section header, stats cards row, Button-based tab switching, table rows with actions, and Card-based modal editing. The backend admin API (`backend/app/api/admin.py`, 565 lines) shows the standard pattern: Pydantic schemas for request/response, `require_admin` dependency for auth, `AuditLog` entries for all mutations, and SQLAlchemy ORM queries. Phase 05 replicates these patterns for agent management.

The data model (`AgentConfig`, `AgentUsageLog`) was created in Phase 01 and is fully operational. The tool registry (`backend/app/tools/__init__.py`) uses `ToolDefinition` dataclasses with a `get_tool_definitions()` helper that returns OpenAI-format dicts. Three seed agents (Meeting Setup, Minutes Generator, Resolution Writer) exist with real system prompts and tool assignments. This phase adds the admin UI and API endpoints for managing those existing models.

**Primary recommendation:** Build the agent admin page at `frontend/src/app/admin/agents/page.tsx` following the exact same patterns as the Users page. Use Button-based tab switching (Agents | Usage) with a table-based agent list, Card-based modal create/edit forms, a checkbox-based tool assignment UI, and a simple aggregated usage stats table. Add the backend admin endpoints in a new `backend/app/api/agent_admin.py` file following the existing `admin.py` patterns. Register the router in `main.py` under `/api/admin` prefix.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMIN-01 | Admin can create, edit, and delete agent configurations (under Admin section) | Standard CRUD following existing admin patterns. Backend `agent_admin.py` with Pydantic schemas, `require_admin` auth. Frontend Card-based modal create/edit with confirm dialog for delete (soft-delete via `is_active=False`). Sidebar nav item added with Bot icon. |
| ADMIN-02 | Admin can assign/remove tools from an agent's allowed tool list | Checkbox list UI in agent edit modal. Tools loaded from backend endpoint that reads `TOOL_REGISTRY` via `ToolDefinition` dataclass (name, description, category). Agent's `allowed_tool_names` JSON column stores selected tool names. |
| ADMIN-03 | Admin can edit an agent's system prompt and select its model | System prompt: large `<textarea>` (monospace, ~20 rows). Model selection: `<select>` dropdown populated from a hardcoded list of supported LiteLLM model identifiers matching the 3 configured providers (Anthropic, Gemini, Groq). Both fields on the agent edit form. |
| ADMIN-04 | Admin can view agent usage statistics (calls, tokens, cost) | SQL aggregation queries on `agent_usage_logs` table (SUM/COUNT/AVG grouped by agent_id). Per-agent breakdown with totals. Optional date range filter. Simple table layout -- no charting library needed. |
</phase_requirements>

## Standard Stack

### Core (already in project -- verified)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.4 | Frontend framework | Already in project, admin pages are Next.js pages |
| React | 19.x | UI components | Already in project |
| shadcn/ui (Card, Button) | N/A | UI primitives | Already used in admin pages -- Card, CardContent, CardHeader, CardTitle, Button |
| lucide-react | 0.563.0 | Icons | Already used throughout admin pages |
| FastAPI | >=0.135.0 | Backend API | Already in project, hosts admin endpoints |
| SQLAlchemy 2.0 | >=2.0.25 | ORM for agent config CRUD | Already in project, used by all models |
| Pydantic | >=2.5 | Request/response schemas | Already in project, used for all API schemas |

### Supporting (already in project -- verified)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-select | 2.2.6 | Select dropdowns | Already installed, use for model selection dropdown |
| httpx | N/A | Async HTTP client for tests | Already in project, used by test client via `ASGITransport` |
| pytest | N/A | Test framework | Already in project, existing test suite with `conftest.py` |

### No New Dependencies Needed
Phase 05 requires zero new dependencies. Everything is built with existing libraries. Key observations:
- The project uses Button-based tab switching (not Radix Tabs component) -- verified in `admin/users/page.tsx`
- Card-based modals are the established pattern (fixed z-50 overlay + backdrop blur) -- verified in `edit-user-modal.tsx`
- No charting library needed -- usage stats displayed as tables and stat cards
- No code editor library needed -- system prompt editing uses a plain `<textarea>` with monospace font

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain textarea for prompt editing | Monaco Editor / CodeMirror | Over-engineering. System prompts are plain text, not code. Textarea is sufficient. Would add ~500KB bundle. |
| Table for usage stats | Recharts / Chart.js | Over-engineering for v1. A well-formatted table with stat cards is clearer for admin use. Charts can be added later if needed. |
| Hardcoded model list | LiteLLM model discovery | The org only supports 3 providers. A hardcoded list is clearer and safer than auto-discovery. |

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/app/
├── api/
│   └── agent_admin.py         # NEW: Admin CRUD endpoints for agent configs + usage stats
└── (models/agent.py)          # EXISTS: AgentConfig, AgentUsageLog (from Phase 01)

backend/tests/
└── test_agent_admin.py        # NEW: Tests for agent admin endpoints

frontend/src/
├── app/
│   └── admin/
│       └── agents/
│           └── page.tsx       # NEW: Agent management admin page
├── components/
│   ├── create-agent-modal.tsx # NEW: Modal for creating new agent
│   └── edit-agent-modal.tsx   # NEW: Modal for editing agent (prompt, model, tools)
└── lib/
    └── api.ts                 # MODIFIED: Add agent admin API methods to adminApi object
```

### Pattern 1: Admin Page Layout (follow existing Users page exactly)
**What:** Every admin page follows: AppShell > Section header with gold accent > Stats cards > Button-based tab switching > Table in Card.
**When to use:** The agents admin page.
**Verified source:** `frontend/src/app/admin/users/page.tsx` lines 182-541
**Example:**
```typescript
// Source: Derived from frontend/src/app/admin/users/page.tsx pattern
export default function AdminAgentsPage() {
  const [activeTab, setActiveTab] = useState<"agents" | "usage">("agents");

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header - matches Users page pattern */}
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

        {/* Stats cards - same grid pattern as Users page */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Total Agents, Active Agents, Total Calls, Total Cost */}
        </div>

        {/* Tabs - Button-based switching (same as Users page) */}
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

        {/* Tables with same styling as Users page */}
      </div>
    </AppShell>
  );
}
```

### Pattern 2: Backend Admin CRUD (follow existing admin.py exactly)
**What:** All admin endpoints use `require_admin` dependency, return Pydantic response models, log changes to `AuditLog`.
**When to use:** All agent admin API endpoints.
**Verified source:** `backend/app/api/admin.py` lines 115-249 (user CRUD pattern)
**Key details:**
- `AuditLog` uses `entity_type="agent"`, `entity_name=agent.name`, `action="create"|"update"|"delete"`, `changes={"field": {"old": x, "new": y}}`
- Soft delete sets `is_active = False` (matching AgentConfig's existing field)
- PATCH for updates (partial update), POST for create, DELETE for soft-delete
- Return `{"status": "updated|deactivated", "id": N}` for mutations
```python
# Source: Follows patterns from backend/app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models.member import BoardMember
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.audit import AuditLog
from app.api.auth import require_admin

router = APIRouter()

@router.get("/agents")
async def list_agents(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    query = db.query(AgentConfig)
    if not include_inactive:
        query = query.filter(AgentConfig.is_active == True)
    return query.order_by(AgentConfig.name).all()

@router.post("/agents")
async def create_agent(
    request: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    # Auto-generate slug from name
    slug = request.name.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    agent = AgentConfig(
        name=request.name,
        slug=slug,
        description=request.description,
        system_prompt=request.system_prompt,
        model=request.model,
        temperature=request.temperature,
        max_iterations=request.max_iterations,
        allowed_tool_names=request.allowed_tool_names or [],
        is_active=True,
    )
    db.add(agent)
    db.add(AuditLog(
        entity_type="agent",
        entity_id=0,  # Will update after commit
        entity_name=request.name,
        action="create",
        changed_by_id=current_user.id,
    ))
    db.commit()
    db.refresh(agent)
    return agent
```

### Pattern 3: Card-Based Modal (follow existing edit-user-modal.tsx exactly)
**What:** Edit forms render in Card-based modals with fixed z-50 overlay, backdrop blur, close on backdrop click, loading state during submission.
**When to use:** Agent create and edit modals.
**Verified source:** `frontend/src/components/edit-user-modal.tsx` lines 75-192
**Key structural elements:**
```typescript
// Source: Exact pattern from frontend/src/components/edit-user-modal.tsx
return (
  <div className="fixed inset-0 z-50 flex items-center justify-center">
    {/* Backdrop */}
    <div
      className="absolute inset-0 bg-background/80 backdrop-blur-sm"
      onClick={handleClose}
    />
    {/* Modal */}
    <Card className="relative z-10 w-full max-w-md mx-4 shadow-lg">
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
          {/* Form fields */}
          {/* Actions row at bottom */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={handleClose} disabled={submitting}>Cancel</Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving...</> : "Save Changes"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
);
```

### Pattern 4: Tool Assignment via Checkbox List
**What:** The tool registry provides a list of available tools via `ToolDefinition` dataclass (name, description, category). The admin checks/unchecks tools to assign them to an agent. The `allowed_tool_names` JSON column stores the selection.
**When to use:** Inside the agent create/edit modal.
**Key detail:** The `ToolDefinition` dataclass in `backend/app/tools/__init__.py` has fields: `name`, `description`, `parameters_schema`, `handler`, `category`. The admin endpoint should expose `name`, `description`, and `category` (not handler or schema).

### Pattern 5: Sidebar Navigation Item
**What:** Add "Agents" to the Admin nav group in the sidebar, between "Templates" and "Settings".
**Verified source:** `frontend/src/components/sidebar.tsx` lines 49-57
**Example:**
```typescript
// In frontend/src/components/sidebar.tsx
// Import Bot icon from lucide-react (add to existing import)
import { Bot } from "lucide-react";

// Modify the Admin group items array (line 52-56):
{
  label: "Admin",
  visibleTo: "admin",
  items: [
    { label: "Users", href: "/admin/users", icon: Users },
    { label: "Templates", href: "/admin/templates", icon: ClipboardList },
    { label: "Agents", href: "/admin/agents", icon: Bot },  // NEW
    { label: "Settings", href: "/admin/settings", icon: Settings },
  ],
}
```

### Pattern 6: Router Registration in main.py
**What:** New routers are imported and registered in `backend/app/main.py` with `app.include_router()`.
**Verified source:** `backend/app/main.py` lines 7, 428-438
**Key detail:** The existing admin router is at `/api/admin`. The agent admin router should be registered separately with its own prefix to avoid route collisions. Use `/api/admin` prefix with route paths like `/agents`, `/agents/{id}`, `/agents/tools`, `/agents/usage`.
**Important:** Since the existing `admin.router` is already at `/api/admin`, there could be route collisions. Options:
  1. Add agent admin routes directly to the existing `admin.py` router (simplest, follows single-router-per-prefix pattern)
  2. Create `agent_admin.py` with its own router and mount at `/api/admin` (two routers sharing a prefix -- FastAPI supports this)

**Recommendation:** Option 2 -- separate file for clean separation of concerns. FastAPI allows multiple routers on the same prefix. Import in `main.py` as `from app.api import agent_admin` and register with `app.include_router(agent_admin.router, prefix="/api/admin", tags=["admin-agents"])`.

### Anti-Patterns to Avoid
- **Separate page for each agent function (list, edit, tools, usage):** Use a single page with tabs and modals. The existing admin section uses this pattern and admin pages should not proliferate.
- **Complex WYSIWYG editor for system prompts:** System prompts are plain text instructions. A monospace textarea is the correct tool. Rich text editors add complexity and corrupt prompt formatting.
- **Real-time usage charts with polling:** Overkill for v1. Usage stats are consulted occasionally, not monitored live. A simple aggregated table with a date range filter is sufficient.
- **Inline editing on the table:** The existing pattern is click-to-edit-modal. Inline editing introduces complex state management for marginal UX gain.
- **Using Radix Dialog for modals:** The project uses custom Card-based modals (verified in `edit-user-modal.tsx`), NOT Radix Dialog. Follow the existing pattern.
- **Using Radix Tabs for tab switching:** The Users page uses Button-based tabs with `variant` toggling, NOT the Radix Tabs component. Follow the existing pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model selection dropdown options | Dynamic model discovery from LiteLLM | Hardcoded list of supported models | The org only supports 3 providers (Anthropic/Gemini/Groq). A hardcoded list with friendly names is clearer and safer than auto-discovery, which could expose unsupported models. Update the list when new models are added. |
| Usage cost aggregation | Custom cost calculation logic | SQL aggregation on `agent_usage_logs.total_cost_usd` | The agent runner already calculates per-call cost at invocation time (Phase 01). Admin just needs SUM/COUNT queries. |
| Slug generation | Manual slug input from admin | Auto-generate from name (lowercase, replace spaces with hyphens, strip special chars) | Slugs should be deterministic from names. Let the backend auto-generate. Validate uniqueness. |
| Tool list for assignment UI | Hardcoded tool list in frontend | Backend endpoint that reads `TOOL_REGISTRY` | Tools are defined as `ToolDefinition` dataclasses in `backend/app/tools/`. The existing `get_tool_definitions()` function provides all registered tools. A backend endpoint should expose name + description + category for the frontend. |
| Tool definition display format | Custom parsing of tool schemas | Read `ToolDefinition.name`, `.description`, `.category` directly | The `ToolDefinition` dataclass already has clean fields. Don't parse the OpenAI-format dict -- read the dataclass attributes directly. |

**Key insight:** Phase 05 is purely a management interface over models and data created in Phase 01. It should not contain any AI logic, tool execution, or streaming code. It is CRUD + aggregation queries + UI.

## Common Pitfalls

### Pitfall 1: Editing System Prompt Loses Formatting
**What goes wrong:** Admin edits a multi-line system prompt in a textarea, but whitespace/newlines are stripped or mangled during save or display.
**Why it happens:** JSON serialization, HTML rendering, or Pydantic validation strips whitespace.
**How to avoid:** The `system_prompt` column is already `Text` type (verified in `agent.py` line 19). Send as raw string in JSON body. Render in a `<textarea>` with `whitespace-pre-wrap` for display. Test with the existing seed agent prompts which contain bullet points, backslash continuations, and multiple paragraphs.
**Warning signs:** Prompts that looked fine in the editor break when the agent uses them.

### Pitfall 2: Deleting an Agent That Is Being Used
**What goes wrong:** Admin deletes an agent while a user is mid-invocation, causing a runtime error.
**Why it happens:** No soft-delete or usage check.
**How to avoid:** Use soft delete (`is_active = False`) instead of hard delete. The `AgentConfig.is_active` field already exists (verified). The agent list endpoint already filters `is_active == True` (verified in `agents.py` line 39). The run endpoint already checks `is_active` (verified in `agents.py` line 88). So soft-deleting an agent will immediately prevent new invocations and hide it from user-facing lists. Show a confirmation dialog in the UI. If the agent has usage logs, warn the admin that stats will be preserved.
**Warning signs:** 404 errors during agent invocations. Loss of usage statistics.

### Pitfall 3: Tool Registry Out of Sync with Agent Config
**What goes wrong:** An agent's `allowed_tool_names` references a tool name that no longer exists in the tool registry (e.g., after a tool is renamed or removed in code).
**Why it happens:** Tool definitions live in code (`backend/app/tools/`), but agent configs live in the database.
**How to avoid:** The `get_tools_for_agent()` function in `tools/__init__.py` already silently ignores unknown tool names (verified, line 41: `if tool:`). In the admin UI, show a warning badge next to tool names that are in the agent's config but not in the current registry. The backend tools endpoint provides the current registry for comparison.
**Warning signs:** Agent silently loses access to tools after a code deploy.

### Pitfall 4: No Audit Trail for Agent Config Changes
**What goes wrong:** Admin changes a system prompt that causes an agent to misbehave, but there's no record of what the prompt was before.
**Why it happens:** Not logging changes to `AuditLog`.
**How to avoid:** Log every create/update/delete to `AuditLog` with `entity_type="agent"`. For updates, include changed fields in the `changes` JSON column (especially `system_prompt` old/new values). This follows the exact pattern used for user updates in `admin.py` (verified, lines 194-213).
**Warning signs:** Cannot determine when or why an agent's behavior changed.

### Pitfall 5: Model Identifier Validation
**What goes wrong:** Admin enters an invalid model identifier and the agent fails at runtime with a LiteLLM error.
**Why it happens:** Free-text model input without validation.
**How to avoid:** Use a `<select>` dropdown with a curated list of supported models, not a free-text input. The `llm_provider.py` supports three providers: anthropic, gemini, groq (verified via `PROVIDER_KEY_MAP`). The model identifiers must use LiteLLM format: `provider/model-name`. The existing seed agents use `anthropic/claude-sonnet-4-5-20250929` (verified in `main.py` line 137).
**Warning signs:** LiteLLM errors about unknown model identifiers.

### Pitfall 6: Route Collision with Existing Agent API
**What goes wrong:** The new admin agent endpoints conflict with the existing `/api/agents` routes (which are user-facing).
**Why it happens:** Both the agent runner API and admin agent API deal with agent configs.
**How to avoid:** Mount admin endpoints under `/api/admin/agents` (via the admin prefix), NOT under `/api/agents`. The existing agent API at `/api/agents` is for user-facing operations (list active agents, run agent). The admin API at `/api/admin/agents` is for configuration management (CRUD, tools, usage). Completely separate concerns.
**Warning signs:** Non-admin users accessing admin-only endpoints, or admin routes shadowing user routes.

## Code Examples

### Backend: Tool Info Endpoint (reads ToolDefinition dataclass)
```python
# Source: backend/app/tools/__init__.py ToolDefinition dataclass
# The TOOL_REGISTRY contains ToolDefinition instances, NOT raw dicts.
# ToolDefinition has: name, description, parameters_schema, handler, category

@router.get("/agents/tools")
async def list_available_tools(
    current_user: BoardMember = Depends(require_admin),
):
    """Return all registered tools from the tool registry."""
    from app.tools import TOOL_REGISTRY
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameter_count": len(tool.parameters_schema.get("properties", {})),
        }
        for tool in TOOL_REGISTRY.values()
    ]
```

### Backend: Usage Stats Aggregation
```python
# Source: Follows patterns from backend/app/api/admin.py
from sqlalchemy import func

@router.get("/agents/usage")
async def get_usage_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Aggregate usage stats per agent."""
    query = db.query(
        AgentUsageLog.agent_id,
        AgentConfig.name.label("agent_name"),
        func.count(AgentUsageLog.id).label("total_calls"),
        func.sum(AgentUsageLog.prompt_tokens).label("total_prompt_tokens"),
        func.sum(AgentUsageLog.completion_tokens).label("total_completion_tokens"),
        func.sum(AgentUsageLog.total_cost_usd).label("total_cost_usd"),
        func.avg(AgentUsageLog.duration_ms).label("avg_duration_ms"),
    ).join(AgentConfig).group_by(AgentUsageLog.agent_id, AgentConfig.name)

    if start_date:
        query = query.filter(AgentUsageLog.created_at >= start_date)
    if end_date:
        query = query.filter(AgentUsageLog.created_at <= end_date)

    return query.all()
```

### Backend: Pydantic Schemas
```python
# Agent admin request/response schemas
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model: str  # e.g., "anthropic/claude-sonnet-4-5-20250929"
    max_iterations: int = 5
    temperature: float = 0.3
    allowed_tool_names: List[str] = []

class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    allowed_tool_names: Optional[List[str]] = None
    is_active: Optional[bool] = None

class AgentAdminResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    system_prompt: str
    model: str
    max_iterations: int
    temperature: float
    allowed_tool_names: list
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Frontend: Agent Admin API Client Methods
```typescript
// Source: Follows patterns from frontend/src/lib/api.ts adminApi section (lines 1209-1421)

// Types (add near other admin types)
export interface AgentConfig {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  system_prompt: string;
  model: string;
  max_iterations: number;
  temperature: number;
  allowed_tool_names: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
  parameter_count: number;
}

export interface AgentUsageStats {
  agent_id: number;
  agent_name: string;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  avg_duration_ms: number;
}

// Add to adminApi object in api.ts:
// Agent Management
listAgents: async (includeInactive = false): Promise<AgentConfig[]> => {
  const query = includeInactive ? "?include_inactive=true" : "";
  const response = await api.get<AgentConfig[] | PaginatedResponse<AgentConfig>>(`/admin/agents${query}`);
  return Array.isArray(response) ? response : response.items || [];
},

createAgent: async (data: Partial<AgentConfig>): Promise<AgentConfig> => {
  return api.post("/admin/agents", data);
},

updateAgent: async (id: number, data: Partial<AgentConfig>): Promise<AgentConfig> => {
  return api.patch(`/admin/agents/${id}`, data);
},

deleteAgent: async (id: number): Promise<void> => {
  return api.delete(`/admin/agents/${id}`);
},

listAvailableTools: async (): Promise<ToolInfo[]> => {
  return api.get("/admin/agents/tools");
},

getAgentUsageStats: async (params?: {
  start_date?: string;
  end_date?: string;
}): Promise<AgentUsageStats[]> => {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);
  const query = searchParams.toString();
  return api.get(`/admin/agents/usage${query ? `?${query}` : ""}`);
},
```

### Frontend: Supported Models List
```typescript
// Hardcoded list of supported models for the model selection dropdown
// Based on verified PROVIDER_KEY_MAP in backend/app/services/llm_provider.py
// and seed agent model values in backend/app/main.py
export const SUPPORTED_MODELS = [
  {
    value: "anthropic/claude-sonnet-4-5-20250929",
    label: "Claude Sonnet 4.5",
    provider: "Anthropic",
  },
  {
    value: "anthropic/claude-haiku-3-5-20241022",
    label: "Claude Haiku 3.5",
    provider: "Anthropic",
  },
  {
    value: "gemini/gemini-2.0-flash",
    label: "Gemini 2.0 Flash",
    provider: "Google",
  },
  {
    value: "gemini/gemini-2.0-flash-lite",
    label: "Gemini 2.0 Flash Lite",
    provider: "Google",
  },
  {
    value: "groq/llama-3.3-70b-versatile",
    label: "Llama 3.3 70B",
    provider: "Groq",
  },
  {
    value: "groq/llama-3.1-8b-instant",
    label: "Llama 3.1 8B (Fast)",
    provider: "Groq",
  },
];
```

### Frontend: Tool Assignment Checkbox Section
```typescript
// Tool assignment section within the create/edit modal
<div>
  <label className="text-sm font-medium">Allowed Tools</label>
  <p className="text-xs text-muted-foreground mt-0.5">
    Select which tools this agent can use
  </p>
  <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
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
        />
        <div>
          <p className="text-sm font-medium">{tool.name}</p>
          <p className="text-xs text-muted-foreground">{tool.description}</p>
        </div>
      </label>
    ))}
  </div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Config files for agent setup | Database-backed admin UI | Industry pattern 2024-2025 | Non-technical admins can manage agents without code deploys |
| Code editor widgets for prompts | Plain textarea | Simplified by narrow-agent pattern | System prompts are natural language, not code. Textarea with monospace is standard. |
| Complex permission-gated tool access | Simple checkbox assignment | Appropriate for 3-5 built-in agents | When tool count is small, a checkbox list is clearer than ACL-based tool permissions |

**Deprecated/outdated:**
- JSON file-based prompt configuration: Replaced by database-backed management with admin UI
- Hardcoded agent definitions in code: Already replaced by `agent_configs` table with runtime editability (Phase 01)

## Open Questions

1. **Should the admin see a "Test Agent" button?**
   - What we know: Admins may want to test a prompt change before it affects users. Phase 01 builds the agent runner.
   - What's unclear: Should Phase 05 include a "test run" feature in the admin UI, or is that deferred?
   - Recommendation: Defer to v2.1. For v2.0, admins can test by using the agent from a board page after saving. Adding a test UI in admin increases scope significantly (needs SSE rendering, tool execution context, etc.).

2. **Prompt versioning/history**
   - What we know: The `AuditLog` captures old/new values for prompt changes. This provides basic version tracking.
   - What's unclear: Should there be a dedicated "prompt history" view with rollback capability?
   - Recommendation: Rely on `AuditLog` for v2.0. The changes JSON captures before/after. A dedicated versioning UI can be added later if admins need it frequently.

3. **Usage stats date granularity**
   - What we know: `agent_usage_logs` has `created_at` timestamps for each call.
   - What's unclear: Should usage stats show daily/weekly/monthly breakdowns, or just a total with date range filter?
   - Recommendation: Start with total aggregation + optional date range filter. This is simplest and covers the ADMIN-04 requirement. Time-series breakdowns can be added later.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), Next.js build (frontend type checking) |
| Config file | `backend/tests/conftest.py` (exists, verified) |
| Quick run command | `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest tests/test_agent_admin.py -x` |
| Full suite command | `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest --tb=short -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | CRUD for agent configs (create, read, update, soft-delete) | unit | `pytest tests/test_agent_admin.py::test_create_agent -x` | Wave 0 |
| ADMIN-01 | Only admin role can access agent admin endpoints | unit | `pytest tests/test_agent_admin.py::test_require_admin -x` | Wave 0 |
| ADMIN-01 | AuditLog entry created for each agent mutation | unit | `pytest tests/test_agent_admin.py::test_audit_log -x` | Wave 0 |
| ADMIN-02 | Tool list endpoint returns registered tools from TOOL_REGISTRY | unit | `pytest tests/test_agent_admin.py::test_list_tools -x` | Wave 0 |
| ADMIN-02 | Agent update with allowed_tool_names persists correctly | unit | `pytest tests/test_agent_admin.py::test_update_tools -x` | Wave 0 |
| ADMIN-03 | Agent update with system_prompt and model persists correctly | unit | `pytest tests/test_agent_admin.py::test_update_prompt_model -x` | Wave 0 |
| ADMIN-03 | Model must be from supported list (or at least valid format) | unit | `pytest tests/test_agent_admin.py::test_model_validation -x` | Wave 0 |
| ADMIN-04 | Usage stats aggregation returns correct totals | unit | `pytest tests/test_agent_admin.py::test_usage_stats -x` | Wave 0 |
| ADMIN-04 | Usage stats date range filter works | unit | `pytest tests/test_agent_admin.py::test_usage_stats_date_filter -x` | Wave 0 |
| ALL | Frontend admin page builds without type errors | build | `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/frontend && npx next build` | N/A |

### Sampling Rate
- **Per task commit:** `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest tests/test_agent_admin.py -x`
- **Per wave merge:** `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest --tb=short -q`
- **Phase gate:** Full backend suite + frontend build green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_agent_admin.py` -- covers ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04
- [x] `backend/tests/conftest.py` -- shared fixtures exist (test DB, admin user `seed_user`, agent `seed_agent`, mock litellm)

### Existing Test Infrastructure (verified)
The following fixtures from `conftest.py` are directly reusable:
- `db_engine` -- in-memory SQLite engine
- `db_session` -- SQLAlchemy session bound to test engine
- `client` -- httpx AsyncClient with FastAPI test transport
- `seed_agent` -- creates a test AgentConfig
- `seed_user` -- creates a test BoardMember with role="admin"

**Additional fixture needed for Phase 05:**
- `seed_usage_logs` -- creates sample AgentUsageLog entries for testing usage stats aggregation

## Files to Create

### Backend (new files)
| File | Purpose |
|------|---------|
| `backend/app/api/agent_admin.py` | Admin CRUD endpoints for agent configs, tool list endpoint, usage stats endpoint |
| `backend/tests/test_agent_admin.py` | Tests for all admin agent endpoints |

### Frontend (new files)
| File | Purpose |
|------|---------|
| `frontend/src/app/admin/agents/page.tsx` | Agent management admin page (list + usage tabs) |
| `frontend/src/components/create-agent-modal.tsx` | Modal for creating a new agent config |
| `frontend/src/components/edit-agent-modal.tsx` | Modal for editing agent (prompt, model, tools, settings) |

### Modified files
| File | Change |
|------|--------|
| `frontend/src/components/sidebar.tsx` | Add "Agents" nav item under Admin group with Bot icon |
| `frontend/src/lib/api.ts` | Add `AgentConfig`, `ToolInfo`, `AgentUsageStats` types and agent admin methods to `adminApi` object |
| `backend/app/main.py` | Import `agent_admin` and register router: `app.include_router(agent_admin.router, prefix="/api/admin", tags=["admin-agents"])` |

## Sources

### Primary (HIGH confidence)
- `backend/app/models/agent.py` -- AgentConfig and AgentUsageLog models (verified fields: id, name, slug, description, system_prompt, model, temperature, max_iterations, is_active, allowed_tool_names, created_at, updated_at)
- `backend/app/tools/__init__.py` -- ToolDefinition dataclass (name, description, parameters_schema, handler, category), TOOL_REGISTRY dict, get_tool_definitions() helper
- `backend/app/api/admin.py` (565 lines) -- Admin endpoint patterns: Pydantic schemas, require_admin auth, AuditLog entries, CRUD operations
- `backend/app/api/agents.py` (223 lines) -- Existing user-facing agent endpoints (list, detail, run, API key management)
- `frontend/src/app/admin/users/page.tsx` (541 lines) -- Admin page layout: AppShell, gold-accent header, stats cards, Button-based tabs, table in Card
- `frontend/src/components/edit-user-modal.tsx` (192 lines) -- Card-based modal pattern: fixed z-50 overlay, backdrop blur, form with loading state
- `frontend/src/components/sidebar.tsx` (193 lines) -- Nav structure with Admin group (Users, Templates, Settings)
- `frontend/src/lib/api.ts` (1421 lines) -- API client patterns, adminApi object structure
- `backend/app/main.py` (445 lines) -- Router registration pattern, seed agent data with real prompts
- `backend/app/api/auth.py` -- `require_admin` dependency (checks `user.role != "admin"`, returns 403)
- `backend/app/models/audit.py` -- AuditLog model (entity_type, entity_id, entity_name, action, changed_by_id, changes JSON)
- `backend/tests/conftest.py` -- Test infrastructure: in-memory SQLite, db_session, client, seed_agent, seed_user fixtures
- `backend/app/services/llm_provider.py` -- PROVIDER_KEY_MAP confirming 3 providers: anthropic, gemini, groq

### Secondary (MEDIUM confidence)
- `frontend/src/hooks/use-permissions.tsx` -- Permission/role checking hooks (isAdmin, isBoardOrAbove)
- `backend/tests/test_agent_api.py` -- Test patterns: async tests with pytest.mark.asyncio, header-based auth

### Tertiary (LOW confidence)
- LiteLLM model identifier formats -- model list may need updating as new models release. The seed agents currently use `anthropic/claude-sonnet-4-5-20250929` which is a real LiteLLM model identifier format.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already in project, no new dependencies, versions verified from package.json
- Architecture: HIGH -- Directly follows existing admin page and API patterns, code-verified against 8 source files
- Pitfalls: HIGH -- All identified pitfalls are standard CRUD concerns with known solutions, existing code already handles some (soft delete, tool filtering)
- UI/UX patterns: HIGH -- Derived directly from existing admin pages in the same codebase, specific line numbers verified
- Test infrastructure: HIGH -- conftest.py and 8 test files already exist with reusable fixtures

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days -- patterns are stable, model list may need updates)
