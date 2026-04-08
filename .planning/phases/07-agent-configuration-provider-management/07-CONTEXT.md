# Phase 07: Agent Configuration & Provider Management — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning
**Source:** Comprehensive audit of agent admin system, minutes flow, and frontend UI

<domain>
## Phase Boundary

This phase fixes the agent configuration UX so admins can actually use the AI features: adds API key management UI, consolidates the hardcoded model list, makes the model dropdown provider-aware, fixes the has_minutes false positive bug, fixes minutes display XSS, and removes Gemini as a provider (only Anthropic and Groq are used).

</domain>

<decisions>
## Implementation Decisions

### API Key Management UI
- Add an "API Keys" section to the existing Admin Agents page (NOT a separate page)
- Show a card per provider (Anthropic, Groq) with: status indicator, masked key preview, input field to update
- Use existing backend endpoints: `GET /api/agents/api-keys` and `PUT /api/agents/api-keys`
- Add `adminApi.getApiKeys()` and `adminApi.updateApiKeys()` functions to `frontend/src/lib/api.ts`

### Remove Gemini Provider
- Remove `gemini` entry from `PROVIDER_KEY_MAP` in `backend/app/services/llm_provider.py`
- Remove Gemini models from the model list
- Remove `gemini_api_key` from the PUT endpoint schema (keep GET backward-compatible, just won't show gemini)
- Update seed agents if any use Gemini models (they don't — all use Anthropic)

### Consolidate Model List
- Create `frontend/src/lib/models.ts` with a single `SUPPORTED_MODELS` array
- Each entry: `{ value: string, label: string, provider: string }`
- Import from this shared file in `create-agent-modal.tsx`, `edit-agent-modal.tsx`, and `admin/agents/page.tsx`
- Remove the 3 duplicate `SUPPORTED_MODELS` / `MODEL_LABELS` definitions

### Provider-Aware Model Dropdown
- Add a backend endpoint: `GET /api/agents/available-models` — returns models filtered to providers that have keys configured
- Frontend model dropdown fetches from this endpoint instead of using the hardcoded list
- If a provider has no key, its models don't appear in the dropdown
- Show a warning if zero models are available ("Configure API keys first")

### Fix has_minutes Bug
- In `backend/app/api/meetings.py` line 158: change `"has_minutes": meeting.status == "completed"` to actually query the `MeetingDocument` table for `relationship_type == "minutes"`
- Use a subquery or join to avoid N+1 queries on the list endpoint

### Fix Minutes Display XSS
- In `frontend/src/app/meetings/[id]/page.tsx` line 929: replace `dangerouslySetInnerHTML={{ __html: minutes.html_content }}` with a safe rendering approach
- Use DOMPurify to sanitize the HTML before rendering (minutes are HTML, not markdown, so ReactMarkdown won't work here)
- Install `dompurify` and `@types/dompurify` packages

### Architecture Alignment
- Work within existing patterns: LiteLLM provider format (`provider/model`), settings table for keys, admin API for CRUD
- Do NOT add new database tables — use existing `settings` table for keys
- Do NOT change the agent runner or tool system — only the configuration UI and model discovery

</decisions>

<specifics>
## Specific Details

### Current Model List (hardcoded in 3 places)
```typescript
// In create-agent-modal.tsx, edit-agent-modal.tsx, admin/agents/page.tsx
"anthropic/claude-sonnet-4-5-20250929": "Claude Sonnet 4.5"
"anthropic/claude-haiku-3-5-20241022": "Claude Haiku 3.5"
"gemini/gemini-2.0-flash": "Gemini 2.0 Flash"        // REMOVE
"gemini/gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite" // REMOVE
"groq/llama-3.3-70b-versatile": "Llama 3.3 70B"
"groq/llama-3.1-8b-instant": "Llama 3.1 8B (Fast)"
```

### Backend API Key Endpoints (existing, working)
- `GET /api/agents/api-keys` — returns `{ providers: [{ name, configured, source, masked_value }] }`
- `PUT /api/agents/api-keys` — accepts `{ anthropic_api_key?, groq_api_key? }`
- Both require admin role

### Provider Key Map (backend/app/services/llm_provider.py)
```python
PROVIDER_KEY_MAP = {
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "gemini": ("gemini_api_key", "GEMINI_API_KEY"),      # REMOVE
    "groq": ("groq_api_key", "GROQ_API_KEY"),
}
```

### has_minutes Bug Location
`backend/app/api/meetings.py` line 158:
```python
"has_minutes": meeting.status == "completed",  # BUG: should check MeetingDocument table
```

### Minutes XSS Location
`frontend/src/app/meetings/[id]/page.tsx` line 929:
```tsx
dangerouslySetInnerHTML={{ __html: minutes.html_content }}
```

</specifics>

<deferred>
## Deferred

- API key encryption at rest (keys stored as plaintext in settings table)
- Rate limiting on agent endpoints
- Cost calculation for usage tracking (currently always $0.00)
- Dynamic model discovery from LiteLLM API
- Agent reactivation UI button
- Agent testing/preview from admin page
</deferred>
