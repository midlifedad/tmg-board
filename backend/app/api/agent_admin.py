"""Admin API endpoints for agent configuration management, tool listing, and usage stats."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.audit import AuditLog
from app.models.member import BoardMember
from app.api.auth import require_admin

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model: str
    max_iterations: int = 5
    temperature: float = 0.3
    allowed_tool_names: List[str] = []


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    allowed_tool_names: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AgentAdminResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    system_prompt: str
    model: str
    max_iterations: int
    temperature: float
    allowed_tool_names: Optional[list]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return slug


# =============================================================================
# Static endpoints (MUST be defined BEFORE /{agent_id} routes)
# =============================================================================


@router.get("/agents/tools")
async def list_available_tools(
    current_user: BoardMember = Depends(require_admin),
):
    """Return all registered tools from the tool registry."""
    from app.tools import TOOL_REGISTRY

    return [
        {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameter_count": len(tool.parameters_schema.get("properties", {})),
        }
        for tool in TOOL_REGISTRY.values()
    ]


@router.get("/agents/usage")
async def get_usage_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Aggregate usage stats per agent."""
    query = db.query(
        AgentUsageLog.agent_id,
        AgentConfig.name.label("agent_name"),
        func.count(AgentUsageLog.id).label("total_calls"),
        func.sum(AgentUsageLog.prompt_tokens).label("total_prompt_tokens"),
        func.sum(AgentUsageLog.completion_tokens).label("total_completion_tokens"),
        func.sum(AgentUsageLog.total_cost_usd).label("total_cost_usd"),
        func.avg(AgentUsageLog.duration_ms).label("avg_duration_ms"),
    ).join(AgentConfig, AgentUsageLog.agent_id == AgentConfig.id).group_by(
        AgentUsageLog.agent_id, AgentConfig.name
    )

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AgentUsageLog.created_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AgentUsageLog.created_at <= end_dt)
        except ValueError:
            pass

    rows = query.all()
    return [
        {
            "agent_id": row.agent_id,
            "agent_name": row.agent_name,
            "total_calls": row.total_calls,
            "total_prompt_tokens": row.total_prompt_tokens,
            "total_completion_tokens": row.total_completion_tokens,
            "total_cost_usd": float(row.total_cost_usd) if row.total_cost_usd else 0.0,
            "avg_duration_ms": float(row.avg_duration_ms) if row.avg_duration_ms else 0.0,
        }
        for row in rows
    ]


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.get("/agents")
async def list_agents(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """List agent configurations. Filters to active-only by default."""
    query = db.query(AgentConfig)
    if not include_inactive:
        query = query.filter(AgentConfig.is_active == True)  # noqa: E712
    agents = query.order_by(AgentConfig.name).all()

    # Serialize manually to ensure datetime fields are ISO strings
    return [
        {
            "id": a.id,
            "name": a.name,
            "slug": a.slug,
            "description": a.description,
            "system_prompt": a.system_prompt,
            "model": a.model,
            "max_iterations": a.max_iterations,
            "temperature": a.temperature,
            "allowed_tool_names": a.allowed_tool_names or [],
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }
        for a in agents
    ]


@router.post("/agents")
async def create_agent(
    request: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Create a new agent configuration."""
    slug = _generate_slug(request.name)

    # Check for duplicate name or slug
    existing = db.query(AgentConfig).filter(
        (AgentConfig.name == request.name) | (AgentConfig.slug == slug)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this name already exists")

    agent = AgentConfig(
        name=request.name,
        slug=slug,
        description=request.description,
        system_prompt=request.system_prompt,
        model=request.model,
        temperature=request.temperature,
        max_iterations=request.max_iterations,
        allowed_tool_names=request.allowed_tool_names or [],
        is_active=True,
    )
    db.add(agent)
    db.flush()  # Get the ID before creating audit log

    db.add(AuditLog(
        entity_type="agent",
        entity_id=agent.id,
        entity_name=request.name,
        action="create",
        changed_by_id=current_user.id,
    ))
    db.commit()
    db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "max_iterations": agent.max_iterations,
        "temperature": agent.temperature,
        "allowed_tool_names": agent.allowed_tool_names or [],
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Get a single agent configuration by ID."""
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent.id,
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "max_iterations": agent.max_iterations,
        "temperature": agent.temperature,
        "allowed_tool_names": agent.allowed_tool_names or [],
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.patch("/agents/{agent_id}")
async def update_agent(
    agent_id: int,
    request: UpdateAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Partial update of an agent configuration."""
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = request.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If name changes, regenerate slug and check uniqueness
    if "name" in update_data:
        new_slug = _generate_slug(update_data["name"])
        existing = db.query(AgentConfig).filter(
            AgentConfig.slug == new_slug,
            AgentConfig.id != agent_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Agent with this name already exists")
        update_data["slug"] = new_slug

    # Build changes dict for audit log
    changes = {}
    for field, new_value in update_data.items():
        if field == "slug":
            continue  # slug is derived from name, no need to log separately
        old_value = getattr(agent, field, None)
        if old_value != new_value:
            # Truncate system_prompt in audit log to avoid huge entries
            if field == "system_prompt":
                old_display = (old_value[:100] + "...") if old_value and len(old_value) > 100 else old_value
                new_display = (new_value[:100] + "...") if new_value and len(new_value) > 100 else new_value
                changes[field] = {"old": old_display, "new": new_display}
            else:
                changes[field] = {"old": old_value, "new": new_value}

    # Apply updates
    for field, value in update_data.items():
        setattr(agent, field, value)

    if changes:
        db.add(AuditLog(
            entity_type="agent",
            entity_id=agent_id,
            entity_name=agent.name,
            action="update",
            changed_by_id=current_user.id,
            changes=changes,
        ))

    db.commit()
    db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "max_iterations": agent.max_iterations,
        "temperature": agent.temperature,
        "allowed_tool_names": agent.allowed_tool_names or [],
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Soft delete an agent (set is_active=False)."""
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_active = False

    db.add(AuditLog(
        entity_type="agent",
        entity_id=agent_id,
        entity_name=agent.name,
        action="delete",
        changed_by_id=current_user.id,
    ))
    db.commit()

    return {"status": "deactivated", "id": agent_id}
