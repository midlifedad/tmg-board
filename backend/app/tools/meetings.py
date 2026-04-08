"""Meeting-related tool handlers: create_agenda_item, get_meeting, list_meetings.

All tools use httpx.AsyncClient to call the board REST API internally.
The base URL defaults to http://localhost:{PORT} and can be overridden via
TOOL_API_BASE_URL environment variable.
Tools pass X-User-Email header on every request for auth context.
"""
import json
import os

import httpx

from app.tools import ToolDefinition, register_tool


def _get_base_url() -> str:
    """Get the base URL for internal API calls (same backend)."""
    return os.environ.get(
        "TOOL_API_BASE_URL",
        f"http://localhost:{os.environ.get('PORT', '3010')}",
    )


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


# ── create_meeting_with_agenda ──


async def _create_meeting_with_agenda(params: dict, user_context: dict) -> str:
    """Create a new meeting with agenda items via the board API."""
    body = {"title": params["title"]}
    for field in ("scheduled_date", "duration_minutes", "location",
                  "meeting_link", "description"):
        if field in params and params[field] is not None:
            body[field] = params[field]
    if "agenda_items" in params:
        body["agenda_items"] = params["agenda_items"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.post(
                "/api/meetings/with-agenda",
                json=body,
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="create_meeting_with_agenda",
    description=(
        "Create a new board meeting with agenda items in a single operation. "
        "Use this after parsing a meeting description to create the structured meeting."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the meeting",
            },
            "scheduled_date": {
                "type": "string",
                "description": (
                    "ISO 8601 datetime for the meeting "
                    "(e.g., '2026-04-15T10:00:00'). "
                    "Leave empty if not specified in the description."
                ),
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Total meeting duration in minutes",
            },
            "location": {
                "type": "string",
                "description": "Physical location or 'Virtual'",
            },
            "meeting_link": {
                "type": "string",
                "description": "URL for virtual meeting",
            },
            "description": {
                "type": "string",
                "description": "Meeting description or notes",
            },
            "agenda_items": {
                "type": "array",
                "description": "List of agenda items in order",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "item_type": {
                            "type": "string",
                            "enum": [
                                "information",
                                "discussion",
                                "decision_required",
                                "consent_agenda",
                            ],
                        },
                        "duration_minutes": {"type": "integer"},
                    },
                    "required": ["title"],
                },
            },
        },
        "required": ["title", "agenda_items"],
    },
    handler=_create_meeting_with_agenda,
    category="meetings",
))
