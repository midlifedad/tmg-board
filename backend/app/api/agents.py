"""Agent API endpoints (placeholder - full implementation in Plan 03)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_agents():
    """List all active agents. Placeholder - will be fully implemented in Plan 03."""
    return {"agents": []}
