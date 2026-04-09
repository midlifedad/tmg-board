"""Core agent loop -- non-streaming tool iterations, streaming final response.

The agent runner calls LiteLLM, detects tool calls, executes them against
the board REST API with user auth context, and iterates until the LLM
produces a final text response.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.llm_provider import get_completion
from app.tools import execute_tool, get_tools_for_agent

logger = logging.getLogger(__name__)


def _extract_user_error(raw: str) -> str:
    """Pull a human-readable message out of nested LiteLLM exception strings."""
    import json as _json

    # Try to find a JSON body with a "message" field (Anthropic/OpenAI style)
    for prefix in ['"message":"', "'message': '"]:
        idx = raw.find(prefix)
        if idx != -1:
            start = idx + len(prefix)
            end = raw.find('"' if prefix.startswith('"') else "'", start)
            if end != -1:
                return raw[start:end]

    # Try parsing embedded JSON object
    brace = raw.find('{"')
    if brace != -1:
        try:
            obj = _json.loads(raw[brace:])
            msg = obj.get("error", {}).get("message") or obj.get("message")
            if msg:
                return msg
        except (_json.JSONDecodeError, AttributeError):
            pass

    # Fallback: strip the litellm prefix noise
    for noise in ["litellm.BadRequestError: ", "AnthropicException - ", "litellm."]:
        raw = raw.replace(noise, "")

    # Truncate if still too long
    if len(raw) > 200:
        return raw[:200] + "..."
    return raw


async def run_agent(
    config,
    message: str,
    user_context: dict,
    db: Optional[Session] = None,
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

    for iteration in range(config.max_iterations):
        try:
            response = await get_completion(
                model=config.model,
                messages=messages,
                tools=tools or None,
                temperature=config.temperature,
                db=db,
            )
        except Exception as e:
            logger.error("LLM call failed on iteration %d: %s", iteration + 1, e, exc_info=True)
            return f"Error: Failed to get response from LLM — {e}"

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
    db: Optional[Session] = None,
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
    logger.info(
        "Agent run started: agent=%s model=%s user=%s",
        config.name, config.model, user_context.get("email", "unknown"),
    )
    yield {"type": "start", "agent_name": config.name}

    messages: List[dict] = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": message},
    ]

    tools = get_tools_for_agent(config.allowed_tool_names) if config.allowed_tool_names else []
    logger.info("Agent tools: %s", [t["function"]["name"] for t in tools] if tools else "none")

    total_prompt_tokens = 0
    total_completion_tokens = 0

    completed = False
    for iteration in range(config.max_iterations):
        # --- LLM call with error handling ---
        try:
            logger.info("LLM call iteration %d/%d (model=%s)", iteration + 1, config.max_iterations, config.model)
            response = await get_completion(
                model=config.model,
                messages=messages,
                tools=tools or None,
                temperature=config.temperature,
                db=db,
            )
        except Exception as e:
            raw_msg = str(e)
            logger.error("LLM call failed: %s: %s", type(e).__name__, raw_msg, exc_info=True)
            # Extract user-friendly message from nested LiteLLM/provider errors
            user_msg = _extract_user_error(raw_msg)
            yield {"type": "error", "message": user_msg}
            break

        msg = response.choices[0].message

        # Accumulate usage
        if response.usage:
            total_prompt_tokens += response.usage.prompt_tokens
            total_completion_tokens += response.usage.completion_tokens

        if msg.tool_calls:
            # Execute tools (non-streaming) and emit events
            messages.append(msg.model_dump())
            for tc in msg.tool_calls:
                logger.info("Tool call: %s (id=%s)", tc.function.name, tc.id)
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
                if not success:
                    logger.warning("Tool %s failed: %s", tc.function.name, result[:200])
                else:
                    logger.info("Tool %s succeeded", tc.function.name)
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

    logger.info(
        "Agent run finished: agent=%s completed=%s tokens=%d+%d",
        config.name, completed, total_prompt_tokens, total_completion_tokens,
    )

    yield {
        "type": "usage",
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "model": config.model,
    }
    yield {"type": "done"}
