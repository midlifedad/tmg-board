"""Tests for tool registry, tool definitions, and tool execution."""
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def user_context():
    """Standard user context for tool tests."""
    return {"email": "test@themany.com", "role": "admin", "user_id": 1}


# ── Tool Registry Tests ──


def test_tool_registry_has_meeting_tools():
    """TOOL_REGISTRY should contain the 3 meeting tools after import."""
    from app.tools import TOOL_REGISTRY

    assert "create_agenda_item" in TOOL_REGISTRY
    assert "get_meeting" in TOOL_REGISTRY
    assert "list_meetings" in TOOL_REGISTRY


def test_get_tools_for_agent_filters():
    """get_tools_for_agent returns only the tools in the allowed list."""
    from app.tools import get_tools_for_agent

    one_tool = get_tools_for_agent(["create_agenda_item"])
    assert len(one_tool) == 1
    assert one_tool[0]["function"]["name"] == "create_agenda_item"

    two_tools = get_tools_for_agent(["create_agenda_item", "get_meeting"])
    assert len(two_tools) == 2
    names = {t["function"]["name"] for t in two_tools}
    assert names == {"create_agenda_item", "get_meeting"}


def test_get_tools_for_agent_unknown_name():
    """get_tools_for_agent with unknown tool name returns empty list (no error)."""
    from app.tools import get_tools_for_agent

    result = get_tools_for_agent(["nonexistent"])
    assert result == []


def test_tool_definitions_format():
    """Each tool definition should have correct OpenAI function calling format."""
    from app.tools import get_tool_definitions

    definitions = get_tool_definitions()
    assert len(definitions) >= 3

    for tool_def in definitions:
        assert tool_def["type"] == "function"
        func = tool_def["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"
        assert "properties" in func["parameters"]


# ── Tool Execution Tests ──


@pytest.mark.asyncio
async def test_execute_tool_unknown(user_context):
    """execute_tool with unknown tool name returns JSON error (not exception)."""
    from app.tools import execute_tool

    result = await execute_tool("fake_tool", "{}", user_context)
    parsed = json.loads(result)
    assert "error" in parsed
    assert "fake_tool" in parsed["error"]


@pytest.mark.asyncio
async def test_create_agenda_item_calls_api(user_context):
    """create_agenda_item handler calls POST with correct URL, body, and X-User-Email header."""
    from app.tools import TOOL_REGISTRY

    handler = TOOL_REGISTRY["create_agenda_item"].handler

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "title": "Budget Review"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.tools.meetings.httpx.AsyncClient", return_value=mock_client):
        result = await handler(
            {"meeting_id": 5, "title": "Budget Review", "item_type": "discussion"},
            user_context,
        )

    # Verify the POST call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/api/meetings/5/agenda" in str(call_args)

    # Verify X-User-Email header was set
    call_kwargs = call_args.kwargs if call_args.kwargs else {}
    if "headers" in call_kwargs:
        assert call_kwargs["headers"]["X-User-Email"] == "test@themany.com"

    parsed = json.loads(result)
    assert parsed["title"] == "Budget Review"


@pytest.mark.asyncio
async def test_tool_handler_api_error(user_context):
    """Tool handler returns error JSON when API returns 403 (does not raise exception)."""
    from app.tools import TOOL_REGISTRY

    handler = TOOL_REGISTRY["get_meeting"].handler

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.tools.meetings.httpx.AsyncClient", return_value=mock_client):
        result = await handler({"meeting_id": 1}, user_context)

    parsed = json.loads(result)
    assert "error" in parsed


# ── create_meeting_with_agenda Tool Tests ──


def test_create_meeting_with_agenda_registered():
    """create_meeting_with_agenda tool must be in TOOL_REGISTRY."""
    from app.tools import TOOL_REGISTRY

    assert "create_meeting_with_agenda" in TOOL_REGISTRY
    tool = TOOL_REGISTRY["create_meeting_with_agenda"]
    assert tool.category == "meetings"


def test_create_meeting_with_agenda_schema():
    """create_meeting_with_agenda has correct parameters schema."""
    from app.tools import TOOL_REGISTRY

    tool = TOOL_REGISTRY["create_meeting_with_agenda"]
    schema = tool.parameters_schema

    # Required fields
    assert schema["type"] == "object"
    assert "title" in schema["properties"]
    assert "agenda_items" in schema["properties"]
    assert set(schema["required"]) == {"title", "agenda_items"}

    # Optional fields
    assert "scheduled_date" in schema["properties"]
    assert "duration_minutes" in schema["properties"]
    assert "location" in schema["properties"]
    assert "meeting_link" in schema["properties"]
    assert "description" in schema["properties"]

    # agenda_items is an array of objects
    items_schema = schema["properties"]["agenda_items"]
    assert items_schema["type"] == "array"
    item_props = items_schema["items"]["properties"]
    assert "title" in item_props
    assert "description" in item_props
    assert "item_type" in item_props
    assert "duration_minutes" in item_props

    # item_type has correct enum values
    assert set(item_props["item_type"]["enum"]) == {
        "information", "discussion", "decision_required", "consent_agenda"
    }


@pytest.mark.asyncio
async def test_create_meeting_with_agenda_calls_api(user_context):
    """create_meeting_with_agenda handler POSTs to /api/meetings/with-agenda with correct body and headers."""
    from app.tools import TOOL_REGISTRY

    handler = TOOL_REGISTRY["create_meeting_with_agenda"].handler

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 42,
        "title": "Q1 Board Meeting",
        "agenda_items": [
            {"id": 1, "title": "Call to Order", "item_type": "information"}
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    params = {
        "title": "Q1 Board Meeting",
        "scheduled_date": "2026-04-15T10:00:00",
        "duration_minutes": 90,
        "location": "Board Room A",
        "agenda_items": [
            {"title": "Call to Order", "item_type": "information", "duration_minutes": 5}
        ],
    }

    with patch("app.tools.meetings.httpx.AsyncClient", return_value=mock_client):
        result = await handler(params, user_context)

    # Verify POST to correct endpoint
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/api/meetings/with-agenda" in str(call_args)

    # Verify X-User-Email header
    call_kwargs = call_args.kwargs if call_args.kwargs else {}
    if "headers" in call_kwargs:
        assert call_kwargs["headers"]["X-User-Email"] == "test@themany.com"

    # Verify result is JSON string
    parsed = json.loads(result)
    assert parsed["id"] == 42
    assert parsed["title"] == "Q1 Board Meeting"


@pytest.mark.asyncio
async def test_create_meeting_with_agenda_api_error(user_context):
    """create_meeting_with_agenda returns error JSON on API failure."""
    from app.tools import TOOL_REGISTRY

    handler = TOOL_REGISTRY["create_meeting_with_agenda"].handler

    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Validation Error"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.tools.meetings.httpx.AsyncClient", return_value=mock_client):
        result = await handler(
            {"title": "Test Meeting", "agenda_items": []},
            user_context,
        )

    parsed = json.loads(result)
    assert "error" in parsed


# ── Meeting Setup Agent Seed Tests ──


def test_meeting_setup_agent_has_create_meeting_with_agenda_tool(seeded_db_session):
    """Meeting Setup agent seed must include create_meeting_with_agenda in allowed_tool_names."""
    from app.models.agent import AgentConfig

    agent = seeded_db_session.query(AgentConfig).filter(
        AgentConfig.slug == "meeting-setup"
    ).first()
    assert agent is not None
    assert "create_meeting_with_agenda" in agent.allowed_tool_names


def test_meeting_setup_agent_has_production_prompt(seeded_db_session):
    """Meeting Setup agent seed must have a real system prompt (not placeholder)."""
    from app.models.agent import AgentConfig

    agent = seeded_db_session.query(AgentConfig).filter(
        AgentConfig.slug == "meeting-setup"
    ).first()
    assert agent is not None
    # Must NOT contain the placeholder text
    assert "[Detailed prompt to be added in Phase 02]" not in agent.system_prompt
    # Must contain key elements of the production prompt
    assert "create_meeting_with_agenda" in agent.system_prompt
    assert "information" in agent.system_prompt
    assert "discussion" in agent.system_prompt
    assert "decision_required" in agent.system_prompt
    assert "consent_agenda" in agent.system_prompt


# ── LLM Provider Tests ──


def test_validate_provider_keys():
    """validate_provider_keys returns correct booleans based on env vars."""
    from app.services.llm_provider import validate_provider_keys

    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "GROQ_API_KEY": "gsk-test",
    }):
        result = validate_provider_keys()

    assert result["anthropic"] is True
    assert result["groq"] is True
    assert "gemini" not in result
