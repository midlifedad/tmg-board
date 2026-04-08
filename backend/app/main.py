import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, documents, meetings, decisions, ideas, webhooks, admin, agent_admin, agents, templates, transcripts, resolutions
from app.db.session import engine, Base

# Configure logging before anything else
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()


_MINUTES_GENERATOR_SYSTEM_PROMPT = """\
You are the Minutes Generator Agent for The Many Group board governance platform.

Your job is to produce structured, formal board meeting minutes from a meeting \
transcript, the agenda, and attendance data.

## Workflow

Follow these steps in order:
1. Call get_board_members to get the list of all board members and their \
canonical name spellings.
2. Call get_meeting_details to get the meeting metadata, agenda items, and \
attendance list.
3. Call get_meeting_transcript to get the full transcript text.
4. Write the minutes in markdown (see format below).
5. Call create_minutes_document with the markdown content to save it.

## How to write the minutes

Use the **agenda items as the structural outline**. Go through each agenda \
item in order and find the corresponding discussion in the transcript. For \
each item, write:

- A brief summary of the discussion (2-5 sentences)
- Any decisions that were made
- Action items: who is responsible, what they will do, and any deadline mentioned
- Motions and votes: who moved, who seconded, and the result (passed/failed/tabled)

**Name spellings**: Cross-reference names you hear in the transcript against \
the board member list from get_board_members. Use the canonical spelling from \
that list. If someone in the transcript is NOT a board member, spell their \
name as it sounds and note their role if mentioned (e.g., "guest speaker", \
"legal counsel").

## Markdown format

Write the minutes as markdown. The tool will handle conversion.

Use this structure:

# [Meeting Title]

**Date:** [date and time]
**Location:** [location or "Virtual"]

## Attendance

**Present:** [names]
**Absent:** [names]
**Also present:** [non-member attendees, if any]

## 1. [First Agenda Item Title]

[Discussion summary, decisions, action items]

## 2. [Second Agenda Item Title]

[Discussion summary, decisions, action items]

## Adjournment

Meeting adjourned at [time] by [name].

## Rules

- Formal, professional tone
- Be concise but capture all substantive points
- Do NOT include verbatim transcript quotes unless they are formal motions
- If the transcript does not cover an agenda item, note "No discussion recorded"
- Always call create_minutes_document as the final step"""

_MEETING_SETUP_SYSTEM_PROMPT = """\
You are the Meeting Setup Agent for The Many Group board governance platform.

Your job is to parse a pasted meeting description into a structured meeting \
with agenda items, then create it using the create_meeting_with_agenda tool.

When given a meeting description, extract:
1. Meeting title
2. Date and time (if mentioned) -- use ISO 8601 format (e.g., "2026-04-15T10:00:00")
3. Location or virtual meeting link (if mentioned)
4. Duration (if mentioned, otherwise estimate by summing agenda item durations \
plus 10 minutes buffer)
5. Individual agenda items with:
   - Title (concise, 3-10 words)
   - Description (additional details if provided)
   - Type: classify as one of:
     * "information" -- announcements, reports, updates
     * "discussion" -- topics needing group input
     * "decision_required" -- votes, resolutions, approvals
     * "consent_agenda" -- routine items approved as a batch \
(e.g., minutes approval)
   - Estimated duration in minutes (5 for simple, 10-15 for discussions, \
15-30 for decisions)
   - Order (sequence as listed in the description)

Rules:
- If the description mentions a vote, resolution, or approval, classify that \
item as "decision_required"
- If items are listed for review without discussion, classify as "consent_agenda"
- Default item type is "information" unless context suggests otherwise
- If the date is not specified, omit the scheduled_date field entirely \
(do NOT guess)
- If the location is not specified, omit the location field
- Always call the create_meeting_with_agenda tool with the parsed data
- After the tool call, respond with a brief summary of what you created and \
list any fields the user needs to fill in manually (e.g., "I couldn't \
determine the meeting date -- please set it manually")
- Do NOT ask follow-up questions. Parse what you can from the description and \
note what's missing."""

_RESOLUTION_WRITER_SYSTEM_PROMPT = """\
You are the Resolution Writer Agent for The Many Group board governance platform.

Your job is to draft formal board resolution documents from brief descriptions.

Follow this workflow:
1. When given a resolution description, create a decision of type=resolution \
using the create_resolution tool. Include a clear title and formal description text.
2. If asked to produce a formal document, draft an HTML resolution document \
using draft_resolution_document. The HTML should follow formal resolution format:
   - WHEREAS clauses stating the context and rationale
   - RESOLVED clauses stating the actions or decisions
   - Signature block placeholder at the bottom
3. Use list_resolutions and get_resolution to check existing resolutions when needed.

Resolution formatting rules:
- Title: "Resolution [Number]: [Subject]" format
- WHEREAS clauses: Each starts with "WHEREAS," on its own line
- RESOLVED clauses: Each starts with "NOW, THEREFORE, BE IT RESOLVED" or \
"BE IT FURTHER RESOLVED"
- Use formal, legal-style language appropriate for board governance
- Keep resolutions concise but comprehensive
- Always call create_resolution first, then optionally draft_resolution_document \
for formal HTML

HTML document formatting:
- Use <h1> for the resolution title
- Use <p> for WHEREAS and RESOLVED clauses with <strong> for the keywords
- Use <table> for signature blocks
- Include date, resolution number, and organization name in the header
- Keep styling minimal (will be rendered with print styles)"""


def _seed_agents(db):
    """Seed built-in agent configurations if none exist.

    Extracted as a standalone function so tests can call it directly
    without running the full lifespan.
    """
    from app.models.agent import AgentConfig

    if db.query(AgentConfig).count() == 0:
        seed_agents = [
            AgentConfig(
                name="Meeting Setup",
                slug="meeting-setup",
                description="Helps create structured meeting agendas from descriptions",
                system_prompt=_MEETING_SETUP_SYSTEM_PROMPT,
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.3,
                max_iterations=5,
                allowed_tool_names=[
                    "create_meeting_with_agenda",
                    "create_agenda_item",
                    "get_meeting",
                    "list_meetings",
                ],
            ),
            AgentConfig(
                name="Minutes Generator",
                slug="minutes-generator",
                description="Creates formatted meeting minutes from transcripts",
                system_prompt=_MINUTES_GENERATOR_SYSTEM_PROMPT,
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.2,
                max_iterations=5,
                allowed_tool_names=[
                    "get_board_members",
                    "get_meeting_details",
                    "get_meeting_transcript",
                    "create_minutes_document",
                ],
            ),
            AgentConfig(
                name="Resolution Writer",
                slug="resolution-writer",
                description="Drafts formal board resolution documents",
                system_prompt=_RESOLUTION_WRITER_SYSTEM_PROMPT,
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.3,
                max_iterations=3,
                allowed_tool_names=[
                    "create_resolution",
                    "draft_resolution_document",
                    "list_resolutions",
                    "get_resolution",
                ],
            ),
        ]
        for agent in seed_agents:
            db.add(agent)
        db.commit()
    else:
        # Update existing Meeting Setup agent if it still has the Phase 01 placeholder
        meeting_agent = db.query(AgentConfig).filter(
            AgentConfig.slug == "meeting-setup"
        ).first()
        if meeting_agent and "[Detailed prompt to be added in Phase 02]" in (
            meeting_agent.system_prompt or ""
        ):
            meeting_agent.system_prompt = _MEETING_SETUP_SYSTEM_PROMPT
            meeting_agent.allowed_tool_names = [
                "create_meeting_with_agenda",
                "create_agenda_item",
                "get_meeting",
                "list_meetings",
            ]
            db.commit()

        # Update existing Minutes Generator if it has an outdated prompt
        minutes_agent = db.query(AgentConfig).filter(
            AgentConfig.slug == "minutes-generator"
        ).first()
        if minutes_agent and (
            "[Detailed prompt to be added in Phase 03]" in (minutes_agent.system_prompt or "")
            or "produce structured, formal board meeting minutes in HTML" in (minutes_agent.system_prompt or "")
        ):
            minutes_agent.system_prompt = _MINUTES_GENERATOR_SYSTEM_PROMPT
            minutes_agent.max_iterations = 5
            minutes_agent.allowed_tool_names = [
                "get_board_members",
                "get_meeting_details",
                "get_meeting_transcript",
                "create_minutes_document",
            ]
            db.commit()

        # Update existing Resolution Writer if it still has the Phase 01 placeholder
        resolution_agent = db.query(AgentConfig).filter(
            AgentConfig.slug == "resolution-writer"
        ).first()
        if resolution_agent and "[Detailed prompt to be added in Phase 04]" in (
            resolution_agent.system_prompt or ""
        ):
            resolution_agent.system_prompt = _RESOLUTION_WRITER_SYSTEM_PROMPT
            resolution_agent.allowed_tool_names = [
                "create_resolution",
                "draft_resolution_document",
                "list_resolutions",
                "get_resolution",
            ]
            db.commit()


def _seed_templates(db):
    """Seed default meeting template if none exist."""
    from app.models.template import MeetingTemplate, TemplateAgendaItem
    from app.models.member import BoardMember

    if db.query(MeetingTemplate).count() == 0:
        # Use the first admin user as template creator
        admin_user = db.query(BoardMember).filter(
            BoardMember.role == "admin"
        ).first()
        if not admin_user:
            return

        template = MeetingTemplate(
            name="Board Meeting",
            description="Standard board meeting template with regulatory items",
            default_duration_minutes=65,
            default_location="Conference Room",
            created_by_id=admin_user.id,
        )
        db.add(template)
        db.flush()

        items = [
            TemplateAgendaItem(
                template_id=template.id,
                title="Call to Order",
                item_type="information",
                duration_minutes=5,
                order_index=0,
                is_regulatory=False,
            ),
            TemplateAgendaItem(
                template_id=template.id,
                title="Approval of Previous Minutes",
                item_type="consent_agenda",
                duration_minutes=5,
                order_index=1,
                is_regulatory=True,
            ),
            TemplateAgendaItem(
                template_id=template.id,
                title="Financial Report",
                item_type="information",
                duration_minutes=15,
                order_index=2,
                is_regulatory=True,
            ),
            TemplateAgendaItem(
                template_id=template.id,
                title="Old Business",
                item_type="discussion",
                duration_minutes=15,
                order_index=3,
                is_regulatory=False,
            ),
            TemplateAgendaItem(
                template_id=template.id,
                title="New Business",
                item_type="discussion",
                duration_minutes=20,
                order_index=4,
                is_regulatory=False,
            ),
            TemplateAgendaItem(
                template_id=template.id,
                title="Adjournment",
                item_type="information",
                duration_minutes=5,
                order_index=5,
                is_regulatory=False,
            ),
        ]
        for item in items:
            db.add(item)
        db.commit()


def _ensure_schema():
    """Ensure database schema matches models. Runs on every startup.

    create_all() handles new tables but can't add columns to existing tables.
    This function adds any missing columns directly, which is fast and idempotent.
    """
    from sqlalchemy import inspect, text

    _log = logging.getLogger(__name__)

    # Create any new tables
    Base.metadata.create_all(bind=engine)

    # Check for and add missing columns on existing tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Build lookup of existing columns per table
    existing_cols = {}
    for table in existing_tables:
        existing_cols[table] = {c["name"] for c in inspector.get_columns(table)}

    # Every column that migrations would add (table, column, SQL)
    required_columns = [
        ("documents", "current_version", "INTEGER DEFAULT 1"),
        ("documents", "archived_at", "TIMESTAMP"),
        ("documents", "archived_by_id", "INTEGER"),
        ("meetings", "duration_minutes", "INTEGER"),
        ("meetings", "started_at", "TIMESTAMP"),
        ("meetings", "ended_at", "TIMESTAMP"),
        ("meetings", "recording_url", "TEXT"),
        ("decisions", "visibility", "VARCHAR(20) DEFAULT 'standard'"),
        ("decisions", "updated_at", "TIMESTAMP"),
        ("decisions", "archived_at", "TIMESTAMP"),
        ("decisions", "archived_by_id", "INTEGER"),
        ("decisions", "archived_reason", "TEXT"),
        ("decisions", "resolution_number", "VARCHAR(50)"),
        ("decisions", "formal_document_id", "INTEGER"),
        ("ideas", "category_id", "INTEGER"),
        ("ideas", "status_reason", "TEXT"),
        ("comments", "parent_id", "INTEGER"),
        ("comments", "is_pinned", "BOOLEAN DEFAULT false"),
        ("comments", "edited_at", "TIMESTAMP"),
        ("audit_log", "entity_name", "VARCHAR(255)"),
        ("audit_log", "ip_address", "VARCHAR(45)"),
        ("audit_log", "user_agent", "TEXT"),
        ("agenda_items", "item_type", "VARCHAR(30) DEFAULT 'information'"),
        ("board_members", "timezone", "VARCHAR(50)"),
    ]

    added = []
    with engine.begin() as conn:
        for table, column, col_type in required_columns:
            if table in existing_tables and column not in existing_cols.get(table, set()):
                try:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    ))
                    added.append(f"{table}.{column}")
                except Exception:
                    pass  # column might already exist from a concurrent startup

    if added:
        _log.info("Added missing columns: %s", ", ".join(added))
    else:
        _log.info("Schema up to date")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    try:
        _ensure_schema()
    except Exception as e:
        logging.getLogger(__name__).error("Schema sync failed: %s", e, exc_info=True)
        # Last resort: at least create new tables
        Base.metadata.create_all(bind=engine)

    # Seed board members and permissions if empty
    from app.db.session import SessionLocal
    from app.models.member import BoardMember
    from app.models.admin import Permission, RolePermission, Setting

    db = SessionLocal()
    try:
        # Seed board members
        if db.query(BoardMember).count() == 0:
            members = [
                BoardMember(email="amir.haque@themany.com", name="Amir Haque", role="admin"),
                BoardMember(email="jens.stoelken@themany.com", name="Jens Stoelken", role="board"),
                BoardMember(email="christian.jacobsen@themany.com", name="Christian Jacobsen", role="board"),
                BoardMember(email="naser.khan@themany.com", name="Naser Khan", role="board"),
                BoardMember(email="damien.eley@themany.com", name="Damien Eley", role="shareholder"),
                BoardMember(email="scott.harris@themany.com", name="Scott Harris", role="shareholder"),
                BoardMember(email="blake.marquis@themany.com", name="Blake Marquis", role="shareholder"),
            ]
            for member in members:
                db.add(member)
            db.commit()

        # Seed permissions
        if db.query(Permission).count() == 0:
            permissions = [
                # Documents
                Permission(code="documents.view", name="View Documents", category="documents"),
                Permission(code="documents.upload", name="Upload Documents", category="documents"),
                Permission(code="documents.delete", name="Delete Documents", category="documents"),
                Permission(code="documents.sign", name="Request Signatures", category="documents"),
                # Meetings
                Permission(code="meetings.view", name="View Meetings", category="meetings"),
                Permission(code="meetings.create", name="Create Meetings", category="meetings"),
                Permission(code="meetings.edit", name="Edit Meetings", category="meetings"),
                Permission(code="meetings.delete", name="Delete Meetings", category="meetings"),
                # Decisions
                Permission(code="decisions.view", name="View Decisions", category="decisions"),
                Permission(code="decisions.create", name="Create Decisions", category="decisions"),
                Permission(code="decisions.vote", name="Cast Votes", category="decisions"),
                Permission(code="decisions.close", name="Close Voting", category="decisions"),
                # Ideas
                Permission(code="ideas.view", name="View Ideas", category="ideas"),
                Permission(code="ideas.submit", name="Submit Ideas", category="ideas"),
                Permission(code="ideas.moderate", name="Moderate Ideas", category="ideas"),
                # Admin
                Permission(code="admin.users", name="Manage Users", category="admin"),
                Permission(code="admin.settings", name="Manage Settings", category="admin"),
                Permission(code="admin.audit", name="View Audit Log", category="admin"),
            ]
            for perm in permissions:
                db.add(perm)
            db.commit()

            # Assign permissions to roles
            all_perms = db.query(Permission).all()
            perm_map = {p.code: p.id for p in all_perms}

            # Admin gets everything
            for perm_id in perm_map.values():
                db.add(RolePermission(role="admin", permission_id=perm_id))

            # Chair gets everything except admin
            chair_perms = [c for c in perm_map.keys() if not c.startswith("admin.")]
            for code in chair_perms:
                db.add(RolePermission(role="chair", permission_id=perm_map[code]))

            # Board gets same as chair (identical permissions for now)
            for code in chair_perms:
                db.add(RolePermission(role="board", permission_id=perm_map[code]))

            # Shareholder gets reports/documents view only
            shareholder_perms = ["documents.view"]
            for code in shareholder_perms:
                db.add(RolePermission(role="shareholder", permission_id=perm_map[code]))

            db.commit()

        # Seed branding settings if not present
        if not db.query(Setting).filter(Setting.key == "app_name").first():
            db.add(Setting(key="app_name", value="Board Portal"))
        if not db.query(Setting).filter(Setting.key == "organization_name").first():
            db.add(Setting(key="organization_name", value=""))
        db.commit()

        # Seed built-in agent configurations
        _seed_agents(db)

        # Seed default meeting template
        _seed_templates(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title="TMG Board API",
    description="Backend API for TMG Board Management Interface",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent 307 redirects that break POST requests
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(agent_admin.router, prefix="/api/admin", tags=["admin-agents"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(resolutions.router, prefix="/api/resolutions", tags=["resolutions"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["ideas"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(transcripts.router, prefix="/api/meetings", tags=["transcripts"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
