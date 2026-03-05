# Phase 01: Agent Infrastructure & Streaming UX - Research Supplement

**Researched:** 2026-03-04
**Supplements:** `01-RESEARCH.md` (base research on LiteLLM, agent loop, SSE, security)
**Focus areas:** Embedded streaming UX patterns, database schema design, testing strategy, codebase integration points
**Confidence:** HIGH

## Summary

This supplement addresses four gaps in the base research: (1) how to embed streaming agent responses inline on existing pages in this specific React/Next.js codebase, (2) the precise database schema for agent configuration tables aligned with the existing SQLAlchemy patterns, (3) a testing strategy for the agent loop, tool execution, and streaming -- given this project has no existing test infrastructure, and (4) exactly which files need to be created or modified in this codebase.

The most critical finding is that the **existing Next.js proxy route (`/api/proxy/[...path]/route.ts`) does not support streaming** -- it awaits the full response body before forwarding. SSE endpoints must either bypass the proxy (frontend hits backend directly for agent calls) or the proxy must be extended with a streaming code path. The recommended approach is to add SSE streaming support to the existing proxy.

**Primary recommendation:** Extend the proxy with streaming support for `text/event-stream` responses. Build a reusable `useAgentStream` hook and `<AgentResponsePanel>` component. Add `react-markdown` for agent output rendering. Schema uses three tables (`agent_configs`, `agent_tools`, `agent_usage_logs`) following existing SQLAlchemy patterns.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGENT-01 | System can route user requests to configured agents with system prompt, model, and allowed tools | Database schema for `agent_configs` table, agent runner service architecture, tool registry pattern |
| AGENT-02 | Agent tools call the board's own REST API with the user's auth context (preserving permissions) | Tool-via-API pattern with `X-User-Email` header forwarding, `httpx.AsyncClient` internal calls |
| AGENT-03 | Agent responses stream to the frontend via SSE | Proxy streaming fix, `useAgentStream` hook, SSE event protocol, `EventSourceResponse` endpoint |
| AGENT-04 | System supports multiple LLM providers (Anthropic, Gemini, Groq) via LiteLLM | LiteLLM provider configuration, API key management in Settings, model validation |
| UX-02 | Agent responses appear inline on the page they're triggered from | `<AgentResponsePanel>` component design, collapsible panel pattern, page-level integration |
| UX-03 | User sees streaming agent output with tool call indicators | Streaming text renderer, `<ToolCallIndicator>` component, SSE event type handling |
| UX-04 | Agent actions apply directly to the current context | Tool result events trigger page data refresh, optimistic UI updates after tool execution |
</phase_requirements>

---

## 1. Embedded Streaming UX Patterns

### Critical Finding: Proxy Does Not Stream

The existing Next.js proxy at `frontend/src/app/api/proxy/[...path]/route.ts` buffers the entire backend response before forwarding:

```typescript
// CURRENT (broken for SSE):
const responseBody = isBinary
  ? await response.arrayBuffer()   // <-- awaits full body
  : await response.text();          // <-- awaits full body

return new NextResponse(responseBody, { ... });
```

**This means SSE events will NOT stream through the proxy.** The client will receive the entire response only after the backend generator completes (which could be 30+ seconds for an agent run).

### Solution: Streaming Proxy for SSE

Add SSE detection to the proxy that forwards the `ReadableStream` directly instead of buffering:

```typescript
// FIXED: Stream SSE responses through proxy
const respContentType = response.headers.get("content-type") || "";
const isSSE = respContentType.includes("text/event-stream");

if (isSSE) {
  // Forward the ReadableStream directly -- do NOT buffer
  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

// ... existing buffered logic for non-SSE responses
```

**Confidence: HIGH** -- Next.js `NextResponse` accepts a `ReadableStream` as body. This is the standard pattern for streaming proxy routes in Next.js 14+/15+. Verified against Next.js App Router documentation.

### Frontend SSE Consumption Hook: `useAgentStream`

A custom React hook that encapsulates SSE consumption, state management, and cleanup:

```typescript
// frontend/src/hooks/use-agent-stream.ts

interface AgentStreamState {
  status: "idle" | "streaming" | "done" | "error";
  text: string;                     // Accumulated text output
  toolCalls: ToolCallEvent[];       // Tool calls with status
  error: string | null;
}

interface ToolCallEvent {
  id: string;
  name: string;
  status: "executing" | "completed" | "failed";
  result?: string;
}

function useAgentStream() {
  const [state, setState] = useState<AgentStreamState>({
    status: "idle",
    text: "",
    toolCalls: [],
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (agentSlug: string, message: string, context?: Record<string, unknown>) => {
    // Abort any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ status: "streaming", text: "", toolCalls: [], error: null });

    try {
      const response = await fetch("/api/proxy/agents/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Email": userEmail,  // from session
        },
        body: JSON.stringify({ agent_slug: agentSlug, message, context }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Agent error: ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              handleEvent(event, setState);
            } catch { /* skip malformed */ }
          }
        }
      }

      setState(prev => ({ ...prev, status: "done" }));
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setState(prev => ({
          ...prev,
          status: "error",
          error: (err as Error).message,
        }));
      }
    }
  }, [userEmail]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState(prev => ({ ...prev, status: "idle" }));
  }, []);

  return { ...state, run, cancel };
}
```

**Key design decisions:**
- **AbortController for cancellation** -- user can stop a running agent
- **Buffer-based SSE parsing** -- handles partial chunks correctly (critical for real streaming)
- **Ref-based abort** -- prevents stale closure issues
- **No EventSource API** -- `EventSource` only supports GET; agent invocations need POST with a body

**Confidence: HIGH** -- This is the standard pattern for POST-based SSE consumption in React. The buffer-based line parsing is necessary because `ReadableStream` chunks do not align with SSE event boundaries.

### SSE Event Protocol

Define a clear protocol for the events the backend emits and the frontend consumes:

```typescript
// Shared event types (document in both backend and frontend)
type AgentEvent =
  | { type: "start"; agent_name: string }
  | { type: "text_delta"; content: string }
  | { type: "tool_start"; tool_name: string; tool_call_id: string }
  | { type: "tool_result"; tool_name: string; tool_call_id: string; result: string; success: boolean }
  | { type: "error"; message: string }
  | { type: "usage"; prompt_tokens: number; completion_tokens: number; model: string }
  | { type: "done" };
```

**Why these specific event types:**
- `start` -- lets the UI show the agent name and a "thinking" indicator before any text arrives
- `text_delta` -- individual text chunks for progressive rendering (not `text` -- "delta" clarifies it is incremental)
- `tool_start` / `tool_result` -- separate events for tool lifecycle (show spinner during execution, result after)
- `usage` -- sent at the end for cost tracking (logged to `agent_usage_logs`)
- `done` -- explicit termination signal (do not rely on stream close alone)
- `error` -- surface errors to the user inline

### Component: `<AgentResponsePanel>`

An embeddable panel that renders agent output inline on any page. Collapsible, with a trigger button.

```
+------------------------------------------------------+
| [AI icon] Agent Name                    [Collapse ^]  |
|------------------------------------------------------|
| [Thinking...]                                         |
|                                                       |
| Here is the response text streaming in progressively  |
| as tokens arrive from the LLM...                      |
|                                                       |
| [tool icon] create_agenda_item  [checkmark] Done      |
|   Created "Budget Review" (15 min, discussion)        |
|                                                       |
| [tool icon] create_agenda_item  [spinner] Running...  |
|                                                       |
| More text continues to stream...                      |
|                                                       |
+------------------------------------------------------+
```

**Component structure:**
```
<AgentResponsePanel>
  <AgentTrigger />         -- Button/textarea to invoke the agent
  <AgentOutput>            -- Streaming text (react-markdown for formatting)
    <ToolCallIndicator />  -- Individual tool call status
  </AgentOutput>
  <AgentFooter />          -- Usage stats, cancel button, retry
</AgentResponsePanel>
```

**Styling:** Follow existing dark theme with gold accents. Use the same `Card`, `CardHeader`, `CardContent` pattern. Tool call indicators use the same status color scheme as agenda items (`bg-blue-500/20` for running, `bg-green-500/20` for completed).

### Markdown Rendering for Agent Output

The project does **not** currently have a markdown rendering library. Agent responses will contain structured text (headers, lists, bold), so a lightweight markdown renderer is needed.

**Recommendation: `react-markdown`**

```bash
npm install react-markdown
```

- Lightweight (25KB gzipped), no heavy dependencies
- Works with React 19 (the project uses React 19.2.3)
- Supports streaming -- just pass the accumulating text string as children; React re-renders naturally as state updates
- No `remark`/`rehype` plugins needed for basic formatting (bold, italic, lists, headings)

**Alternative considered:** Raw `dangerouslySetInnerHTML` with a simple regex-based markdown parser. Rejected because: XSS risk, edge cases in parsing, and `react-markdown` is minimal overhead.

**Confidence: MEDIUM** -- `react-markdown` compatibility with React 19 needs validation during implementation (most recent verified version is v9.x which supports React 18; React 19 support likely works but should be tested).

### Page Integration Pattern

Agents are triggered from **existing pages** (meetings, decisions, etc.), not a separate chat page. The `<AgentResponsePanel>` is embedded as a collapsible section within the existing page layout.

**Example: Meeting detail page (`/meetings/[id]/page.tsx`)**

```tsx
// In the meeting detail page, add an agent panel in the sidebar column:
<div className="space-y-6">
  {/* Existing sidebar content (calendar, recording) */}

  {/* Agent panel -- only for board+ users */}
  {isBoardLevel && (
    <AgentResponsePanel
      agentSlug="meeting-setup"
      context={{ meeting_id: meeting.id }}
      onToolComplete={() => fetchMeeting()}  // Refresh page data
      title="AI Assistant"
      placeholder="Ask the assistant to help with this meeting..."
    />
  )}
</div>
```

**Key pattern: `onToolComplete` callback.** When the agent executes a tool (e.g., creates an agenda item), the page re-fetches its data. This makes agent actions "apply directly to the current context" (UX-04) without any special sync mechanism -- the existing data fetching pattern already handles it.

### Auto-scroll During Streaming

During streaming, the response panel should auto-scroll to show the latest text. Use a ref on the bottom of the output area:

```tsx
const bottomRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (status === "streaming") {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }
}, [text, status]);
```

---

## 2. Database Schema

### Schema Design Principles (Aligned with Existing Codebase)

After reviewing the existing models (`BoardMember`, `Meeting`, `Decision`, etc.), the agent schema follows these patterns:

- **Integer primary keys** with `index=True` (not UUIDs -- consistent with all existing tables)
- **`Mapped[type]` annotations** with `mapped_column()` (SQLAlchemy 2.0 style, consistent with `member.py`, `meeting.py`)
- **`datetime.utcnow` defaults** for timestamps (matches existing pattern, though deprecated -- keep consistent)
- **String columns with explicit lengths** (`String(100)`, `String(255)`, etc.)
- **`Text` for long content** (system prompts, descriptions)
- **ForeignKey to `board_members.id`** for user references
- **Soft delete not needed** -- agent configs can be hard-deleted by admin (is_active flag for deactivation instead)

### Table: `agent_configs`

```python
# backend/app/models/agent.py

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentConfig(Base):
    """Agent configuration -- stores system prompt, model, and tool permissions."""

    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "anthropic/claude-sonnet-4-5-20250929", "gemini/gemini-2.0-flash", "groq/llama-3.3-70b-versatile"
    temperature: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSON array of tool names this agent is allowed to use
    # e.g., ["create_agenda_item", "list_meetings", "get_meeting"]
    allowed_tool_names: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    usage_logs: Mapped[List["AgentUsageLog"]] = relationship(
        "AgentUsageLog", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AgentConfig {self.slug} ({self.model})>"
```

**Design decisions:**
- `slug` is indexed and unique -- used in API URLs and frontend routing (e.g., `/api/agents/meeting-setup/run`)
- `allowed_tool_names` is JSON array rather than a join table -- simpler for the small number of tools (~10-20 total), and matches the admin UI pattern (checkbox list). The base research recommended this approach.
- `model` stores the LiteLLM model identifier with provider prefix -- this is the exact string passed to `acompletion()`
- No `version` column yet -- deferred to Phase 05 admin management (keep it simple for Phase 01)

### Table: `agent_tools` (Registry, Not Per-Agent)

The tool registry is a **code-level registry**, not a database table. Tool definitions are Python code (function signature + JSON schema). The database stores only which tools an agent is allowed to use (via `allowed_tool_names` JSON column on `agent_configs`).

**Why no `agent_tools` table:**
- Tool definitions include executable code (the function that calls the API) -- this cannot live in the database
- Tool schemas are tightly coupled to the Python function signatures
- The "tool shed" (Phase 05 admin feature) shows tools from the code registry and lets admins toggle them per agent -- the `allowed_tool_names` JSON array is sufficient for this

**Code-level tool registry:**
```python
# backend/app/tools/__init__.py

TOOL_REGISTRY: dict[str, ToolDefinition] = {}

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters_schema: dict       # OpenAI function calling format
    handler: Callable             # async function(params, user_context) -> str
    category: str                 # "meetings", "documents", "decisions", "ideas"
    requires_permission: str | None  # e.g., "meetings.create" -- checked before execution
```

### Table: `agent_usage_logs`

```python
class AgentUsageLog(Base):
    """Tracks each agent invocation for usage stats and cost tracking."""

    __tablename__ = "agent_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_configs.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False, index=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent: Mapped["AgentConfig"] = relationship("AgentConfig", back_populates="usage_logs")
    user: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<AgentUsageLog agent={self.agent_id} user={self.user_id} cost=${self.total_cost_usd:.4f}>"
```

**Design decisions:**
- `model_used` is separate from `agent.model` because the admin might change the agent's model between invocations -- the log records what was actually used
- `success` + `error_message` for error tracking without a separate table
- Indexed on `agent_id` and `user_id` for the admin usage dashboard queries (Phase 05)
- No `conversation_id` -- agents are single-turn for v2.0 (per base research recommendation)

### Alembic Migration

The project has `alembic.ini` but no migrations directory found. The `main.py` uses `Base.metadata.create_all(bind=engine)` for table creation. For the new agent tables:

1. Create migration via: `cd backend && alembic revision --autogenerate -m "add agent config and usage tables"`
2. The migration should create `agent_configs` and `agent_usage_logs` tables
3. Include a data migration to seed the three built-in agents (Meeting Setup, Minutes Generator, Resolution Writer) with initial system prompts

### Model Registration

Add to `backend/app/models/__init__.py`:

```python
from app.models.agent import AgentConfig, AgentUsageLog

__all__ = [
    # ... existing exports ...
    "AgentConfig",
    "AgentUsageLog",
]
```

### Seed Data for Built-in Agents

```python
# In lifespan function or alembic data migration:
builtin_agents = [
    AgentConfig(
        name="Meeting Setup",
        slug="meeting-setup",
        description="Parses meeting descriptions into structured agendas",
        system_prompt="...",  # Detailed prompt for Phase 02
        model="anthropic/claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_iterations=5,
        allowed_tool_names=["create_agenda_item", "get_meeting", "list_members"],
    ),
    AgentConfig(
        name="Minutes Generator",
        slug="minutes-generator",
        description="Creates formatted meeting minutes from transcripts",
        system_prompt="...",  # Detailed prompt for Phase 03
        model="anthropic/claude-sonnet-4-5-20250929",
        temperature=0.2,
        max_iterations=3,
        allowed_tool_names=["get_meeting", "get_agenda", "get_attendance"],
    ),
    AgentConfig(
        name="Resolution Writer",
        slug="resolution-writer",
        description="Drafts board resolution documents",
        system_prompt="...",  # Detailed prompt for Phase 04
        model="anthropic/claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_iterations=3,
        allowed_tool_names=["create_resolution", "get_decision"],
    ),
]
```

**Note:** System prompts will be filled in during Phases 02-04 when each agent is actually built. Phase 01 seeds the configs with placeholder prompts for testing the infrastructure.

---

## 3. Testing Strategy

### Current Test Infrastructure

**There are no existing tests in this codebase.** No `tests/` directory, no `pytest.ini`, no test configuration. The `backend/requirements.txt` does not include `pytest`.

This means Phase 01 must establish test infrastructure from scratch.

### Test Framework Setup

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio + httpx (for FastAPI TestClient) |
| Config file | `backend/pytest.ini` (to be created) |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

**Additional test dependencies:**
```
# Add to backend/requirements.txt (dev section or separate requirements-dev.txt):
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.26.0  # already present, used for TestClient
```

### Test Categories for Phase 01

#### Unit Tests: Agent Runner

Test the core agent loop in isolation (mock LiteLLM calls):

| Test | What It Validates | File |
|------|-------------------|------|
| `test_agent_runner_simple_response` | Agent returns text when no tool calls | `tests/test_agent_runner.py` |
| `test_agent_runner_tool_call_cycle` | Agent calls tool, feeds result back, gets final response | `tests/test_agent_runner.py` |
| `test_agent_runner_max_iterations` | Agent stops after max_iterations | `tests/test_agent_runner.py` |
| `test_agent_runner_tool_error_handling` | Tool execution failure is handled gracefully | `tests/test_agent_runner.py` |
| `test_agent_runner_streaming_events` | Streaming generator yields correct event types in order | `tests/test_agent_runner.py` |

```python
# Example test structure:
@pytest.mark.asyncio
async def test_agent_runner_simple_response(mock_litellm):
    """Agent returns text when LLM has no tool calls."""
    mock_litellm.acompletion.return_value = mock_response(content="Hello!", tool_calls=None)

    result = await run_agent(
        model="anthropic/claude-sonnet-4-5-20250929",
        system_prompt="You are a helpful assistant.",
        user_message="Hi",
        tools=[],
        tool_executor=mock_executor,
    )

    assert result == "Hello!"
    mock_litellm.acompletion.assert_called_once()
```

#### Integration Tests: Tool Execution via API

Test that tools correctly call the board API with user auth context:

| Test | What It Validates | File |
|------|-------------------|------|
| `test_tool_creates_agenda_item` | Tool calls POST /api/meetings/{id}/agenda with correct params | `tests/test_tools.py` |
| `test_tool_respects_user_permissions` | Tool with non-admin user gets 403 on admin-only operations | `tests/test_tools.py` |
| `test_tool_handles_api_error` | Tool returns error message when API returns 4xx/5xx | `tests/test_tools.py` |
| `test_tool_registry_returns_schemas` | All registered tools have valid JSON schemas | `tests/test_tools.py` |

#### Integration Tests: SSE Endpoint

Test the streaming endpoint end-to-end (with mocked LiteLLM):

| Test | What It Validates | File |
|------|-------------------|------|
| `test_agent_run_returns_sse` | POST /api/agents/run returns content-type text/event-stream | `tests/test_agent_api.py` |
| `test_agent_run_streams_events` | SSE events arrive in correct order: start -> text_delta(s) -> done | `tests/test_agent_api.py` |
| `test_agent_run_with_tool_calls` | SSE includes tool_start and tool_result events | `tests/test_agent_api.py` |
| `test_agent_run_requires_auth` | Returns 401 without X-User-Email | `tests/test_agent_api.py` |
| `test_agent_run_unknown_agent` | Returns 404 for non-existent agent slug | `tests/test_agent_api.py` |
| `test_agent_run_logs_usage` | AgentUsageLog created after successful run | `tests/test_agent_api.py` |

```python
# Example SSE test:
@pytest.mark.asyncio
async def test_agent_run_streams_events(client, mock_litellm, seed_agent):
    """SSE endpoint streams events in correct order."""
    mock_litellm.acompletion.return_value = mock_response(content="Test response")

    async with client.stream(
        "POST",
        "/api/agents/run",
        json={"agent_slug": "meeting-setup", "message": "Hello"},
        headers={"X-User-Email": "amir.haque@themany.com"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert events[0]["type"] == "start"
        assert events[-1]["type"] == "done"
        text_events = [e for e in events if e["type"] == "text_delta"]
        assert len(text_events) > 0
```

#### Schema/Model Tests

| Test | What It Validates | File |
|------|-------------------|------|
| `test_agent_config_creation` | AgentConfig can be created with all fields | `tests/test_models.py` |
| `test_agent_config_slug_unique` | Duplicate slugs raise IntegrityError | `tests/test_models.py` |
| `test_usage_log_foreign_keys` | Usage log correctly links to agent and user | `tests/test_models.py` |

### Test Fixtures

```python
# backend/tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.session import Base
from app.main import app
from app.db import get_db

@pytest.fixture
def db_engine():
    """In-memory SQLite for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db_engine):
    """Test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden DB."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def seed_agent(db_session):
    """Seed a test agent config."""
    from app.models.agent import AgentConfig
    agent = AgentConfig(
        name="Test Agent",
        slug="test-agent",
        system_prompt="You are a test assistant.",
        model="anthropic/claude-sonnet-4-5-20250929",
    )
    db_session.add(agent)
    db_session.commit()
    return agent

@pytest.fixture
def seed_user(db_session):
    """Seed a test board member."""
    from app.models.member import BoardMember
    user = BoardMember(
        email="test@themany.com",
        name="Test User",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def mock_litellm(monkeypatch):
    """Mock LiteLLM acompletion to avoid real API calls."""
    import unittest.mock as mock
    mock_module = mock.AsyncMock()
    monkeypatch.setattr("app.services.agent_runner.acompletion", mock_module)
    return mock_module
```

### Frontend Testing (Manual for Phase 01)

Frontend tests are **manual-only** for Phase 01. The project has no frontend test setup (no Jest, Vitest, or Playwright tests). Setting up frontend testing infrastructure is out of scope for this phase.

**Manual test plan:**
1. Trigger an agent from a page and verify inline streaming response
2. Verify tool call indicators appear and disappear correctly
3. Verify cancellation (user clicks cancel during stream)
4. Verify the page refreshes data after tool execution
5. Swap model provider in admin and re-run -- verify same UX behavior

---

## 4. Codebase Integration Points

### Files to Create (Backend)

| File | Purpose |
|------|---------|
| `backend/app/models/agent.py` | `AgentConfig`, `AgentUsageLog` SQLAlchemy models |
| `backend/app/schemas/agent.py` | Pydantic request/response schemas for agent API |
| `backend/app/api/agents.py` | Agent API endpoints: `POST /run`, `GET /list` |
| `backend/app/services/agent_runner.py` | Core agent loop (streaming + non-streaming) |
| `backend/app/services/llm_provider.py` | LiteLLM wrapper, API key validation, model config |
| `backend/app/tools/__init__.py` | Tool registry (`TOOL_REGISTRY`, `ToolDefinition`) |
| `backend/app/tools/meetings.py` | Meeting-related tools (create_agenda_item, get_meeting, list_meetings) |
| `backend/tests/__init__.py` | Test package init |
| `backend/tests/conftest.py` | Shared test fixtures |
| `backend/tests/test_agent_runner.py` | Unit tests for agent loop |
| `backend/tests/test_agent_api.py` | Integration tests for SSE endpoint |
| `backend/tests/test_tools.py` | Tool execution tests |
| `backend/pytest.ini` | Pytest configuration |

### Files to Create (Frontend)

| File | Purpose |
|------|---------|
| `frontend/src/hooks/use-agent-stream.ts` | SSE consumption hook |
| `frontend/src/components/agent-response-panel.tsx` | Embeddable agent response UI |
| `frontend/src/components/tool-call-indicator.tsx` | Tool call status display |
| `frontend/src/lib/agent-api.ts` | Agent API client functions |

### Files to Modify

| File | Change | Why |
|------|--------|-----|
| `backend/requirements.txt` | Add `litellm>=1.80.0`, bump `fastapi>=0.135.0`, add `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` | New dependencies |
| `backend/app/models/__init__.py` | Import `AgentConfig`, `AgentUsageLog` | Model registration |
| `backend/app/main.py` | Add `app.include_router(agents.router, ...)`, add agent seeding in lifespan | Router registration, seed data |
| `backend/app/config.py` | Add `anthropic_api_key`, `gemini_api_key`, `groq_api_key` to `Settings` | LLM provider API keys |
| `frontend/src/app/api/proxy/[...path]/route.ts` | Add SSE streaming detection and pass-through | SSE does not work through buffered proxy |
| `frontend/package.json` | Add `react-markdown` dependency | Agent response rendering |
| `frontend/src/lib/api.ts` | Add `agentsApi` section | Agent API client |

### API Endpoints to Implement

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/agents/run` | `require_member` | Run an agent (SSE streaming response) |
| `GET` | `/api/agents` | `require_member` | List available agents (active only) |
| `GET` | `/api/agents/{slug}` | `require_member` | Get agent details (for admin/debug) |

**Request schema for `/api/agents/run`:**
```python
class RunAgentRequest(BaseModel):
    agent_slug: str                              # Which agent to run
    message: str                                 # User's input
    context: dict | None = None                  # Page context (meeting_id, etc.)
```

**Why `agent_slug` not `agent_id`:** Slugs are stable, human-readable identifiers that can be hardcoded in frontend code (e.g., `agentSlug="meeting-setup"`). IDs can change across environments.

### Router Registration Pattern

Follow existing pattern in `main.py`:

```python
from app.api import agents

app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
```

### Auth Pattern for Agent Endpoints

The agent `run` endpoint uses `require_member` (board-level access). The user's email is forwarded to tool execution via the `X-User-Email` header pattern already established in the codebase:

```python
@router.post("/run", response_class=EventSourceResponse)
async def run_agent(
    request: RunAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),  # Existing dependency
):
    # current_user.email is passed to tool executor
    # Tools call internal API with headers={"X-User-Email": current_user.email}
```

### LLM API Key Configuration

Add to `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # LLM Provider API Keys
    anthropic_api_key: str = ""
    gemini_api_key: str = ""        # Google AI Studio key
    groq_api_key: str = ""
```

LiteLLM reads these from environment variables automatically (it checks `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`), but storing them in `Settings` allows validation at startup.

---

## 5. Common Pitfalls (Supplement to Base Research)

### Pitfall S1: Next.js Proxy Buffering Kills SSE

**What goes wrong:** Developer builds SSE backend endpoint, tests it with `curl` (works), but frontend shows nothing for 30 seconds then all text appears at once.
**Why it happens:** The Next.js proxy route awaits `response.text()` before forwarding, buffering the entire SSE stream.
**How to avoid:** Detect `text/event-stream` content-type in the proxy and forward `response.body` (ReadableStream) directly. See section 1 above.
**Warning signs:** SSE works via direct backend URL but not through `/api/proxy/`.

### Pitfall S2: React State Batching Causes Choppy Streaming

**What goes wrong:** Text updates appear in batches rather than character-by-character.
**Why it happens:** React 18+ automatically batches state updates. Multiple rapid `setState` calls in an event handler are batched into one re-render.
**How to avoid:** This is actually acceptable behavior -- batch rendering every ~16ms is fine for streaming text. Do NOT try to force synchronous rendering. The user perceives smooth streaming even with batched updates. However, avoid calling `setState` inside a `for` loop processing multiple events -- instead, accumulate all text from the current chunk and set state once.
**Warning signs:** `setState` called dozens of times per second. Use `flushSync` only as last resort (it is almost never needed).

### Pitfall S3: AbortController Not Cleaning Up SSE Streams

**What goes wrong:** User navigates away from the page while agent is streaming. The SSE connection stays open, the agent keeps running on the backend, and the frontend logs errors about updating unmounted components.
**Why it happens:** No cleanup on component unmount.
**How to avoid:** (1) AbortController in the hook cancels the fetch on unmount. (2) Backend detects client disconnect (FastAPI SSE handles this automatically -- the generator stops when the client disconnects). (3) Hook cleanup via `useEffect` return.

### Pitfall S4: Tool Call Permission Check Bypass

**What goes wrong:** A tool that creates meeting agenda items is allowed in the agent's `allowed_tool_names`, but the tool does not check if the user has `meetings.create` permission before calling the API.
**Why it happens:** The developer assumes the API endpoint's auth middleware handles it -- which it does, but only if the user's email is correctly forwarded.
**How to avoid:** Double-check: (1) `X-User-Email` header is set on every internal API call, (2) the tool definition has a `requires_permission` field that is checked before execution as an early gate, (3) the board API endpoint itself enforces the permission (defense in depth).

---

## 6. Architecture Patterns (Supplement)

### Pattern S1: Hybrid Streaming Strategy (Recommended)

The base research's Open Question #1 asked whether to stream everything or use non-streaming for tool call iterations. After analyzing the tradeoffs:

**Recommended approach: Stream text, non-stream for tool iterations.**

```python
async def run_agent_streaming(config, message, user_context):
    messages = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": message},
    ]

    for iteration in range(config.max_iterations):
        # First, make a NON-STREAMING call to detect tool calls
        response = await acompletion(
            model=config.model,
            messages=messages,
            tools=get_tools(config.allowed_tool_names),
            stream=False,
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            # Execute tools (not streamed, but emit events for UI)
            messages.append(msg.model_dump())
            for tc in msg.tool_calls:
                yield {"type": "tool_start", "tool_name": tc.function.name, "tool_call_id": tc.id}
                result = await execute_tool(tc, user_context)
                yield {"type": "tool_result", "tool_name": tc.function.name, "tool_call_id": tc.id, "result": result, "success": True}
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            # Final response -- stream THIS one for progressive display
            final_response = await acompletion(
                model=config.model,
                messages=messages,
                stream=True,  # Only stream the final response
            )
            async for chunk in final_response:
                if chunk.choices[0].delta.content:
                    yield {"type": "text_delta", "content": chunk.choices[0].delta.content}
            break

    yield {"type": "usage", "prompt_tokens": ..., "completion_tokens": ..., "model": config.model}
    yield {"type": "done"}
```

**Why this approach:**
- Avoids the tool call accumulation problem entirely (Pitfall 1 from base research)
- Text still streams progressively for the final response (user sees tokens appearing)
- Tool call events are emitted immediately when tools start/complete (no delay)
- Much simpler code than full streaming with tool call chunk accumulation

**Tradeoff:** If the agent does 3 tool call iterations before producing text, the user sees tool indicators but no text for those iterations. The final text then streams. This is acceptable because:
1. Tool call iterations are fast (sub-second API calls + LLM inference)
2. The user sees tool indicators so they know the agent is working
3. Streaming text only for the final response is still perceived as responsive

### Pattern S2: Tool Execution with Permission Pre-check

```python
async def execute_tool(tool_call, user_context: dict) -> str:
    """Execute a tool with permission checking."""
    tool = TOOL_REGISTRY.get(tool_call.function.name)
    if not tool:
        return json.dumps({"error": f"Unknown tool: {tool_call.function.name}"})

    # Pre-check: does the user have the required permission?
    if tool.requires_permission:
        # Quick check before making the API call
        user_permissions = user_context.get("permissions", [])
        if tool.requires_permission not in user_permissions:
            return json.dumps({
                "error": f"Permission denied: {tool.requires_permission} required",
                "user_role": user_context.get("role"),
            })

    # Execute the tool (calls board API with user's auth context)
    try:
        params = json.loads(tool_call.function.arguments)
        result = await tool.handler(params, user_context)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### Pattern S3: Frontend Page Data Refresh After Tool Execution

```typescript
// In the useAgentStream hook or component:
function handleEvent(event: AgentEvent, setState, onToolComplete?) {
  switch (event.type) {
    case "text_delta":
      setState(prev => ({ ...prev, text: prev.text + event.content }));
      break;
    case "tool_start":
      setState(prev => ({
        ...prev,
        toolCalls: [...prev.toolCalls, {
          id: event.tool_call_id,
          name: event.tool_name,
          status: "executing"
        }],
      }));
      break;
    case "tool_result":
      setState(prev => ({
        ...prev,
        toolCalls: prev.toolCalls.map(tc =>
          tc.id === event.tool_call_id
            ? { ...tc, status: event.success ? "completed" : "failed", result: event.result }
            : tc
        ),
      }));
      // Trigger page data refresh
      onToolComplete?.();
      break;
    case "done":
      setState(prev => ({ ...prev, status: "done" }));
      break;
  }
}
```

---

## 7. Don't Hand-Roll (Supplement)

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE proxy streaming | Custom WebSocket relay or separate streaming server | Next.js `NextResponse(response.body)` stream pass-through | One line fix in the existing proxy. WebSocket adds bidirectional complexity that SSE doesn't need. |
| Markdown rendering | Regex-based custom parser | `react-markdown` | Edge cases in markdown parsing are endless. Library is 25KB gzipped. |
| SSE event parsing | Manual string splitting with regex | Buffer-based line parser in `useAgentStream` | Must handle partial chunks -- SSE event boundaries do not align with `ReadableStream` chunk boundaries |
| Frontend state for streaming | Redux/Zustand store for agent state | Local component state via `useState` | Agent state is ephemeral (per-invocation), not shared across components. Global state is overkill. |

---

## 8. Open Questions (Resolved or Deferred)

### Resolved from Base Research

**Q1 (Hybrid streaming):** Resolved. Use non-streaming for tool iterations, stream only the final text response. See Pattern S1 above.

**Q3 (Internal API latency):** Resolved. Localhost HTTP calls add <1ms latency. LLM inference is 1-10 seconds. The overhead is negligible. Use internal API calls.

### New Open Questions

1. **react-markdown compatibility with React 19**
   - What we know: react-markdown v9.x works with React 18. React 19 was released Dec 2024.
   - What's unclear: Whether react-markdown v9.x is fully compatible with React 19.2.3
   - Recommendation: Install and test during implementation. If incompatible, fall back to plain text rendering with `whitespace-pre-wrap` -- agent responses are still useful without markdown formatting.

2. **FastAPI SSE keepalive through Railway proxy**
   - What we know: FastAPI SSE sends automatic keep-alive pings. Railway uses HTTP proxying.
   - What's unclear: Whether Railway's proxy has a read timeout that could kill long-running SSE connections (agent runs can take 30+ seconds with tool calls).
   - Recommendation: Test in staging. If Railway times out, add explicit keep-alive events (empty SSE comments) every 15 seconds during tool execution. FastAPI's `EventSourceResponse` supports this.

3. **LiteLLM streaming with Groq provider**
   - What we know: Groq has very fast inference (<1 second) and may not benefit from streaming.
   - What's unclear: Whether LiteLLM's streaming with Groq provider works identically to Anthropic/Gemini.
   - Recommendation: Test with all three providers. The hybrid approach (non-stream for tool calls, stream for final) minimizes provider-specific streaming differences.

---

## Sources

### Primary (HIGH confidence)
- **Existing codebase analysis** -- proxy route, auth patterns, model structure, API patterns (direct code review)
- **Next.js App Router streaming** -- `NextResponse` accepts `ReadableStream` for streaming responses (verified in Next.js docs)
- **FastAPI SSE** -- `EventSourceResponse` with async generators (verified in FastAPI 0.135+ docs)

### Secondary (MEDIUM confidence)
- **react-markdown** -- v9.x supports React 18, likely React 19 compatible (needs validation)
- **LiteLLM stream_chunk_builder** -- documented utility for reconstructing streaming responses

### Architecture Decisions (Project-Specific, HIGH confidence)
- Proxy streaming fix pattern verified against Next.js source
- Auth forwarding pattern verified against existing codebase (`X-User-Email` header)
- SQLAlchemy model patterns verified against existing models in codebase

---

## Metadata

**Confidence breakdown:**
- Proxy streaming fix: HIGH -- verified Next.js supports ReadableStream in NextResponse
- useAgentStream hook: HIGH -- standard fetch + ReadableStream pattern, well-established
- Database schema: HIGH -- follows existing codebase patterns exactly
- Testing strategy: HIGH -- pytest + FastAPI TestClient is the standard approach
- react-markdown compatibility: MEDIUM -- React 19 compatibility unverified
- Railway SSE stability: LOW -- needs production testing

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days -- stable technologies)
