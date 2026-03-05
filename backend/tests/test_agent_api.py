"""Integration tests for the Agent API endpoints (SSE streaming, list, detail)."""
from __future__ import annotations

import json
from typing import List
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.models.agent import AgentConfig, AgentUsageLog


def parse_sse_events(body: str) -> List[dict]:
    """Parse SSE response body into list of event data dicts.

    SSE format:
        event: agent
        data: {"type": "start", ...}
        <blank line>
    """
    events = []
    for block in body.strip().split("\n\n"):
        for line in block.strip().split("\n"):
            if line.startswith("data: "):
                data_str = line[len("data: "):]
                events.append(json.loads(data_str))
    return events


def _make_llm_response(content="Test response", tool_calls=None, prompt_tokens=10, completion_tokens=5):
    """Create a mock LiteLLM response object."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    msg.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": None,
    }

    choice = MagicMock()
    choice.message = msg

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _make_tool_call_response(tool_name="get_meeting", tool_call_id="call_123", arguments='{"meeting_id": 1}'):
    """Create a mock LiteLLM response with a tool call."""
    tc = MagicMock()
    tc.id = tool_call_id
    tc.function = MagicMock()
    tc.function.name = tool_name
    tc.function.arguments = arguments

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    msg.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tool_call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": arguments},
            }
        ],
    }

    usage = MagicMock()
    usage.prompt_tokens = 8
    usage.completion_tokens = 4

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    response.usage = usage
    return response


# =========================================================================
# GET /api/agents (list)
# =========================================================================


@pytest.mark.asyncio
async def test_list_agents(client, db_session, seed_user):
    """GET /api/agents returns only active agents."""
    # Seed 1 active + 1 inactive agent
    active = AgentConfig(
        name="Active Agent",
        slug="active-agent",
        system_prompt="active prompt",
        model="anthropic/claude-sonnet-4-5-20250929",
        is_active=True,
    )
    inactive = AgentConfig(
        name="Inactive Agent",
        slug="inactive-agent",
        system_prompt="inactive prompt",
        model="anthropic/claude-sonnet-4-5-20250929",
        is_active=False,
    )
    db_session.add_all([active, inactive])
    db_session.commit()

    resp = await client.get("/api/agents", headers={"X-User-Email": "test@themany.com"})

    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    slugs = [a["slug"] for a in data["agents"]]
    assert "active-agent" in slugs
    assert "inactive-agent" not in slugs


# =========================================================================
# GET /api/agents/{slug} (detail)
# =========================================================================


@pytest.mark.asyncio
async def test_get_agent_by_slug(client, db_session, seed_agent, seed_user):
    """GET /api/agents/{slug} returns agent details for valid slug."""
    resp = await client.get(
        f"/api/agents/{seed_agent.slug}",
        headers={"X-User-Email": seed_user.email},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == seed_agent.slug
    assert data["name"] == seed_agent.name
    assert data["model"] == seed_agent.model


@pytest.mark.asyncio
async def test_get_agent_not_found(client, seed_user):
    """GET /api/agents/nonexistent returns 404."""
    resp = await client.get(
        "/api/agents/nonexistent",
        headers={"X-User-Email": seed_user.email},
    )
    assert resp.status_code == 404


# =========================================================================
# POST /api/agents/run (SSE streaming)
# =========================================================================


@pytest.mark.asyncio
async def test_run_agent_sse_content_type(client, db_session, seed_agent, seed_user):
    """POST /api/agents/run returns content-type text/event-stream."""
    with patch("app.services.llm_provider.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()

        resp = await client.post(
            "/api/agents/run",
            json={"agent_slug": seed_agent.slug, "message": "hello"},
            headers={"X-User-Email": seed_user.email},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_run_agent_sse_event_order(client, db_session, seed_agent, seed_user):
    """POST /api/agents/run SSE events arrive in order: start -> text_delta(s) -> usage -> done."""
    with patch("app.services.llm_provider.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(content="Hello from agent!")

        resp = await client.post(
            "/api/agents/run",
            json={"agent_slug": seed_agent.slug, "message": "hello"},
            headers={"X-User-Email": seed_user.email},
        )

    events = parse_sse_events(resp.text)
    assert len(events) >= 4  # start, text_delta, usage, done

    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert types[-1] == "done"
    assert types[-2] == "usage"
    assert "text_delta" in types


@pytest.mark.asyncio
async def test_run_agent_with_tool_events(client, db_session, seed_agent, seed_user):
    """POST /api/agents/run with tool calls includes tool_start and tool_result events."""
    tool_response = _make_tool_call_response()
    final_response = _make_llm_response(content="Done with tools")

    with patch("app.services.llm_provider.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [tool_response, final_response]

        with patch("app.tools.execute_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = '{"meeting_id": 1, "title": "Board Meeting"}'

            resp = await client.post(
                "/api/agents/run",
                json={"agent_slug": seed_agent.slug, "message": "get meeting"},
                headers={"X-User-Email": seed_user.email},
            )

    events = parse_sse_events(resp.text)
    types = [e["type"] for e in events]

    assert "tool_start" in types
    assert "tool_result" in types

    # tool_start must come before tool_result
    assert types.index("tool_start") < types.index("tool_result")


@pytest.mark.asyncio
async def test_run_agent_requires_auth(client):
    """POST /api/agents/run returns 401 without X-User-Email header."""
    resp = await client.post(
        "/api/agents/run",
        json={"agent_slug": "test-agent", "message": "hello"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_run_agent_unknown_slug(client, seed_user):
    """POST /api/agents/run with agent_slug='fake' returns 404."""
    resp = await client.post(
        "/api/agents/run",
        json={"agent_slug": "fake", "message": "hello"},
        headers={"X-User-Email": seed_user.email},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_agent_creates_usage_log(client, db_session, seed_agent, seed_user):
    """POST /api/agents/run creates AgentUsageLog after successful run."""
    with patch("app.services.llm_provider.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()

        resp = await client.post(
            "/api/agents/run",
            json={"agent_slug": seed_agent.slug, "message": "hello"},
            headers={"X-User-Email": seed_user.email},
        )

    assert resp.status_code == 200

    # Check usage log was created
    logs = db_session.query(AgentUsageLog).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.agent_id == seed_agent.id
    assert log.user_id == seed_user.id
    assert log.success is True
    assert log.prompt_tokens == 10
    assert log.completion_tokens == 5


@pytest.mark.asyncio
async def test_run_agent_inactive(client, db_session, seed_user):
    """POST /api/agents/run returns 400 when agent is inactive."""
    agent = AgentConfig(
        name="Dead Agent",
        slug="dead-agent",
        system_prompt="I'm dead",
        model="anthropic/claude-sonnet-4-5-20250929",
        is_active=False,
    )
    db_session.add(agent)
    db_session.commit()

    resp = await client.post(
        "/api/agents/run",
        json={"agent_slug": "dead-agent", "message": "hello"},
        headers={"X-User-Email": seed_user.email},
    )
    assert resp.status_code == 400
