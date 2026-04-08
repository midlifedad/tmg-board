# Roadmap — TMG Board Enhancements

## v1.0 Meeting Minutes Generation

### Phase 1: Meeting Minutes Generation
**Goal:** Enable chairs/admins to generate AI-powered meeting minutes from pasted transcripts, with a document template system for admin-configurable prompts, viewable and printable minutes within the meeting detail page.

**Requirements:** [M-1, M-2, M-3, M-4, M-5]
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Backend foundation: models, migration, AI service, API endpoints
- [ ] 01-02-PLAN.md — Frontend meeting minutes: modal, inline display, print support
- [ ] 01-03-PLAN.md — Admin template management UI in settings page

## Requirements
- **M-1:** Backend AI service layer using Anthropic SDK + Jinja2 templates for document generation
- **M-2:** Database-driven DocumentTemplate model so admins can configure/edit generation prompts
- **M-3:** Meeting detail page replaces "Recording" section with "Meeting Minutes" section, with a "Create Meeting Minutes" button that opens a modal for pasting transcript and generating minutes
- **M-4:** Generated minutes stored as markdown, viewable inline (similar to agenda display) and printable
- **M-5:** Admin section includes template management UI for viewing/editing document generation prompts, following existing RBAC patterns
