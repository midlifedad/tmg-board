"""Tests for the agent runner -- core loop with tool iteration and streaming."""
from __future__ import annotations

import json
from typing import Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ──


class MockMessage:
    """Mimics LiteLLM response message."""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self):
        dump = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            dump["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return dump


class MockChoice:
    def __init__(self, message):
        self.message = message


class MockUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=5):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class MockResponse:
    """Mimics LiteLLM completion response."""

    def __init__(self, content=None, tool_calls=None, usage=None):
        self.choices = [MockChoice(MockMessage(content=content, tool_calls=tool_calls))]
        self.usage = usage or MockUsage()


class MockFunctionCall:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    def __init__(self, name, arguments, id="tc_1"):
        self.id = id
        self.function = MockFunctionCall(name, arguments)
        self.type = "function"


def make_agent_config(
    name="Test Agent",
    slug="test-agent",
    model="anthropic/claude-sonnet-4-5-20250929",
    system_prompt="You are a test assistant.",
    temperature=0.3,
    max_iterations=5,
    allowed_tool_names=None,
):
    """Create a mock AgentConfig object."""
    config = MagicMock()
    config.name = name
    config.slug = slug
    config.model = model
    config.system_prompt = system_prompt
    config.temperature = temperature
    config.max_iterations = max_iterations
    config.allowed_tool_names = allowed_tool_names or []
    return config


# ── run_agent tests ──


@pytest.mark.asyncio
async def test_agent_runner_simple_response():
    """Agent returns text when LLM response has no tool calls (single iteration)."""
    from app.services.agent_runner import run_agent

    mock_acompletion = AsyncMock(return_value=MockResponse(content="Hello!"))

    with patch("app.services.llm_provider.acompletion", mock_acompletion):
        result = await run_agent(
            config=make_agent_config(),
            message="Hi",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        )

    assert result == "Hello!"
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio
async def test_agent_runner_tool_call_cycle():
    """Agent executes tool call, feeds result back, gets final text response (two iterations)."""
    from app.services.agent_runner import run_agent

    tool_call = MockToolCall("get_meeting", json.dumps({"meeting_id": 1}))

    # First call returns tool_call, second returns text
    mock_acompletion = AsyncMock(side_effect=[
        MockResponse(tool_calls=[tool_call]),
        MockResponse(content="Done!"),
    ])

    mock_execute_tool = AsyncMock(return_value='{"id": 1, "title": "Board Meeting"}')

    with patch("app.services.llm_provider.acompletion", mock_acompletion), \
         patch("app.services.agent_runner.execute_tool", mock_execute_tool):
        result = await run_agent(
            config=make_agent_config(allowed_tool_names=["get_meeting"]),
            message="Get the meeting",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        )

    assert result == "Done!"
    assert mock_acompletion.call_count == 2
    mock_execute_tool.assert_called_once_with("get_meeting", json.dumps({"meeting_id": 1}), {"email": "test@themany.com", "role": "admin", "user_id": 1})


@pytest.mark.asyncio
async def test_agent_runner_max_iterations():
    """Agent stops after max_iterations if LLM keeps requesting tool calls."""
    from app.services.agent_runner import run_agent

    tool_call = MockToolCall("get_meeting", json.dumps({"meeting_id": 1}))

    # Always return tool_calls -- should hit max_iterations
    mock_acompletion = AsyncMock(return_value=MockResponse(tool_calls=[tool_call]))
    mock_execute_tool = AsyncMock(return_value='{"id": 1}')

    with patch("app.services.llm_provider.acompletion", mock_acompletion), \
         patch("app.services.agent_runner.execute_tool", mock_execute_tool):
        result = await run_agent(
            config=make_agent_config(max_iterations=2, allowed_tool_names=["get_meeting"]),
            message="Get the meeting",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        )

    assert "maximum iterations" in result.lower()
    assert mock_acompletion.call_count == 2


@pytest.mark.asyncio
async def test_agent_runner_tool_error_handling():
    """Agent handles tool execution error gracefully -- tool returns error JSON, agent continues."""
    from app.services.agent_runner import run_agent

    tool_call = MockToolCall("get_meeting", json.dumps({"meeting_id": 999}))

    mock_acompletion = AsyncMock(side_effect=[
        MockResponse(tool_calls=[tool_call]),
        MockResponse(content="I couldn't retrieve that meeting."),
    ])

    mock_execute_tool = AsyncMock(return_value='{"error": "Not found"}')

    with patch("app.services.llm_provider.acompletion", mock_acompletion), \
         patch("app.services.agent_runner.execute_tool", mock_execute_tool):
        result = await run_agent(
            config=make_agent_config(allowed_tool_names=["get_meeting"]),
            message="Get meeting 999",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        )

    assert result == "I couldn't retrieve that meeting."


@pytest.mark.asyncio
async def test_agent_runner_passes_config():
    """Agent passes correct model, temperature, and tools from AgentConfig to LiteLLM."""
    from app.services.agent_runner import run_agent

    mock_acompletion = AsyncMock(return_value=MockResponse(content="OK"))

    config = make_agent_config(
        model="gemini/gemini-2.0-flash",
        temperature=0.7,
        allowed_tool_names=["create_agenda_item"],
    )

    with patch("app.services.llm_provider.acompletion", mock_acompletion), \
         patch("app.services.agent_runner.get_tools_for_agent") as mock_get_tools:
        mock_get_tools.return_value = [{"type": "function", "function": {"name": "create_agenda_item"}}]

        result = await run_agent(
            config=config,
            message="Test",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        )

    call_kwargs = mock_acompletion.call_args.kwargs
    assert call_kwargs["model"] == "gemini/gemini-2.0-flash"
    assert call_kwargs["temperature"] == 0.7
    mock_get_tools.assert_called_with(["create_agenda_item"])


# ── run_agent_streaming tests ──


@pytest.mark.asyncio
async def test_streaming_event_order_no_tools():
    """Streaming without tools yields events: start -> text_delta -> usage -> done."""
    from app.services.agent_runner import run_agent_streaming

    mock_acompletion = AsyncMock(return_value=MockResponse(content="Hello stream!"))

    with patch("app.services.llm_provider.acompletion", mock_acompletion):
        events = []
        async for event in run_agent_streaming(
            config=make_agent_config(),
            message="Hi",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        ):
            events.append(event)

    event_types = [e["type"] for e in events]
    assert event_types[0] == "start"
    assert "text_delta" in event_types
    assert event_types[-2] == "usage"
    assert event_types[-1] == "done"


@pytest.mark.asyncio
async def test_streaming_event_order_with_tools():
    """Streaming with tools yields: start -> tool_start -> tool_result -> text_delta -> usage -> done."""
    from app.services.agent_runner import run_agent_streaming

    tool_call = MockToolCall("get_meeting", json.dumps({"meeting_id": 1}))

    mock_acompletion = AsyncMock(side_effect=[
        MockResponse(tool_calls=[tool_call]),
        MockResponse(content="Here is the meeting."),
    ])

    mock_execute_tool = AsyncMock(return_value='{"id": 1, "title": "Board Meeting"}')

    with patch("app.services.llm_provider.acompletion", mock_acompletion), \
         patch("app.services.agent_runner.execute_tool", mock_execute_tool):
        events = []
        async for event in run_agent_streaming(
            config=make_agent_config(allowed_tool_names=["get_meeting"]),
            message="Get the meeting",
            user_context={"email": "test@themany.com", "role": "admin", "user_id": 1},
        ):
            events.append(event)

    event_types = [e["type"] for e in events]
    assert event_types[0] == "start"
    assert "tool_start" in event_types
    assert "tool_result" in event_types
    assert "text_delta" in event_types
    assert event_types[-2] == "usage"
    assert event_types[-1] == "done"

    # Verify ordering: tool events come before text
    tool_start_idx = event_types.index("tool_start")
    text_delta_idx = event_types.index("text_delta")
    assert tool_start_idx < text_delta_idx
