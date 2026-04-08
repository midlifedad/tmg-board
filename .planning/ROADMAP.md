# Roadmap: TMG Board

## Overview

v2.0 adds an agentic layer to the existing TMG Board governance platform. Phase 01 builds the AI engine — LiteLLM multi-model support, a lightweight agent loop, SSE streaming, and the embedded UX patterns. Phase 02 overhauled meeting creation with paste-to-populate and the Meeting Setup agent. Phase 03 adds transcript management and the Minutes Generator. Phase 04 adds board resolution digital signatures and the Resolution Writer agent. Phase 05 gives admins full control over agent configuration under the existing Admin section.

## Milestones

- ✅ **v1.0 Meetings UX Redesign** — Phases pre-01 (shipped 2026-03-04, outside GSD)
- ✅ **v2.0 Agentic Layer & Board Enhancements** — Phases 01-05 (completed 2026-03-05)
- ✅ **v2.1 Stability & Quality** — Phases 06-07 (completed 2026-04-08)

## Phases

### v2.0 Agentic Layer & Board Enhancements

- [x] **Phase 01: Agent Infrastructure & Streaming UX** - Build the AI engine: LiteLLM, agent loop, SSE streaming, and embedded response UI patterns (completed 2026-03-05)
- [x] **Phase 02: Meeting Creation Overhaul & Meeting Setup Agent** - Rework meeting creation with paste-to-populate and templates, powered by the first built-in agent (completed 2026-03-05)
- [x] **Phase 03: Transcripts & Minutes Generator** - Transcript paste/upload for completed meetings and AI-driven minutes generation (completed 2026-03-05)
- [x] **Phase 04: Board Resolutions & Resolution Writer** - Digital signature workflow and AI-assisted resolution drafting (completed 2026-03-05)
- [x] **Phase 05: Admin Agent Management** - CRUD, tool assignment, prompt editing, and usage stats under the Admin section (completed 2026-03-05)

## Phase Details

### Phase 01: Agent Infrastructure & Streaming UX
**Goal**: Board members can invoke AI agents that stream responses inline on existing pages, with tool call indicators, using any configured LLM provider
**Depends on**: Nothing (first phase)
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, UX-02, UX-03, UX-04
**Success Criteria** (what must be TRUE):
  1. A user can trigger an agent from a board page and see the response appear inline on that same page (no redirect, no separate chat UI)
  2. The response streams in real time — text appears progressively as the agent generates it
  3. When the agent calls a tool, the UI shows which tool is executing and the result inline
  4. The same agent invocation works when the underlying model is swapped to Anthropic, Gemini, or Groq without frontend changes
  5. Tool actions performed by the agent (e.g., creating an agenda item) take effect in the live app and respect the invoking user's role permissions
**Plans:** 4/4 plans complete
Plans:
- [x] 01-01-PLAN.md — Backend foundation: models, schemas, dependencies, config, test infrastructure, seed data
- [ ] 01-02-PLAN.md — Agent runner service: LiteLLM integration, tool registry, tool implementations, agent loop
- [ ] 01-03-PLAN.md — SSE streaming: FastAPI endpoint, proxy fix, SSE event protocol, integration tests
- [ ] 01-04-PLAN.md — Frontend: useAgentStream hook, AgentResponsePanel, ToolCallIndicator, visual checkpoint

### Phase 02: Meeting Creation Overhaul & Meeting Setup Agent
**Goal**: Users can create meetings by pasting a description for agent-assisted population or filling fields manually, and admins can define reusable templates with regulatory items
**Depends on**: Phase 01
**Requirements**: MEET-01, MEET-02, MEET-03, MEET-04, MEET-05, UX-01, BUILT-01
**Success Criteria** (what must be TRUE):
  1. User can paste a full meeting description into an expandable section on the meeting creation page and the Meeting Setup agent parses it into a structured meeting with agenda items
  2. User can still create meetings manually by filling fields (the existing flow, improved)
  3. Admin can create a meeting template with standard agenda items, including flagged regulatory items
  4. User can select a template when creating a meeting and then customize the pre-populated agenda
**Plans:** 3/3 plans complete
Plans:
- [x] 02-01-PLAN.md — Backend: Template models, migration, template CRUD API, batch meeting creation endpoint
- [x] 02-02-PLAN.md — Meeting Setup Agent: Production system prompt, create_meeting_with_agenda tool
- [x] 02-03-PLAN.md — Frontend: Meeting creation page overhaul, AI-assisted section, template selector, admin templates page

### Phase 03: Transcripts & Minutes Generator
**Goal**: Chairs and admins can attach transcripts to completed meetings and generate formatted minutes documents from them using AI
**Depends on**: Phase 01
**Requirements**: TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05
**Success Criteria** (what must be TRUE):
  1. Chair or admin can paste transcript text directly into a completed meeting's detail page
  2. Chair or admin can upload a .txt transcript file for a meeting
  3. Any board member can view the stored transcript for a meeting they have access to
  4. Minutes Generator agent produces a formatted minutes document from the meeting's transcript, visible inline on the meeting page
  5. The recording URL field is absent from all meeting forms and views (removed, not just hidden)
**Plans:** 3/3 plans complete
Plans:
- [x] 03-01-PLAN.md — Backend: MeetingTranscript/MeetingDocument models, migration, transcript CRUD API, recording_url removal
- [x] 03-02-PLAN.md — Minutes Generator Agent: Production system prompt, agent tools, seed data update
- [x] 03-03-PLAN.md — Frontend: Transcript section, minutes generator button, recording card removal

### Phase 04: Board Resolutions & Resolution Writer
**Goal**: Board members can view and digitally sign resolutions, chairs and admins can export signed resolutions, and the Resolution Writer agent can draft resolution documents
**Depends on**: Phase 01
**Requirements**: RES-01, RES-02, RES-03, RES-04, BUILT-03
**Success Criteria** (what must be TRUE):
  1. A dedicated Resolutions section surfaces decisions typed as resolution, separate from general decisions
  2. Any board member can affix a digital signature (name, timestamp, IP recorded) to a resolution
  3. Resolution detail shows a signature status panel: who has signed and who has not
  4. Chair or admin can export a signed resolution (PDF or printable view)
  5. Resolution Writer agent drafts a resolution document from a brief description and links it to the relevant decision
**Plans:** 3/3 plans complete
Plans:
- [x] 04-01-PLAN.md — Backend: ResolutionSignature model, migration, schemas, resolutions API with sign/signatures endpoints, tests
- [x] 04-02-PLAN.md — Resolution Writer Agent: Production system prompt, four agent tools, seed data upgrade
- [x] 04-03-PLAN.md — Frontend: Sidebar entry, resolutions list/detail pages, signature panel, print export, Resolution Writer component

### Phase 05: Admin Agent Management
**Goal**: Admins can create, configure, and monitor all board agents from within the existing Admin section without touching code or deployments
**Depends on**: Phase 01
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04
**Success Criteria** (what must be TRUE):
  1. Admin can create a new agent configuration with a name, system prompt, model selection, and tool list from the Admin section
  2. Admin can edit an existing agent's system prompt and change its model without a deployment
  3. Admin can add or remove tools from an agent's allowed tool list
  4. Admin can view a usage dashboard showing call counts, token usage, and estimated cost per agent
**Plans:** 2/2 plans complete
Plans:
- [x] 05-01-PLAN.md — Backend: Agent admin API (CRUD, tool list, usage stats endpoints) with tests
- [x] 05-02-PLAN.md — Frontend: Admin agents page, create/edit modals, tool assignment, usage tab, sidebar entry

### v2.1 Stability & Quality

- [x] **Phase 06: Bug Fixes, Minutes Persistence & Test Coverage** - Fix critical bugs from code review, add missing minutes persistence endpoint, print CSS, and comprehensive test coverage (completed 2026-04-08)
- [x] **Phase 07: Agent Configuration & Provider Management** - Add API key management UI, consolidate model list, fix has_minutes bug, fix minutes XSS, remove Gemini provider (completed 2026-04-08)

## Phase Details (v2.1)

### Phase 06: Bug Fixes, Minutes Persistence & Test Coverage
**Goal**: Fix 4 critical bugs (route conflict, XSS, auth leak, minutes not persisting), add print support for meeting minutes, and bring test coverage from ~35% to ~60%+
**Depends on**: v2.0 complete
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Admin can access GET /api/agents/api-keys without 404 (route conflict fixed)
  2. Resolution detail page renders content safely via ReactMarkdown (no XSS)
  3. Unauthenticated users do not see admin UI on meetings/decisions pages
  4. Minutes Generator agent successfully persists generated minutes to the database
  5. Meeting detail page displays previously generated minutes and supports printing
  6. All tests pass with 120+ total test functions covering core domain
**Plans:** 2/2 plans complete
Plans:
- [x] 06-01-PLAN.md — Bug fixes (route conflict, XSS, auth leak) + minutes persistence endpoints + print CSS
- [x] 06-02-PLAN.md — Comprehensive test coverage: meetings CRUD, minutes, auth, agent API keys, tool handlers

### Phase 07: Agent Configuration & Provider Management
**Goal**: Admin can manage LLM API keys through the UI, model list is dynamic based on configured providers, has_minutes bug fixed, minutes XSS fixed, Gemini removed
**Depends on**: Phase 06
**Requirements**: AGCFG-01, AGCFG-02, AGCFG-03, AGCFG-04, AGCFG-05, AGCFG-06, AGCFG-07
**Success Criteria** (what must be TRUE):
  1. Admin can enter/update Anthropic and Groq API keys from the Admin Agents page
  2. API key status section shows configured/not configured with masked key preview per provider
  3. Agent model dropdown only shows models for providers that have keys configured
  4. Model list defined once in a shared constants file (not duplicated)
  5. Meetings list page shows "Minutes Available" badge only for meetings that actually have minutes
  6. Meeting detail minutes card renders HTML safely (no dangerouslySetInnerHTML)
  7. Gemini models and provider removed from the model list and provider map
**Plans:** 2 plans
Plans:
- [x] 07-01-PLAN.md — Backend: remove Gemini provider, fix has_minutes, add available-models endpoint
- [x] 07-02-PLAN.md — Frontend: API key management UI, consolidated model list, provider-aware dropdowns, minutes XSS fix

## Progress

**Execution Order:** 01 → 02 → 03 → 04 → 05 → 06 → 07

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 01. Agent Infrastructure & Streaming UX | 4/4 | Complete    | 2026-03-05 |
| 02. Meeting Creation Overhaul & Meeting Setup Agent | 3/3 | Complete    | 2026-03-05 |
| 03. Transcripts & Minutes Generator | 3/3 | Complete    | 2026-03-05 |
| 04. Board Resolutions & Resolution Writer | 3/3 | Complete    | 2026-03-05 |
| 05. Admin Agent Management | 2/2 | Complete    | 2026-03-05 |
| 06. Bug Fixes, Minutes Persistence & Tests | 2/2 | Complete    | 2026-04-08 |
| 07. Agent Configuration & Provider Mgmt | 2/2 | Complete    | 2026-04-08 |
