"""Meeting-related tool handlers: create_agenda_item, get_meeting, list_meetings.

All tools use httpx.AsyncClient to call the board REST API internally.
The base URL defaults to http://localhost:3010 and can be overridden via
TOOL_API_BASE_URL environment variable.
Tools pass X-User-Email header on every request for auth context.
"""
import json
import os

import httpx

from app.tools import ToolDefinition, register_tool


def _get_base_url() -> str:
    """Get the base URL for internal API calls."""
    return os.environ.get("TOOL_API_BASE_URL", "http://localhost:3010")


# ── create_agenda_item ──


async def _create_agenda_item(params: dict, user_context: dict) -> str:
    """Create a new agenda item for a meeting via the board API."""
    meeting_id = params["meeting_id"]
    body = {"title": params["title"]}
    if "description" in params:
        body["description"] = params["description"]
    if "item_type" in params:
        body["item_type"] = params["item_type"]
    if "duration_minutes" in params:
        body["duration_minutes"] = params["duration_minutes"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.post(
                f"/api/meetings/{meeting_id}/agenda",
                json=body,
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="create_agenda_item",
    description="Create a new agenda item for a board meeting",
    parameters_schema={
        "type": "object",
        "properties": {
            "meeting_id": {"type": "integer", "description": "ID of the meeting"},
            "title": {"type": "string", "description": "Title of the agenda item"},
            "description": {"type": "string", "description": "Description or details"},
            "item_type": {
                "type": "string",
                "enum": ["information", "discussion", "decision_required", "consent_agenda"],
                "description": "Type of agenda item",
            },
            "duration_minutes": {"type": "integer", "description": "Expected duration in minutes"},
        },
        "required": ["meeting_id", "title"],
    },
    handler=_create_agenda_item,
    category="meetings",
))


# ── get_meeting ──


async def _get_meeting(params: dict, user_context: dict) -> str:
    """Get meeting details via the board API."""
    meeting_id = params["meeting_id"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.get(
                f"/api/meetings/{meeting_id}",
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="get_meeting",
    description="Get details of a specific board meeting by ID",
    parameters_schema={
        "type": "object",
        "properties": {
            "meeting_id": {"type": "integer", "description": "ID of the meeting to retrieve"},
        },
        "required": ["meeting_id"],
    },
    handler=_get_meeting,
    category="meetings",
))


# ── list_meetings ──


async def _list_meetings(params: dict, user_context: dict) -> str:
    """List board meetings via the board API."""
    limit = params.get("limit", 10)

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.get(
                "/api/meetings",
                params={"limit": limit},
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="list_meetings",
    description="List upcoming board meetings with optional limit",
    parameters_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximum number of meetings to return (default 10)"},
        },
    },
    handler=_list_meetings,
    category="meetings",
))
