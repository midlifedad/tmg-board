from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, documents, meetings, decisions, ideas, webhooks, admin, agents
from app.db.session import engine, Base

settings = get_settings()


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
                system_prompt=(
                    "You are a meeting setup assistant for The Many Group board. "
                    "You help create structured meeting agendas from descriptions. "
                    "[Detailed prompt to be added in Phase 02]"
                ),
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.3,
                max_iterations=5,
                allowed_tool_names=["create_agenda_item", "get_meeting", "list_members"],
            ),
            AgentConfig(
                name="Minutes Generator",
                slug="minutes-generator",
                description="Creates formatted meeting minutes from transcripts",
                system_prompt=(
                    "You are a minutes generator for The Many Group board. "
                    "You create formatted meeting minutes from transcripts. "
                    "[Detailed prompt to be added in Phase 03]"
                ),
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.2,
                max_iterations=3,
                allowed_tool_names=["get_meeting", "get_agenda", "get_attendance"],
            ),
            AgentConfig(
                name="Resolution Writer",
                slug="resolution-writer",
                description="Drafts formal board resolution documents",
                system_prompt=(
                    "You are a resolution writer for The Many Group board. "
                    "You draft formal board resolution documents. "
                    "[Detailed prompt to be added in Phase 04]"
                ),
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.3,
                max_iterations=3,
                allowed_tool_names=["create_resolution", "get_decision"],
            ),
        ]
        for agent in seed_agents:
            db.add(agent)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    # Create all tables
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
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["ideas"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
