"""Tests for admin agent management endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from app.models.agent import AgentConfig, AgentUsageLog
from app.models.audit import AuditLog
from app.models.member import BoardMember


ADMIN_HEADERS = {"X-User-Email": "test@themany.com"}


@pytest.fixture
def seed_usage_logs(db_session: Session, seed_agent: AgentConfig, seed_user: BoardMember):
    """Create sample AgentUsageLog entries for testing usage stats."""
    logs = [
        AgentUsageLog(
            agent_id=seed_agent.id,
            user_id=seed_user.id,
            model_used="anthropic/claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.005,
            tool_calls_count=2,
            duration_ms=1500,
            success=True,
        ),
        AgentUsageLog(
            agent_id=seed_agent.id,
            user_id=seed_user.id,
            model_used="anthropic/claude-sonnet-4-5-20250929",
            prompt_tokens=200,
            completion_tokens=100,
            total_cost_usd=0.010,
            tool_calls_count=3,
            duration_ms=2500,
            success=True,
        ),
        AgentUsageLog(
            agent_id=seed_agent.id,
            user_id=seed_user.id,
            model_used="anthropic/claude-sonnet-4-5-20250929",
            prompt_tokens=150,
            completion_tokens=75,
            total_cost_usd=0.008,
            tool_calls_count=1,
            duration_ms=1000,
            success=True,
        ),
    ]
    for log in logs:
        db_session.add(log)
    db_session.commit()
    return logs


# =============================================================================
# List Agents
# =============================================================================


@pytest.mark.asyncio
async def test_list_agents_returns_active(client, seed_agent, seed_user):
    """GET /api/admin/agents returns list of active agents."""
    resp = await client.get("/api/admin/agents", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [a["name"] for a in data]
    assert "Test Agent" in names


@pytest.mark.asyncio
async def test_list_agents_include_inactive(client, db_session, seed_user):
    """GET /api/admin/agents?include_inactive=true returns inactive agents too."""
    # Create an inactive agent
    inactive = AgentConfig(
        name="Inactive Agent",
        slug="inactive-agent",
        system_prompt="Inactive.",
        model="anthropic/claude-sonnet-4-5-20250929",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    # Without include_inactive, should NOT see it
    resp = await client.get("/api/admin/agents", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()]
    assert "Inactive Agent" not in names

    # With include_inactive, should see it
    resp = await client.get(
        "/api/admin/agents", params={"include_inactive": "true"}, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()]
    assert "Inactive Agent" in names


# =============================================================================
# Create Agent
# =============================================================================


@pytest.mark.asyncio
async def test_create_agent(client, seed_user, db_session):
    """POST /api/admin/agents creates agent with auto-generated slug."""
    payload = {
        "name": "My New Agent",
        "description": "A test agent",
        "system_prompt": "You are a helpful assistant.",
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "allowed_tool_names": ["get_meeting"],
    }
    resp = await client.post("/api/admin/agents", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My New Agent"
    assert data["slug"] == "my-new-agent"
    assert data["description"] == "A test agent"
    assert data["allowed_tool_names"] == ["get_meeting"]
    assert data["is_active"] is True

    # Verify AuditLog entry
    audit = db_session.query(AuditLog).filter(
        AuditLog.entity_type == "agent",
        AuditLog.action == "create",
    ).first()
    assert audit is not None
    assert audit.entity_name == "My New Agent"
    assert audit.changed_by_id == seed_user.id


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client, seed_agent, seed_user):
    """POST /api/admin/agents with duplicate name returns 400."""
    payload = {
        "name": "Test Agent",
        "system_prompt": "Duplicate.",
        "model": "anthropic/claude-sonnet-4-5-20250929",
    }
    resp = await client.post("/api/admin/agents", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 400


# =============================================================================
# Update Agent
# =============================================================================


@pytest.mark.asyncio
async def test_update_agent(client, seed_agent, seed_user):
    """PATCH /api/admin/agents/{id} updates fields."""
    payload = {
        "system_prompt": "Updated prompt.",
        "model": "gemini/gemini-2.0-flash",
        "allowed_tool_names": ["get_meeting", "list_meetings"],
    }
    resp = await client.patch(
        f"/api/admin/agents/{seed_agent.id}", json=payload, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["system_prompt"] == "Updated prompt."
    assert data["model"] == "gemini/gemini-2.0-flash"
    assert data["allowed_tool_names"] == ["get_meeting", "list_meetings"]


@pytest.mark.asyncio
async def test_update_agent_creates_audit_log(client, seed_agent, seed_user, db_session):
    """PATCH /api/admin/agents/{id} creates AuditLog with old/new values."""
    payload = {"model": "gemini/gemini-2.0-flash"}
    resp = await client.patch(
        f"/api/admin/agents/{seed_agent.id}", json=payload, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200

    audit = db_session.query(AuditLog).filter(
        AuditLog.entity_type == "agent",
        AuditLog.action == "update",
        AuditLog.entity_id == seed_agent.id,
    ).first()
    assert audit is not None
    assert audit.changes is not None
    assert "model" in audit.changes
    assert audit.changes["model"]["old"] == "anthropic/claude-sonnet-4-5-20250929"
    assert audit.changes["model"]["new"] == "gemini/gemini-2.0-flash"


# =============================================================================
# Delete (Soft Delete) Agent
# =============================================================================


@pytest.mark.asyncio
async def test_delete_agent_soft_delete(client, seed_agent, seed_user, db_session):
    """DELETE /api/admin/agents/{id} sets is_active=False and creates AuditLog."""
    resp = await client.delete(
        f"/api/admin/agents/{seed_agent.id}", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deactivated"
    assert data["id"] == seed_agent.id

    # Verify agent is now inactive
    db_session.refresh(seed_agent)
    assert seed_agent.is_active is False

    # Verify AuditLog
    audit = db_session.query(AuditLog).filter(
        AuditLog.entity_type == "agent",
        AuditLog.action == "delete",
        AuditLog.entity_id == seed_agent.id,
    ).first()
    assert audit is not None


# =============================================================================
# Tool List
# =============================================================================


@pytest.mark.asyncio
async def test_list_tools(client, seed_user):
    """GET /api/admin/agents/tools returns tool names, descriptions, categories."""
    resp = await client.get("/api/admin/agents/tools", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # TOOL_REGISTRY should have at least the meeting tools
    if len(data) > 0:
        tool = data[0]
        assert "name" in tool
        assert "description" in tool
        assert "category" in tool
        assert "parameter_count" in tool


# =============================================================================
# Usage Stats
# =============================================================================


@pytest.mark.asyncio
async def test_usage_stats(client, seed_agent, seed_user, seed_usage_logs):
    """GET /api/admin/agents/usage returns aggregated stats per agent."""
    resp = await client.get("/api/admin/agents/usage", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Find the seed agent stats
    agent_stats = [s for s in data if s["agent_id"] == seed_agent.id]
    assert len(agent_stats) == 1
    stats = agent_stats[0]
    assert stats["agent_name"] == "Test Agent"
    assert stats["total_calls"] == 3
    assert stats["total_prompt_tokens"] == 450  # 100 + 200 + 150
    assert stats["total_completion_tokens"] == 225  # 50 + 100 + 75
    # Float comparison with tolerance
    assert abs(stats["total_cost_usd"] - 0.023) < 0.001  # 0.005 + 0.010 + 0.008


@pytest.mark.asyncio
async def test_usage_stats_date_filter(client, seed_agent, seed_user, seed_usage_logs, db_session):
    """GET /api/admin/agents/usage?start_date=X&end_date=Y filters by date range."""
    # Set one log to the past
    old_log = seed_usage_logs[0]
    old_log.created_at = datetime.utcnow() - timedelta(days=30)
    db_session.commit()

    # Filter to last 7 days -- should exclude the old log
    start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
    resp = await client.get(
        "/api/admin/agents/usage",
        params={"start_date": start_date},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    if len(data) > 0:
        agent_stats = [s for s in data if s["agent_id"] == seed_agent.id]
        if len(agent_stats) > 0:
            # Should only have 2 logs (not the old one)
            assert agent_stats[0]["total_calls"] == 2


# =============================================================================
# Auth: Non-admin gets 403
# =============================================================================


@pytest.mark.asyncio
async def test_non_admin_gets_403(client, db_session):
    """Non-admin user gets 403 on all agent admin endpoints."""
    non_admin = BoardMember(
        email="viewer@themany.com",
        name="Viewer User",
        role="board",
    )
    db_session.add(non_admin)
    db_session.commit()

    headers = {"X-User-Email": "viewer@themany.com"}

    resp = await client.get("/api/admin/agents", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/admin/agents",
        json={"name": "X", "system_prompt": "Y", "model": "Z"},
        headers=headers,
    )
    assert resp.status_code == 403

    resp = await client.get("/api/admin/agents/tools", headers=headers)
    assert resp.status_code == 403

    resp = await client.get("/api/admin/agents/usage", headers=headers)
    assert resp.status_code == 403
