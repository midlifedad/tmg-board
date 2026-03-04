# Roadmap: TMG Board

## Overview

v2.0 adds an agentic layer to the existing TMG Board governance platform. Phase 01 builds the AI engine — LiteLLM multi-model support, a lightweight agent loop, SSE streaming, and the embedded UX patterns. Phase 02 overhauled meeting creation with paste-to-populate and the Meeting Setup agent. Phase 03 adds transcript management and the Minutes Generator. Phase 04 adds board resolution digital signatures and the Resolution Writer agent. Phase 05 gives admins full control over agent configuration under the existing Admin section.

## Milestones

- ✅ **v1.0 Meetings UX Redesign** — Phases pre-01 (shipped 2026-03-04, outside GSD)
- 🚧 **v2.0 Agentic Layer & Board Enhancements** — Phases 01–05 (in progress)

## Phases

### v2.0 Agentic Layer & Board Enhancements

- [ ] **Phase 01: Agent Infrastructure & Streaming UX** - Build the AI engine: LiteLLM, agent loop, SSE streaming, and embedded response UI patterns
- [ ] **Phase 02: Meeting Creation Overhaul & Meeting Setup Agent** - Rework meeting creation with paste-to-populate and templates, powered by the first built-in agent
- [ ] **Phase 03: Transcripts & Minutes Generator** - Transcript paste/upload for completed meetings and AI-driven minutes generation
- [ ] **Phase 04: Board Resolutions & Resolution Writer** - Digital signature workflow and AI-assisted resolution drafting
- [ ] **Phase 05: Admin Agent Management** - CRUD, tool assignment, prompt editing, and usage stats under the Admin section

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
**Plans:** 4 plans
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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

### Phase 05: Admin Agent Management
**Goal**: Admins can create, configure, and monitor all board agents from within the existing Admin section without touching code or deployments
**Depends on**: Phase 01
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04
**Success Criteria** (what must be TRUE):
  1. Admin can create a new agent configuration with a name, system prompt, model selection, and tool list from the Admin section
  2. Admin can edit an existing agent's system prompt and change its model without a deployment
  3. Admin can add or remove tools from an agent's allowed tool list
  4. Admin can view a usage dashboard showing call counts, token usage, and estimated cost per agent
**Plans**: TBD

## Progress

**Execution Order:** 01 → 02 → 03 → 04 → 05

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 01. Agent Infrastructure & Streaming UX | 1/4 | In progress | - |
| 02. Meeting Creation Overhaul & Meeting Setup Agent | 0/TBD | Not started | - |
| 03. Transcripts & Minutes Generator | 0/TBD | Not started | - |
| 04. Board Resolutions & Resolution Writer | 0/TBD | Not started | - |
| 05. Admin Agent Management | 0/TBD | Not started | - |
