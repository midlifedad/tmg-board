---
phase: 01-meeting-minutes-generation
plan: 01
subsystem: backend
tags: [python, fastapi, sqlalchemy, anthropic, jinja2, alembic, pytest]
dependency_graph:
  requires: []
  provides: [meeting-minutes-api, document-template-api, document-generator-service]
  affects: [01-02-PLAN.md, 01-03-PLAN.md]
tech_stack:
  added: [anthropic>=0.40.0, pytest>=8.0.0, pytest-asyncio>=0.23.0]
  patterns: [singleton-service, tdd-red-green-refactor, jinja2-template-rendering, sqlalchemy-mapped-column, alembic-manual-migration]
key_files:
  created:
    - backend/app/models/generation.py
    - backend/app/services/document_generator.py
    - backend/app/api/generation.py
    - backend/migrations/versions/005_add_document_templates_and_meeting_minutes.py
    - backend/tests/conftest.py
    - backend/tests/test_models.py
    - backend/tests/test_document_generator.py
    - backend/tests/test_generation_api.py
    - backend/tests/__init__.py
  modified:
    - backend/requirements.txt
    - backend/app/config.py
    - backend/app/models/__init__.py
    - backend/app/main.py
decisions:
  - "Store content_markdown as DB Text column (not file-only via StorageService) for fast retrieval"
  - "Use AsyncAnthropic (not sync) per locked constraint for non-blocking FastAPI handlers"
  - "Upsert MeetingMinutes on POST: UPDATE if exists, INSERT if not (allows regeneration)"
  - "document_generator singleton is None when ANTHROPIC_API_KEY is empty (avoids 503 on import)"
  - "Jinja2 template validation on save: render with dummy context, return 400 on error"
  - "Model: claude-sonnet-4-20250514, max_tokens=4096, non-streaming"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-08"
  tasks_completed: 3
  tasks_total: 3
  files_created: 9
  files_modified: 4
  tests_passing: 14
---

# Phase 1 Plan 01: Backend Foundation — Meeting Minutes Generation Summary

**One-liner:** FastAPI backend with Anthropic AsyncAnthropic + Jinja2 DB-templating for AI meeting minutes generation, including two new SQLAlchemy models, Alembic migration with seeded default template, and 14 passing tests.

## What Was Built

Complete backend layer for AI-powered meeting minutes generation:

1. **Test Infrastructure (Wave 0):** `conftest.py` with 7 shared fixtures (in-memory SQLite, mock Anthropic client, async test client, user/meeting/template fixtures). 14 test stubs created then implemented during TDD.

2. **Models (`generation.py`):** Two SQLAlchemy models following the `mapped_column` pattern:
   - `DocumentTemplate`: Admin-configurable Jinja2 prompt templates (name, template_type, system_prompt, user_prompt_template, is_active)
   - `MeetingMinutes`: Generated minutes linked to meetings with unique constraint (one set per meeting)

3. **Migration 005:** Creates both tables, drops in reverse order on downgrade, seeds a default "Meeting Minutes" template with professional board secretary system prompt and Jinja2 user prompt template.

4. **Document Generator Service (`document_generator.py`):** Singleton following the StorageService pattern. Uses `AsyncAnthropic` (non-blocking), renders Jinja2 template with meeting context, calls `claude-sonnet-4-20250514` with 4096 max tokens. Singleton is `None` when `ANTHROPIC_API_KEY` is unset.

5. **Generation API Router (`generation.py`):** 5 endpoints:
   - `POST /api/meetings/{id}/minutes` (require_chair): validate meeting, get active template, build context, call Anthropic, upsert MeetingMinutes
   - `GET /api/meetings/{id}/minutes` (require_member): retrieve stored minutes or 404
   - `GET /api/admin/templates` (require_admin): list all templates
   - `GET /api/admin/templates/{id}` (require_admin): single template
   - `PUT /api/admin/templates/{id}` (require_admin): update with Jinja2 validation

6. **Config:** `anthropic_api_key: str = ""` added to `Settings` class.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create backend test infrastructure (Wave 0) | `8b991b2` | tests/conftest.py, 3 test stubs files |
| 2 | Models, migration, config (TDD) | `8648bfe` | models/generation.py, migration 005, config.py |
| 3 | Document generator service and API router (TDD) | `f4301b5` | services/document_generator.py, api/generation.py, main.py |

## Test Results

All 14 tests pass:
- `tests/test_models.py`: 3 tests (DocumentTemplate creation, MeetingMinutes creation, unique constraint)
- `tests/test_document_generator.py`: 3 tests (Jinja2 rendering, Anthropic call, return value)
- `tests/test_generation_api.py`: 8 tests (auth, generate, get, 404, admin templates CRUD, Jinja2 validation)

## Deviations from Plan

None — plan executed exactly as written. The TDD RED-GREEN cycle was followed for Tasks 2 and 3.

## Key Decisions Made

- **DB storage over file storage:** `content_markdown` stored as Text column in `meeting_minutes` table rather than exclusively via StorageService. Avoids async file I/O on every page load.
- **Non-streaming Anthropic calls:** Simpler implementation; streaming can be added later if minutes generation exceeds 15 seconds.
- **Singleton-is-None pattern:** `document_generator = None` when API key is empty prevents import-time crash while giving clear 503 error at request time.
- **Jinja2 validation on save:** Template is rendered with a dummy context on PUT — returns 400 on both syntax and runtime errors.

## What Downstream Plans Depend On

- **01-02-PLAN.md (Frontend minutes):** Needs `POST /api/meetings/{id}/minutes` and `GET /api/meetings/{id}/minutes` endpoints — both exist.
- **01-03-PLAN.md (Admin template UI):** Needs `GET/PUT /api/admin/templates` endpoints — both exist.

## Self-Check: PASSED

All 9 created files confirmed present on disk.
All 3 task commits confirmed in git log (8b991b2, 8648bfe, f4301b5).
14/14 tests pass per `pytest tests/ -v`.
