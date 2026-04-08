---
phase: 01
slug: meeting-minutes-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) / manual verification (frontend) |
| **Config file** | backend/tests/conftest.py (to be created) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | M-1, M-2 | unit | `pytest tests/unit/test_document_generator.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | M-2 | unit | `pytest tests/unit/test_template_model.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | M-3 | manual | Browser: navigate to meeting detail, verify modal | N/A | ⬜ pending |
| 01-03-01 | 03 | 2 | M-4 | manual | Browser: verify inline minutes render and print | N/A | ⬜ pending |
| 01-04-01 | 04 | 2 | M-5 | manual | Browser: admin settings > templates tab | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures (test DB, mock Anthropic client)
- [ ] `backend/tests/unit/test_document_generator.py` — stubs for M-1
- [ ] `backend/tests/unit/test_template_model.py` — stubs for M-2
- [ ] `pip install pytest pytest-asyncio` — test framework

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal opens from meeting detail | M-3 | UI interaction | Click "Create Meeting Minutes" on completed meeting |
| Minutes render inline as formatted markdown | M-4 | Visual verification | Generate minutes, verify rendered output |
| Minutes are printable | M-4 | Print CSS | Use browser print preview on minutes view |
| Admin template editor saves/loads | M-5 | UI interaction | Navigate to admin settings > templates, edit and save |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
