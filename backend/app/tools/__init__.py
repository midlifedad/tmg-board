"""Tool registry with ToolDefinition dataclass and lookup functions.

Tools are registered at module level by importing tool modules at the bottom
of this file. Each tool module calls register_tool() to add itself to
TOOL_REGISTRY.
"""
import json
from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolDefinition:
    """A registered tool that an agent can invoke."""
    name: str
    description: str
    parameters_schema: dict  # OpenAI function calling format
    handler: Callable  # async function(params: dict, user_context: dict) -> str
    category: str  # e.g. "meetings", "documents", "decisions"


# Global tool registry populated by tool modules on import
TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def register_tool(tool: ToolDefinition) -> None:
    """Register a tool in the global registry."""
    TOOL_REGISTRY[tool.name] = tool


def get_tools_for_agent(allowed_names: list[str]) -> list[dict]:
    """Return OpenAI-format tool definitions filtered by allowed_names.

    Each returned item has shape:
    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}

    Unknown names are silently ignored (no error).
    """
    result = []
    for name in allowed_names:
        tool = TOOL_REGISTRY.get(name)
        if tool:
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            })
    return result


def get_tool_definitions() -> list[dict]:
    """Return all tool definitions in OpenAI format (for admin display)."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            },
        }
        for tool in TOOL_REGISTRY.values()
    ]


async def execute_tool(tool_name: str, arguments: str, user_context: dict) -> str:
    """Look up a tool in registry, parse arguments, call handler, return result string.

    On error, returns JSON string {"error": "message"}.
    If tool not found, returns {"error": "Unknown tool: {name}"}.
    """
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        params = json.loads(arguments) if isinstance(arguments, str) else arguments
        result = await tool.handler(params, user_context)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})


# Import tool modules to trigger registration
from app.tools import meetings  # noqa: E402, F401
from app.tools import transcripts  # noqa: E402, F401
