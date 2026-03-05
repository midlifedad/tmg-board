# Requirements: TMG Board

**Defined:** 2026-03-04
**Core Value:** Board members can efficiently conduct governance and leverage AI assistants embedded in their workflow

## v2.0 Requirements

Requirements for the Agentic Board Tools milestone. Each maps to roadmap phases.

### Agent Infrastructure

- [x] **AGENT-01**: System can route user requests to configured agents with system prompt, model, and allowed tools
- [x] **AGENT-02**: Agent tools call the board's own REST API with the user's auth context (preserving permissions)
- [x] **AGENT-03**: Agent responses stream to the frontend via SSE
- [x] **AGENT-04**: System supports multiple LLM providers (Anthropic, Gemini, Groq) via LiteLLM

### Meeting Creation & Templates

- [x] **MEET-01**: User can create a meeting by selecting a date and pasting a full description that the agent parses into structured agenda
- [x] **MEET-02**: User can alternatively fill in meeting details manually (as today, but improved UX)
- [x] **MEET-03**: Admin can create meeting templates with standard agenda items
- [x] **MEET-04**: User can apply a template when creating a meeting, then customize
- [x] **MEET-05**: Meeting templates can include required regulatory items (manual configuration for now)

### Meeting Transcripts & Minutes

- [ ] **TRANS-01**: Chair/admin can paste transcript text for a completed meeting
- [ ] **TRANS-02**: Chair/admin can upload a transcript file (.txt) for a meeting
- [ ] **TRANS-03**: Any board member can view a meeting's transcript
- [ ] **TRANS-04**: Minutes Generator agent can produce minutes document from a transcript
- [ ] **TRANS-05**: Recording URL field is removed from meetings model

### Board Resolutions & Signatures

- [ ] **RES-01**: Board resolutions appear as a dedicated section (building on existing decisions with type=resolution)
- [ ] **RES-02**: Board members can digitally sign a resolution (name + timestamp + IP)
- [ ] **RES-03**: Resolution shows signature status (who signed, who hasn't)
- [ ] **RES-04**: Chair/admin can view and export signed resolutions

### Embedded Agent UX

- [x] **UX-01**: Meeting creation page has an expandable section where user can paste a description for agent-assisted setup
- [x] **UX-02**: Agent responses appear inline on the page they're triggered from (not a separate chat UI)
- [x] **UX-03**: User sees streaming agent output with tool call indicators
- [x] **UX-04**: Agent actions (create agenda items, generate minutes, draft resolution) apply directly to the current context

### Built-in Agents

- [x] **BUILT-01**: Meeting Setup agent can parse a pasted description into structured meeting with agenda items
- [ ] **BUILT-02**: Minutes Generator agent can create minutes document from meeting transcript
- [ ] **BUILT-03**: Resolution Writer agent can draft resolution documents and link them to decisions

### Admin Agent Management

- [ ] **ADMIN-01**: Admin can create, edit, and delete agent configurations (under Admin section)
- [ ] **ADMIN-02**: Admin can assign/remove tools from an agent's allowed tool list
- [ ] **ADMIN-03**: Admin can edit an agent's system prompt and select its model
- [ ] **ADMIN-04**: Admin can view agent usage statistics (calls, tokens, cost)

## v2.1 Requirements

Deferred to next milestone. Needs domain research first.

### Compliance & Governance

- **COMP-01**: System stores jurisdiction-specific governance requirements (country/state/province)
- **COMP-02**: Compliance rules define required board activities by frequency (quarterly/annual/monthly)
- **COMP-03**: Dashboard shows compliance status — what's been done, what's due, what's overdue
- **COMP-04**: Compliance agent advises on upcoming requirements and flags gaps
- **COMP-05**: Multi-company support with per-company jurisdiction configuration

## Out of Scope

| Feature | Reason |
|---------|--------|
| Standalone agent chat UI | Agents are embedded in existing pages, not a separate interface |
| DocuSign / third-party e-signatures | Lightweight name+timestamp+IP sufficient for v2.0 |
| Heavy AI frameworks (LangChain, CrewAI) | Overkill for narrow-purpose agents |
| Autonomous multi-step agents | Simple tool-calling agents only |
| Real-time collaborative editing | Too complex for v2.0 |
| Compliance rules engine | Deferred to v2.1 (needs jurisdiction research) |
| Multi-company support | Deferred to v2.1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGENT-01 | Phase 01 | Complete |
| AGENT-02 | Phase 01 | Complete |
| AGENT-03 | Phase 01 | Complete |
| AGENT-04 | Phase 01 | Complete |
| UX-02 | Phase 01 | Complete |
| UX-03 | Phase 01 | Complete |
| UX-04 | Phase 01 | Complete |
| MEET-01 | Phase 02 | Complete |
| MEET-02 | Phase 02 | Complete |
| MEET-03 | Phase 02 | Complete |
| MEET-04 | Phase 02 | Complete |
| MEET-05 | Phase 02 | Complete |
| UX-01 | Phase 02 | Complete |
| BUILT-01 | Phase 02 | Complete |
| TRANS-01 | Phase 03 | Pending |
| TRANS-02 | Phase 03 | Pending |
| TRANS-03 | Phase 03 | Pending |
| TRANS-04 | Phase 03 | Pending |
| TRANS-05 | Phase 03 | Pending |
| BUILT-02 | Phase 03 | Pending |
| RES-01 | Phase 04 | Pending |
| RES-02 | Phase 04 | Pending |
| RES-03 | Phase 04 | Pending |
| RES-04 | Phase 04 | Pending |
| BUILT-03 | Phase 04 | Pending |
| ADMIN-01 | Phase 05 | Pending |
| ADMIN-02 | Phase 05 | Pending |
| ADMIN-03 | Phase 05 | Pending |
| ADMIN-04 | Phase 05 | Pending |

**Coverage:**
- v2.0 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-05 — MEET-03, MEET-04, MEET-05 completed (02-01)*
