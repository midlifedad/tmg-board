from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunAgentRequest(BaseModel):
    """Request to invoke an agent."""
    agent_slug: str
    message: str
    context: Optional[dict] = None


class AgentConfigResponse(BaseModel):
    """Response schema for a single agent configuration."""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    model: str
    is_active: bool
    allowed_tool_names: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Response schema for listing agents."""
    agents: list[AgentConfigResponse]
