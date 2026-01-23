from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import auth, documents, meetings, decisions, ideas, webhooks

settings = get_settings()

app = FastAPI(
    title="TMG Board API",
    description="Backend API for TMG Board Management Interface",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
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
