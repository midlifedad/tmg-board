from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, documents, meetings, decisions, ideas, webhooks
from app.db.session import engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Seed board members if empty
    from app.db.session import SessionLocal
    from app.models.member import BoardMember

    db = SessionLocal()
    try:
        if db.query(BoardMember).count() == 0:
            # Seed initial board members
            members = [
                BoardMember(email="admin@themany.com", name="Admin User", role="admin"),
                BoardMember(email="chair@themany.com", name="Board Chair", role="chair"),
                BoardMember(email="member1@themany.com", name="Board Member 1", role="member"),
                BoardMember(email="member2@themany.com", name="Board Member 2", role="member"),
                BoardMember(email="member3@themany.com", name="Board Member 3", role="member"),
            ]
            for member in members:
                db.add(member)
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
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["decisions"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["ideas"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
