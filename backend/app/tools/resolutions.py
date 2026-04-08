"""Resolution Writer agent tool handlers.

Tools:
- create_resolution: Creates a decision with type=resolution via REST API
- draft_resolution_document: Creates an HTML resolution document and links it
- list_resolutions: Lists resolutions via /api/resolutions
- get_resolution: Gets resolution detail via /api/resolutions/{id}

All tools use httpx.AsyncClient to call the board REST API internally.
The base URL defaults to http://localhost:{PORT} and can be overridden via
TOOL_API_BASE_URL environment variable.
Tools pass X-User-Email header on every request for auth context.
"""
from __future__ import annotations

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


# -- create_resolution --


async def _create_resolution(params: dict, user_context: dict) -> str:
    """Create a new decision of type=resolution via the board API."""
    body = {
        "title": params["title"],
        "description": params["description"],
        "type": "resolution",
    }
    if "resolution_number" in params:
        body["resolution_number"] = params["resolution_number"]
    if "meeting_id" in params:
        body["meeting_id"] = params["meeting_id"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.post(
                "/api/decisions",
                json=body,
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="create_resolution",
    description="Create a new board resolution (a decision with type=resolution)",
    parameters_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Resolution title",
            },
            "description": {
                "type": "string",
                "description": "Resolution body text / description",
            },
            "resolution_number": {
                "type": "string",
                "description": "Resolution number (e.g., '2026-001'). Auto-generated if omitted.",
            },
            "meeting_id": {
                "type": "integer",
                "description": "Optional meeting ID to link this resolution to",
            },
        },
        "required": ["title", "description"],
    },
    handler=_create_resolution,
    category="resolutions",
))


# -- draft_resolution_document --


async def _draft_resolution_document(params: dict, user_context: dict) -> str:
    """Create a formal HTML resolution document and link it to the resolution."""
    resolution_id = params["resolution_id"]
    title = params["title"]
    html_content = params["html_content"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            # Step 1: Upload the HTML content as a document via multipart form
            files = {
                "file": ("resolution.html", html_content.encode("utf-8"), "text/html"),
            }
            data = {
                "title": title,
                "type": "resolution",
            }
            doc_response = await client.post(
                "/api/documents/upload",
                files=files,
                data=data,
                headers={"X-User-Email": user_context["email"]},
            )
            if doc_response.status_code >= 400:
                return json.dumps({
                    "error": f"Failed to create document: {doc_response.text}",
                    "status": doc_response.status_code,
                })

            doc_data = doc_response.json()
            document_id = doc_data.get("id")

            # Step 2: Link the document to the resolution via PATCH /api/decisions/{id}
            link_response = await client.patch(
                f"/api/decisions/{resolution_id}",
                json={"document_id": document_id},
                headers={"X-User-Email": user_context["email"]},
            )
            if link_response.status_code >= 400:
                return json.dumps({
                    "partial_success": True,
                    "document_id": document_id,
                    "error": f"Document created but linking failed: {link_response.text}",
                    "status": link_response.status_code,
                })

            return json.dumps({
                "status": "success",
                "document_id": document_id,
                "resolution_id": resolution_id,
                "message": f"Document '{title}' created and linked to resolution.",
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="draft_resolution_document",
    description=(
        "Create a formal HTML resolution document and link it to an existing "
        "resolution. The HTML should follow formal resolution format with "
        "WHEREAS and RESOLVED clauses."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "resolution_id": {
                "type": "integer",
                "description": "ID of the resolution (decision) to link the document to",
            },
            "title": {
                "type": "string",
                "description": "Title for the document (e.g., 'Resolution 2026-001: Budget Approval')",
            },
            "html_content": {
                "type": "string",
                "description": "The formatted HTML content of the resolution document",
            },
        },
        "required": ["resolution_id", "title", "html_content"],
    },
    handler=_draft_resolution_document,
    category="resolutions",
))


# -- list_resolutions --


async def _list_resolutions(params: dict, user_context: dict) -> str:
    """List resolutions via the /api/resolutions endpoint."""
    query_params = {}
    if "status" in params:
        query_params["status"] = params["status"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.get(
                "/api/resolutions",
                params=query_params,
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="list_resolutions",
    description="List board resolutions with optional status filter",
    parameters_schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status (draft, open, closed)",
            },
        },
    },
    handler=_list_resolutions,
    category="resolutions",
))


# -- get_resolution --


async def _get_resolution(params: dict, user_context: dict) -> str:
    """Get resolution detail via /api/resolutions/{id}."""
    resolution_id = params["resolution_id"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.get(
                f"/api/resolutions/{resolution_id}",
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})


register_tool(ToolDefinition(
    name="get_resolution",
    description="Get details of a specific board resolution by ID",
    parameters_schema={
        "type": "object",
        "properties": {
            "resolution_id": {
                "type": "integer",
                "description": "ID of the resolution to retrieve",
            },
        },
        "required": ["resolution_id"],
    },
    handler=_get_resolution,
    category="resolutions",
))
