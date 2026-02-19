from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, documents, meetings, decisions, ideas, webhooks, admin
from app.db.session import engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Seed board members and permissions if empty
    from app.db.session import SessionLocal
    from app.models.member import BoardMember
    from app.models.admin import Permission, RolePermission

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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
