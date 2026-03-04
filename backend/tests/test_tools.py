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


# ── LLM Provider Tests ──


def test_validate_provider_keys():
    """validate_provider_keys returns correct booleans based on env vars."""
    from app.services.llm_provider import validate_provider_keys

    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "GEMINI_API_KEY": "",
        "GROQ_API_KEY": "gsk-test",
    }):
        result = validate_provider_keys()

    assert result["anthropic"] is True
    assert result["gemini"] is False
    assert result["groq"] is True
