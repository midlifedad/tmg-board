# TMG Board

## What This Is

A board governance platform for The Many Group — enables board members to manage meetings, decisions, documents, and ideas through a dark-themed web app with gold accents. Built with Next.js 15 frontend and FastAPI backend, deployed on Railway.

## Core Value

Board members can efficiently conduct governance — schedule meetings, track decisions, manage documents, and (with v2.0) leverage AI assistants to automate repetitive board tasks like agenda creation, minutes generation, and resolution drafting.

## Current Milestone: v2.0 Agentic Layer & Board Enhancements

**Goal:** Add AI assistants that help board members with meeting prep, minutes, and resolutions — plus meeting transcript support and digital resolution signatures.

**Target features:**
- AI agent infrastructure with multi-model support (Anthropic/Gemini/Groq)
- Meeting transcript paste/upload and AI-driven minutes generation
- Board resolution section with digital signatures
- Agent management admin UI with tool shed and prompt editing
- Three built-in agents: Agenda Creator, Minutes Generator, Resolution Writer

## Requirements

### Validated

<!-- Shipped and confirmed valuable — v1.0 -->

- ✓ Dynamic org branding (logo, name, colors) — v1.0
- ✓ Meeting scheduling with agenda items, time slots, presenters — v1.0
- ✓ Inline agenda editing with drag-to-reorder — v1.0
- ✓ Decision tracking with voting (transparent/anonymous/roll_call) — v1.0
- ✓ Document management with PDF viewer — v1.0
- ✓ Idea/suggestion tracking — v1.0
- ✓ Role-based access (admin/chair/board/shareholder) — v1.0
- ✓ Google OAuth + email whitelist authentication — v1.0
- ✓ Reports page — v1.0

### Active

<!-- v2.0 scope — see REQUIREMENTS.md for formal REQ-IDs -->

- [ ] AI agent infrastructure (LiteLLM, agent loop, SSE streaming, tool system)
- [ ] Meeting transcript paste/upload
- [ ] AI-driven minutes generation from transcript
- [ ] Board resolution digital signatures
- [ ] Agent frontend (listing, chat, per-agent tool access)
- [ ] Built-in agents (Agenda Creator, Minutes Generator, Resolution Writer)
- [ ] Admin agent management (CRUD, tool shed, prompt editing, usage stats)

### Out of Scope

- Real-time collaborative editing — complexity too high for v2.0
- DocuSign/third-party e-signature integration — lightweight name+timestamp+IP signatures sufficient
- Autonomous multi-step agents — narrow-purpose tool-calling agents only
- Heavy AI frameworks (LangChain, CrewAI, LangGraph) — overkill for simple agents
- Mobile app — web-first
- Video/audio recording — transcript paste/upload instead

## Context

- **Stack:** Next.js 15 + FastAPI + PostgreSQL + SQLAlchemy 2.0 + Alembic
- **Theme:** Dark theme with gold accents, shadcn/ui components
- **Auth:** Google OAuth via NextAuth, X-User-Email header proxied to backend
- **Deployment:** Railway (auto-deploys on staging merge)
- **Existing models:** Meeting, AgendaItem, Decision, Document, BoardMember, Idea
- **Decision model** already has `type: "resolution"` — board resolutions build on this
- **Meeting model** has unused `recording_url` field — will be removed in favor of transcripts
- **Research:** Comprehensive agentic layer research at `.planning/phases/01-agent-infrastructure/01-RESEARCH.md`

## Constraints

- **Tech stack**: Must extend existing FastAPI + Next.js stack (no new frameworks)
- **Multi-model**: Must support Anthropic, Gemini, and Groq models via LiteLLM
- **Auth**: Agents must respect existing role-based permissions (tools call board REST API with user auth)
- **FastAPI version**: Needs >=0.135.0 for native SSE support
- **No new frontend AI deps**: SSE consumption via native fetch + ReadableStream (no Vercel AI SDK)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LiteLLM for multi-model | Unified API for 100+ LLMs, OpenAI-format tool calling across providers | — Pending |
| Custom agent loop (~100 lines) | Narrow-purpose agents don't need LangChain/CrewAI complexity | — Pending |
| Tools call board REST API | Preserves auth checks, validation, audit logging | — Pending |
| FastAPI native SSE (v0.135+) | Built-in EventSourceResponse, no sse-starlette dependency | — Pending |
| Lightweight digital signatures | Name + timestamp + IP, not DocuSign integration | — Pending |
| Remove recording_url | Replace with transcript paste/upload model | — Pending |

---
*Last updated: 2026-03-04 after v2.0 milestone initialization*
