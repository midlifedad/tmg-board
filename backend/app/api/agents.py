"""Agent API endpoints -- list, detail, SSE streaming run, and API key management."""
from __future__ import annotations

import json
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.db import get_db
from app.api.auth import require_member, require_admin
from app.models.admin import Setting
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.member import BoardMember
from app.schemas.agent import RunAgentRequest, AgentConfigResponse, AgentListResponse
from app.services.agent_runner import run_agent_streaming
from app.services.llm_provider import PROVIDER_KEY_MAP, SUPPORTED_MODELS, validate_provider_keys

router = APIRouter()


# =========================================================================
# GET / -- list active agents
# =========================================================================


@router.get("", response_model=AgentListResponse)
async def list_agents(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """List all active agents, ordered by name."""
    agents = (
        db.query(AgentConfig)
        .filter(AgentConfig.is_active == True)
        .order_by(AgentConfig.name)
        .all()
    )
    return AgentListResponse(agents=agents)


# =========================================================================
# API Key Management (admin only) -- static paths BEFORE parameterized
# =========================================================================


def _mask_key(value: str) -> str:
    """Mask an API key for display, showing only the last 4 characters."""
    if not value or len(value) <= 4:
        return "****"
    return "****" + value[-4:]


class UpdateApiKeysRequest(BaseModel):
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None


@router.get("/api-keys")
async def get_api_keys(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Get LLM API key status -- shows which providers are configured and masked values."""
    provider_status = validate_provider_keys(db=db)

    # Read DB values for masking
    db_keys = {v[0]: v[1] for v in PROVIDER_KEY_MAP.values()}
    settings = db.query(Setting).filter(Setting.key.in_(db_keys.keys())).all()
    settings_map = {s.key: s.value for s in settings}

    result = {}
    for provider, (db_key, env_key) in PROVIDER_KEY_MAP.items():
        db_value = settings_map.get(db_key, "")
        result[provider] = {
            "configured": provider_status[provider],
            "source": "database" if db_value else ("environment" if provider_status[provider] else "not set"),
            "masked_value": _mask_key(db_value) if db_value else ("****" if provider_status[provider] else ""),
        }

    return result


@router.put("/api-keys")
async def update_api_keys(
    request: UpdateApiKeysRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Set LLM API keys in the database settings table.

    Only updates keys that are provided (non-None). Send empty string to clear a key.
    """
    updates = {}
    if request.anthropic_api_key is not None:
        updates["anthropic_api_key"] = request.anthropic_api_key
    if request.groq_api_key is not None:
        updates["groq_api_key"] = request.groq_api_key

    if not updates:
        raise HTTPException(status_code=400, detail="No keys provided")

    for key, value in updates.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
            setting.updated_by_id = current_user.id
        else:
            db.add(Setting(key=key, value=value, updated_by_id=current_user.id))

    db.commit()

    return {"status": "updated", "keys": list(updates.keys())}


@router.get("/available-models")
async def get_available_models(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Return models filtered to only providers with configured API keys."""
    provider_status = validate_provider_keys(db=db)
    available = [m for m in SUPPORTED_MODELS if provider_status.get(m["provider"], False)]
    return {"models": available}


# =========================================================================
# GET /{slug} -- agent detail (parameterized -- AFTER static routes)
# =========================================================================


@router.get("/{slug}", response_model=AgentConfigResponse)
async def get_agent(
    slug: str,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get a single agent by slug."""
    agent = db.query(AgentConfig).filter(AgentConfig.slug == slug).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# =========================================================================
# POST /run -- run agent with SSE streaming
# =========================================================================


@router.post("/run")
async def run_agent_endpoint(
    request: RunAgentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Run an agent and stream results via SSE.

    Returns a text/event-stream response with events in the format:
        event: agent
        data: {"type": "start", ...}

    Events follow the protocol:
        start -> tool_start/tool_result (optional) -> text_delta(s) -> usage -> done
    """
    # Look up agent
    config = db.query(AgentConfig).filter(AgentConfig.slug == request.agent_slug).first()
    if not config:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not config.is_active:
        raise HTTPException(status_code=400, detail="Agent is inactive")

    # Build user context
    user_context = {
        "email": current_user.email,
        "role": current_user.role,
        "user_id": current_user.id,
    }
    if request.context:
        user_context["page_context"] = request.context

    async def event_generator() -> AsyncGenerator[str, None]:
        """Yield SSE-formatted events from the agent runner, then log usage."""
        start_time = time.time()
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "model": config.model}
        tool_count = 0
        error_msg = None

        async for event in run_agent_streaming(config, request.message, user_context, db=db):
            # Track metrics from events
            if event["type"] == "usage":
                usage_data["prompt_tokens"] = event.get("prompt_tokens", 0)
                usage_data["completion_tokens"] = event.get("completion_tokens", 0)
                usage_data["model"] = event.get("model", config.model)
            elif event["type"] == "tool_start":
                tool_count += 1
            elif event["type"] == "error":
                error_msg = event.get("message", "Unknown error")

            # Format as SSE
            yield f"event: agent\ndata: {json.dumps(event)}\n\n"

        # Create usage log after streaming completes
        duration_ms = int((time.time() - start_time) * 1000)
        log = AgentUsageLog(
            agent_id=config.id,
            user_id=current_user.id,
            model_used=usage_data["model"],
            prompt_tokens=usage_data["prompt_tokens"],
            completion_tokens=usage_data["completion_tokens"],
            total_cost_usd=0.0,
            tool_calls_count=tool_count,
            duration_ms=duration_ms,
            success=error_msg is None,
            error_message=error_msg,
        )
        db.add(log)
        db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
