"""Core agent loop -- non-streaming tool iterations, streaming final response.

The agent runner calls LiteLLM, detects tool calls, executes them against
the board REST API with user auth context, and iterates until the LLM
produces a final text response.
"""
from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from litellm import acompletion

from app.tools import execute_tool, get_tools_for_agent


async def run_agent(
    config,
    message: str,
    user_context: dict,
) -> str:
    """Non-streaming agent loop.

    Args:
        config: AgentConfig with model, system_prompt, temperature, max_iterations, allowed_tool_names
        message: User's input message
        user_context: Dict with email, role, user_id for tool auth context

    Returns:
        Final text response from the LLM.
    """
    messages: List[dict] = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": message},
    ]

    tools = get_tools_for_agent(config.allowed_tool_names) if config.allowed_tool_names else []

    for _ in range(config.max_iterations):
        kwargs: dict = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await acompletion(**kwargs)
        msg = response.choices[0].message

        # No tool calls means final response
        if not msg.tool_calls:
            return msg.content

        # Execute each tool call and feed results back
        messages.append(msg.model_dump())
        for tool_call in msg.tool_calls:
            result = await execute_tool(
                tool_call.function.name,
                tool_call.function.arguments,
                user_context,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

    return "Agent reached maximum iterations without completing."


async def run_agent_streaming(
    config,
    message: str,
    user_context: dict,
) -> AsyncGenerator[dict, None]:
    """Hybrid streaming agent loop (Pattern S1).

    Non-streaming for tool iterations (avoids tool call accumulation pitfall),
    yields text content from the final non-streaming call as a single text_delta.

    Yields SSE event dicts:
        - {"type": "start", "agent_name": str}
        - {"type": "tool_start", "tool_name": str, "tool_call_id": str}
        - {"type": "tool_result", "tool_name": str, "tool_call_id": str, "result": str, "success": bool}
        - {"type": "text_delta", "content": str}
        - {"type": "error", "message": str}
        - {"type": "usage", "prompt_tokens": int, "completion_tokens": int, "model": str}
        - {"type": "done"}
    """
    yield {"type": "start", "agent_name": config.name}

    messages: List[dict] = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": message},
    ]

    tools = get_tools_for_agent(config.allowed_tool_names) if config.allowed_tool_names else []

    total_prompt_tokens = 0
    total_completion_tokens = 0

    completed = False
    for _ in range(config.max_iterations):
        kwargs: dict = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await acompletion(**kwargs)
        msg = response.choices[0].message

        # Accumulate usage
        if response.usage:
            total_prompt_tokens += response.usage.prompt_tokens
            total_completion_tokens += response.usage.completion_tokens

        if msg.tool_calls:
            # Execute tools (non-streaming) and emit events
            messages.append(msg.model_dump())
            for tc in msg.tool_calls:
                yield {
                    "type": "tool_start",
                    "tool_name": tc.function.name,
                    "tool_call_id": tc.id,
                }
                result = await execute_tool(
                    tc.function.name,
                    tc.function.arguments,
                    user_context,
                )
                success = '"error"' not in result
                yield {
                    "type": "tool_result",
                    "tool_name": tc.function.name,
                    "tool_call_id": tc.id,
                    "result": result,
                    "success": success,
                }
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
        else:
            # Final response -- yield content as single text_delta
            if msg.content:
                yield {"type": "text_delta", "content": msg.content}
            completed = True
            break

    if not completed:
        yield {"type": "error", "message": "Agent reached maximum iterations without completing."}

    yield {
        "type": "usage",
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "model": config.model,
    }
    yield {"type": "done"}
