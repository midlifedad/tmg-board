# Phase 05: Admin Agent Management - Research

**Researched:** 2026-03-04
**Domain:** Admin CRUD UI for agent configurations, tool assignment, prompt editing, and usage statistics
**Confidence:** HIGH

## Summary

Phase 05 builds the admin-facing management interface for the AI agents created in Phase 01. The core challenge is not technical novelty -- it is a standard CRUD admin interface -- but rather maintaining consistency with the existing admin section patterns (Users page, Settings page) and providing good UX for the three distinct editing concerns: agent configuration (name, model, description), system prompt editing (multi-line text with potential for long prompts), and tool assignment (selecting from a registry of available tools).

The existing codebase provides strong patterns to follow. The admin Users page (`frontend/src/app/admin/users/page.tsx`) demonstrates the established layout: `AppShell` wrapper, gold-accent section header, stats cards row, tabbed content with tables, and modal-based editing. The backend admin API (`backend/app/api/admin.py`) shows the standard pattern: Pydantic schemas for request/response, `require_admin` dependency for auth, `AuditLog` entries for all mutations, and SQLAlchemy ORM queries. Phase 05 replicates these patterns for agent management.

The data model (`AgentConfig`, `AgentUsageLog`) was already designed in Phase 01 research and will be created as part of Phase 01 implementation. Phase 05 depends on Phase 01 being complete -- specifically the `agent_configs` and `agent_usage_logs` tables, the tool registry in `backend/app/tools/`, and the agent runner service. This phase adds the admin UI and API endpoints for managing those existing models.

**Primary recommendation:** Build the agent admin page at `frontend/src/app/admin/agents/page.tsx` following the exact same patterns as the Users page. Use a tabbed layout (Agents | Usage) with a table-based agent list, modal-based create/edit forms, a checkbox-based tool assignment UI, and a simple aggregated usage stats table. Add the backend admin endpoints in a new `backend/app/api/agent_admin.py` file following the existing `admin.py` patterns.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMIN-01 | Admin can create, edit, and delete agent configurations (under Admin section) | Standard CRUD following existing admin patterns. Backend `agent_admin.py` with Pydantic schemas, `require_admin` auth. Frontend modal-based create/edit with confirm dialog for delete. Sidebar nav item added. |
| ADMIN-02 | Admin can assign/remove tools from an agent's allowed tool list | Checkbox list UI in agent edit modal/page. Tools loaded from the tool registry (`backend/app/tools/`). Agent's `allowed_tool_names` JSON field stores selected tool names. |
| ADMIN-03 | Admin can edit an agent's system prompt and select its model | System prompt: large textarea (monospace, ~20 rows). Model selection: dropdown populated from a hardcoded list of supported LiteLLM model identifiers. Both fields on the agent edit form. |
| ADMIN-04 | Admin can view agent usage statistics (calls, tokens, cost) | Aggregation queries on `agent_usage_logs` table. Per-agent breakdown with totals. Date range filter. Simple table layout -- no charting library needed. |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.4 | Frontend framework | Already in project, admin pages are Next.js pages |
| React | 19.2.3 | UI components | Already in project |
| shadcn/ui (Card, Button) | N/A | UI primitives | Already used in admin pages -- Card, CardContent, CardHeader, CardTitle, Button |
| lucide-react | 0.563.0 | Icons | Already used throughout admin pages |
| FastAPI | >=0.135.0 | Backend API | Already in project, will host admin endpoints |
| SQLAlchemy 2.0 | >=2.0.25 | ORM for agent config CRUD | Already in project, used by all models |
| Pydantic | >=2.5 | Request/response schemas | Already in project, used for all API schemas |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-tabs | 1.1.13 | Tab component | Already installed, used for Agents/Usage tabs |
| @radix-ui/react-select | 2.2.6 | Select dropdowns | Already installed, use for model selection dropdown |
| @radix-ui/react-dialog | 1.1.15 | Modal dialogs | Already installed, but project uses custom modals (Card-based). Follow existing pattern. |
| Alembic | >=1.13.1 | Database migrations | Already in project. Phase 01 creates the agent tables; Phase 05 may not need new migrations. |

### No New Dependencies Needed
Phase 05 requires zero new dependencies. Everything is built with existing libraries. Key observations:
- The project already has `@radix-ui/react-tabs` and `@radix-ui/react-select` installed
- Custom Card-based modals are the established pattern (not Radix Dialog)
- No charting library needed -- usage stats are displayed as tables and stat cards
- No code editor library needed -- system prompt editing uses a plain `<textarea>` with monospace font

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain textarea for prompt editing | Monaco Editor / CodeMirror | Over-engineering. System prompts are plain text, not code. Textarea is sufficient. Would add ~500KB bundle. |
| Table for usage stats | Recharts / Chart.js | Over-engineering for v1. A well-formatted table with stat cards is clearer for admin use. Charts can be added later if needed. |
| Custom checkbox list for tools | Radix Checkbox component | Could work, but native HTML checkboxes with Tailwind styling match the existing patterns (see permissions table in settings page). |

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/app/
├── api/
│   └── agent_admin.py         # NEW: Admin CRUD endpoints for agent configs + usage stats
└── (models/agent.py)          # EXISTS from Phase 01: AgentConfig, AgentUsageLog

frontend/src/
├── app/
│   └── admin/
│       └── agents/
│           └── page.tsx       # NEW: Agent management admin page
├── components/
│   ├── create-agent-modal.tsx # NEW: Modal for creating new agent
│   └── edit-agent-modal.tsx   # NEW: Modal for editing agent (prompt, model, tools)
└── lib/
    └── api.ts                 # MODIFIED: Add agentAdminApi section
```

### Pattern 1: Admin Page Layout (follow existing Users page)
**What:** Every admin page follows: AppShell > Section header with gold accent > Stats cards > Tabbed content with tables.
**When to use:** The agents admin page.
**Example:**
```typescript
// Source: Derived from frontend/src/app/admin/users/page.tsx pattern
export default function AdminAgentsPage() {
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

        {/* Tabs: Agents | Usage */}
        {/* Tables with same styling as Users page */}
      </div>
    </AppShell>
  );
}
```

### Pattern 2: Backend Admin CRUD (follow existing admin.py)
**What:** All admin endpoints use `require_admin` dependency, return Pydantic response models, log changes to `AuditLog`.
**When to use:** All agent admin API endpoints.
**Example:**
```python
# Source: Derived from backend/app/api/admin.py patterns
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.member import BoardMember
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.audit import AuditLog
from app.api.auth import require_admin

router = APIRouter()

@router.get("/agents")
async def list_agents(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """List all agent configurations."""
    agents = db.query(AgentConfig).order_by(AgentConfig.name).all()
    return agents

@router.post("/agents")
async def create_agent(
    request: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Create a new agent configuration."""
    agent = AgentConfig(
        name=request.name,
        slug=request.slug,
        description=request.description,
        system_prompt=request.system_prompt,
        model=request.model,
        allowed_tool_names=request.allowed_tool_names or [],
        is_active=True,
    )
    db.add(agent)
    db.add(AuditLog(
        entity_type="agent",
        entity_id=0,
        entity_name=request.name,
        action="create",
        changed_by_id=current_user.id,
    ))
    db.commit()
    db.refresh(agent)
    return agent
```

### Pattern 3: Modal-Based Editing (follow existing edit-user-modal)
**What:** Edit forms render in Card-based modals with backdrop blur, close on backdrop click, show loading state during submission.
**When to use:** Agent create and edit modals.
**Example:**
```typescript
// Source: Derived from frontend/src/components/edit-user-modal.tsx pattern
interface EditAgentModalProps {
  isOpen: boolean;
  agent: AgentConfig | null;
  availableTools: ToolInfo[];
  onClose: () => void;
  onSuccess: () => void;
}

export function EditAgentModal({ isOpen, agent, availableTools, onClose, onSuccess }: EditAgentModalProps) {
  // Fixed z-50 overlay with backdrop blur
  // Card-based modal with CardHeader (title + close button) + CardContent (form)
  // Form fields: name, description, model (select), system prompt (textarea), tools (checkboxes)
  // Submit calls agentAdminApi.updateAgent(), onSuccess refetches list
}
```

### Pattern 4: Tool Assignment via Checkbox List
**What:** The tool registry provides a list of available tools with name and description. The admin checks/unchecks tools to assign them to an agent. The `allowed_tool_names` JSON array stores the selection.
**When to use:** Inside the agent edit modal.
**Example:**
```typescript
// Tool assignment section within the edit modal
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

### Pattern 5: Sidebar Navigation Item
**What:** Add "Agents" to the Admin nav group in the sidebar, between "Users" and "Settings".
**When to use:** Sidebar modification.
**Example:**
```typescript
// In frontend/src/components/sidebar.tsx
// Import Bot icon from lucide-react
import { Bot } from "lucide-react";

// Add to the Admin group items array:
{
  label: "Admin",
  visibleTo: "admin",
  items: [
    { label: "Users", href: "/admin/users", icon: Users },
    { label: "Agents", href: "/admin/agents", icon: Bot },  // NEW
    { label: "Settings", href: "/admin/settings", icon: Settings },
  ],
}
```

### Anti-Patterns to Avoid
- **Separate page for each agent function (list, edit, tools, usage):** Use a single page with tabs and modals. The existing admin section uses this pattern and admin pages should not proliferate.
- **Complex WYSIWYG editor for system prompts:** System prompts are plain text instructions. A monospace textarea is the correct tool. Rich text editors add complexity and corrupt prompt formatting.
- **Real-time usage charts with polling:** Overkill for v1. Usage stats are consulted occasionally, not monitored live. A simple aggregated table with a date range filter is sufficient.
- **Inline editing on the table:** The existing pattern is click-to-edit-modal. Inline editing introduces complex state management for marginal UX gain.
- **Separate API router file registration pattern:** Register the new agent_admin router in `main.py` under the `/api/admin` prefix, alongside the existing admin router. Use a sub-prefix like `/api/admin/agents`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model selection dropdown options | Dynamic model discovery from LiteLLM | Hardcoded list of supported models | The org only supports 3 providers (Anthropic/Gemini/Groq). A hardcoded list with friendly names is clearer and safer than auto-discovery, which could expose unsupported models. Update the list when new models are added. |
| Usage cost aggregation | Custom cost calculation logic | SQL aggregation on `agent_usage_logs.total_cost_usd` | LiteLLM already calculates per-call cost at invocation time (Phase 01). Admin just needs SUM/COUNT queries. |
| Slug generation | Manual slug input | Auto-generate from name (lowercase, replace spaces with hyphens, strip special chars) | Slugs should be deterministic from names. Let the backend auto-generate. |
| Tool list for assignment UI | Hardcoded tool list in frontend | Backend endpoint that returns registered tools from the tool registry | Tools are defined in `backend/app/tools/`. A backend endpoint should expose the tool registry (name + description) for the frontend to consume. |

**Key insight:** Phase 05 is purely a management interface over models and data created in Phase 01. It should not contain any AI logic, tool execution, or streaming code. It is CRUD + aggregation queries + UI.

## Common Pitfalls

### Pitfall 1: Editing System Prompt Loses Formatting
**What goes wrong:** Admin edits a multi-line system prompt in a textarea, but whitespace/newlines are stripped or mangled during save or display.
**Why it happens:** JSON serialization, HTML rendering, or Pydantic validation strips whitespace.
**How to avoid:** Store as `Text` column (not `String`). Send as raw string in JSON body. Render in a `<textarea>` with `whitespace-pre-wrap` for display. Test with prompts containing bullet points, code blocks, and multiple paragraphs.
**Warning signs:** Prompts that looked fine in the editor break when the agent uses them.

### Pitfall 2: Deleting an Agent That Is Being Used
**What goes wrong:** Admin deletes an agent while a user is mid-invocation, causing a runtime error.
**Why it happens:** No soft-delete or usage check.
**How to avoid:** Use soft delete (`is_active = False`) instead of hard delete. Show a confirmation dialog. If the agent has usage logs, warn the admin. Deactivated agents don't appear in user-facing agent lists but preserve their usage history.
**Warning signs:** 404 errors during agent invocations. Loss of usage statistics.

### Pitfall 3: Tool Registry Out of Sync with Agent Config
**What goes wrong:** An agent's `allowed_tool_names` references a tool name that no longer exists in the tool registry (e.g., after a tool is renamed or removed).
**Why it happens:** Tool definitions live in code (`backend/app/tools/`), but agent configs live in the database.
**How to avoid:** When loading agent config for execution, validate `allowed_tool_names` against the current tool registry and filter out any unknown tools (log a warning). In the admin UI, show a warning badge next to tools that are in the agent's config but not in the registry.
**Warning signs:** Agent silently loses access to tools after a code deploy.

### Pitfall 4: No Audit Trail for Agent Config Changes
**What goes wrong:** Admin changes a system prompt that causes an agent to misbehave, but there's no record of what the prompt was before.
**Why it happens:** Not logging changes to `AuditLog`.
**How to avoid:** Log every create/update/delete to `AuditLog` with `entity_type="agent"`. For updates, include the changed fields in the `changes` JSON column (especially `system_prompt` old/new values). This follows the exact pattern used for user updates in `admin.py`.
**Warning signs:** Cannot determine when or why an agent's behavior changed.

### Pitfall 5: Model Identifier Validation
**What goes wrong:** Admin types a model identifier incorrectly (e.g., "claude-sonnet" instead of "anthropic/claude-sonnet-4-5-20250929") and the agent fails at runtime.
**Why it happens:** Free-text model input without validation.
**How to avoid:** Use a `<select>` dropdown with a curated list of supported models, not a free-text input. The list should include only models the org has API keys for. Show the provider prefix clearly (e.g., "Anthropic: Claude Sonnet 4.5").
**Warning signs:** LiteLLM errors about unknown model identifiers.

## Code Examples

### Backend: Agent Admin Endpoints
```python
# Source: Follows patterns from backend/app/api/admin.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Schemas ---

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

class AgentConfigResponse(BaseModel):
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

class ToolInfoResponse(BaseModel):
    name: str
    description: str
    parameter_count: int

class UsageStatsResponse(BaseModel):
    agent_id: int
    agent_name: str
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    avg_duration_ms: float

# --- Endpoints ---

@router.get("/agents", response_model=List[AgentConfigResponse])
async def list_agents(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    query = db.query(AgentConfig)
    if not include_inactive:
        query = query.filter(AgentConfig.is_active == True)
    return query.order_by(AgentConfig.name).all()

@router.get("/agents/tools", response_model=List[ToolInfoResponse])
async def list_available_tools(
    current_user: BoardMember = Depends(require_admin),
):
    """Return all registered tools from the tool registry."""
    from app.tools import TOOL_REGISTRY
    return [
        ToolInfoResponse(
            name=name,
            description=tool["function"]["description"],
            parameter_count=len(tool["function"]["parameters"].get("properties", {})),
        )
        for name, tool in TOOL_REGISTRY.items()
    ]

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

### Frontend: Agent Admin API Client
```typescript
// Source: Follows patterns from frontend/src/lib/api.ts adminApi section

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
  return api.get(`/admin/agents${query}`);
},

getAgent: async (id: number): Promise<AgentConfig> => {
  return api.get(`/admin/agents/${id}`);
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

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Config files for agent setup | Database-backed admin UI | Industry pattern 2024-2025 | Non-technical admins can manage agents without code deploys |
| Code editor widgets for prompts | Plain textarea | Simplified by narrow-agent pattern | System prompts are natural language, not code. Textarea with monospace is standard. |
| Complex permission-gated tool access | Simple checkbox assignment | Appropriate for 3-5 built-in agents | When tool count is small, a checkbox list is clearer than ACL-based tool permissions |

**Deprecated/outdated:**
- JSON file-based prompt configuration: Replaced by database-backed management with admin UI
- Hardcoded agent definitions in code: Replaced by `agent_configs` table with runtime editability

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
   - Recommendation: Start with total aggregation + date range filter. This is simplest and covers the ADMIN-04 requirement. Time-series breakdowns can be added later.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), Next.js build (frontend type checking) |
| Config file | backend: `pytest.ini` or `pyproject.toml` (create in Wave 0 if absent) |
| Quick run command | `cd backend && python -m pytest tests/test_agent_admin.py -x` |
| Full suite command | `cd backend && python -m pytest --tb=short -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | CRUD for agent configs (create, read, update, soft-delete) | unit | `pytest tests/test_agent_admin.py::test_create_agent -x` | Wave 0 |
| ADMIN-01 | Only admin role can access agent admin endpoints | unit | `pytest tests/test_agent_admin.py::test_require_admin -x` | Wave 0 |
| ADMIN-01 | AuditLog entry created for each agent mutation | unit | `pytest tests/test_agent_admin.py::test_audit_log -x` | Wave 0 |
| ADMIN-02 | Tool list endpoint returns registered tools | unit | `pytest tests/test_agent_admin.py::test_list_tools -x` | Wave 0 |
| ADMIN-02 | Agent update with allowed_tool_names persists correctly | unit | `pytest tests/test_agent_admin.py::test_update_tools -x` | Wave 0 |
| ADMIN-03 | Agent update with system_prompt and model persists correctly | unit | `pytest tests/test_agent_admin.py::test_update_prompt_model -x` | Wave 0 |
| ADMIN-03 | Invalid model identifier is rejected | unit | `pytest tests/test_agent_admin.py::test_invalid_model -x` | Wave 0 |
| ADMIN-04 | Usage stats aggregation returns correct totals | unit | `pytest tests/test_agent_admin.py::test_usage_stats -x` | Wave 0 |
| ADMIN-04 | Usage stats date range filter works | unit | `pytest tests/test_agent_admin.py::test_usage_stats_date_filter -x` | Wave 0 |
| ALL | Frontend admin page builds without type errors | build | `cd frontend && npx next build` | N/A |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_agent_admin.py -x`
- **Per wave merge:** `cd backend && python -m pytest --tb=short -q && cd ../frontend && npx next build`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_agent_admin.py` -- covers ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04
- [ ] `backend/tests/conftest.py` -- shared fixtures (test DB, admin user, agent fixtures) -- may already exist from Phase 01
- [ ] Verify pytest is in `requirements.txt` dev dependencies

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
| `frontend/src/components/sidebar.tsx` | Add "Agents" nav item under Admin group |
| `frontend/src/lib/api.ts` | Add `AgentConfig`, `ToolInfo`, `AgentUsageStats` types and `agentAdminApi` methods |
| `backend/app/main.py` | Register `agent_admin.router` under `/api/admin` prefix |

## Sources

### Primary (HIGH confidence)
- `backend/app/api/admin.py` (lines 1-565) -- Existing admin endpoint patterns (schemas, auth, audit logging)
- `frontend/src/app/admin/users/page.tsx` (lines 1-541) -- Existing admin page layout, styling, tabs, tables, modals
- `frontend/src/app/admin/settings/page.tsx` (lines 1-687) -- Existing admin settings page with tabs and forms
- `frontend/src/components/edit-user-modal.tsx` (lines 1-192) -- Existing modal pattern (Card-based, backdrop blur)
- `frontend/src/components/sidebar.tsx` (lines 1-189) -- Existing nav structure and Admin group
- `frontend/src/lib/api.ts` (lines 1003-1215) -- Existing adminApi client pattern
- `.planning/phases/01-agent-infrastructure/01-RESEARCH.md` -- AgentConfig and AgentUsageLog model definitions, tool registry architecture

### Secondary (MEDIUM confidence)
- `frontend/src/hooks/use-permissions.tsx` -- Permission/role checking hooks for admin gate
- `backend/app/api/auth.py` -- `require_admin` dependency implementation

### Tertiary (LOW confidence)
- LiteLLM model identifier formats -- model list may need updating as new models release

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already in project, no new dependencies
- Architecture: HIGH -- Directly follows existing admin page and API patterns documented in the codebase
- Pitfalls: HIGH -- All identified pitfalls are standard CRUD concerns with known solutions
- UI/UX patterns: HIGH -- Derived directly from existing admin pages in the same codebase

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days -- patterns are stable, model list may need updates)
