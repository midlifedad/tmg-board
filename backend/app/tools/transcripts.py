"""Transcript-related tool handlers for the Minutes Generator agent.

Tools:
- get_meeting_details: Fetches meeting info, agenda, and attendance in parallel
- get_meeting_transcript: Fetches transcript content for a meeting
- create_minutes_document: Creates an HTML minutes document linked to a meeting

All tools use httpx.AsyncClient to call the board REST API internally.
The base URL defaults to http://localhost:{PORT} and can be overridden via
TOOL_API_BASE_URL environment variable.
Tools pass X-User-Email header on every request for auth context.
"""
from __future__ import annotations

import asyncio
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


# -- get_meeting_details --


async def _get_meeting_details(params: dict, user_context: dict) -> str:
    """Fetch meeting info, agenda, and attendance in parallel."""
    meeting_id = params["meeting_id"]
    headers = {"X-User-Email": user_context["email"]}

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            meeting_task = client.get(
                f"/api/meetings/{meeting_id}", headers=headers
            )
            agenda_task = client.get(
                f"/api/meetings/{meeting_id}/agenda", headers=headers
            )
            attendance_task = client.get(
                f"/api/meetings/{meeting_id}/attendance", headers=headers
            )

            meeting_resp, agenda_resp, attendance_resp = await asyncio.gather(
                meeting_task, agenda_task, attendance_task
            )

        result = {}

        if meeting_resp.status_code >= 400:
            return json.dumps({"error": meeting_resp.text, "status": meeting_resp.status_code})
        result["meeting"] = meeting_resp.json()

        # Agenda and attendance may 404 if none exist yet -- return empty lists
        result["agenda"] = agenda_resp.json() if agenda_resp.status_code < 400 else []
        result["attendance"] = attendance_resp.json() if attendance_resp.status_code < 400 else []

        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="get_meeting_details",
    description=(
        "Get full meeting details including meeting info, agenda items, and "
        "attendance list. Returns all three in a single response."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "meeting_id": {
                "type": "integer",
                "description": "ID of the meeting to retrieve details for",
            },
        },
        "required": ["meeting_id"],
    },
    handler=_get_meeting_details,
    category="transcripts",
))


# -- get_meeting_transcript --


async def _get_meeting_transcript(params: dict, user_context: dict) -> str:
    """Fetch transcript content for a meeting."""
    meeting_id = params["meeting_id"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.get(
                f"/api/meetings/{meeting_id}/transcript",
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="get_meeting_transcript",
    description=(
        "Get the transcript content for a board meeting. Returns the full "
        "transcript text along with metadata (source, character count, etc.)."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "meeting_id": {
                "type": "integer",
                "description": "ID of the meeting whose transcript to retrieve",
            },
        },
        "required": ["meeting_id"],
    },
    handler=_get_meeting_transcript,
    category="transcripts",
))


# -- create_minutes_document --


async def _create_minutes_document(params: dict, user_context: dict) -> str:
    """Create an HTML minutes document and link it to the meeting."""
    meeting_id = params["meeting_id"]
    title = params["title"]
    html_content = params["html_content"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.post(
                f"/api/meetings/{meeting_id}/minutes",
                json={"title": title, "html_content": html_content},
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                # If the minutes endpoint doesn't exist yet (parallel plan),
                # return a clear message rather than failing silently
                if response.status_code in (404, 405):
                    return json.dumps({
                        "error": (
                            "Minutes endpoint not available yet. "
                            "The /api/meetings/{meeting_id}/minutes endpoint "
                            "may not have been created. The HTML content was "
                            "generated successfully but could not be saved."
                        ),
                        "html_content": html_content,
                        "status": response.status_code,
                    })
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="create_minutes_document",
    description=(
        "Create a formatted HTML minutes document and link it to the meeting. "
        "The document is saved as type 'minutes' and automatically linked to "
        "the source meeting."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "meeting_id": {
                "type": "integer",
                "description": "ID of the meeting to create minutes for",
            },
            "title": {
                "type": "string",
                "description": "Title for the minutes document (e.g., 'Board Meeting Minutes - January 2026')",
            },
            "html_content": {
                "type": "string",
                "description": "The formatted HTML content of the meeting minutes",
            },
        },
        "required": ["meeting_id", "title", "html_content"],
    },
    handler=_create_minutes_document,
    category="transcripts",
))
