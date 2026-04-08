"""Tests for meeting minutes persistence endpoints (POST and GET /api/meetings/{id}/minutes).

These endpoints were added in Plan 06-01 to support the minutes generator tool.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.models.meeting import Meeting, MeetingDocument
from app.models.document import Document


ADMIN_HEADERS = {"X-User-Email": "test@themany.com"}


# =============================================================================
# POST /api/meetings/{id}/minutes (create)
# =============================================================================


@pytest.mark.asyncio
async def test_create_minutes(client, db_session, seed_user, completed_meeting):
    """POST /api/meetings/{id}/minutes creates Document + MeetingDocument link."""
    payload = {
        "html_content": "<h1>Board Meeting Minutes</h1><p>The meeting was called to order.</p>",
        "title": "Meeting Minutes - February 2026",
    }
    resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "document_id" in data
    assert data["meeting_id"] == completed_meeting.id
    assert data["title"] == "Meeting Minutes - February 2026"
    assert data["status"] == "created"

    # Verify document was created in DB
    doc = db_session.query(Document).filter(Document.id == data["document_id"]).first()
    assert doc is not None
    assert doc.type == "minutes"
    assert "<h1>Board Meeting Minutes</h1>" in doc.description

    # Verify MeetingDocument link
    link = db_session.query(MeetingDocument).filter(
        MeetingDocument.meeting_id == completed_meeting.id,
        MeetingDocument.relationship_type == "minutes",
    ).first()
    assert link is not None
    assert link.document_id == doc.id


@pytest.mark.asyncio
async def test_create_minutes_requires_chair(client, db_session, seed_user, seed_shareholder, completed_meeting):
    """POST /api/meetings/{id}/minutes returns 403 for shareholder."""
    payload = {
        "html_content": "<p>Minutes</p>",
        "title": "Minutes",
    }
    resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=payload,
        headers={"X-User-Email": seed_shareholder.email},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_minutes_meeting_not_found(client, db_session, seed_user):
    """POST /api/meetings/99999/minutes returns 404 for nonexistent meeting."""
    payload = {"html_content": "<p>Test</p>", "title": "Test"}
    resp = await client.post(
        "/api/meetings/99999/minutes",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 404


# =============================================================================
# GET /api/meetings/{id}/minutes (retrieve)
# =============================================================================


@pytest.mark.asyncio
async def test_get_minutes(client, db_session, seed_user, completed_meeting):
    """GET /api/meetings/{id}/minutes returns minutes content after creation."""
    # First create minutes
    payload = {
        "html_content": "<h2>Minutes Content</h2><p>Discussion points here.</p>",
        "title": "Board Meeting Minutes",
    }
    create_resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert create_resp.status_code == 200

    # Now retrieve
    resp = await client.get(
        f"/api/meetings/{completed_meeting.id}/minutes",
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meeting_id"] == completed_meeting.id
    assert "Minutes Content" in data["html_content"]
    assert data["title"] == "Board Meeting Minutes"
    assert "document_id" in data


@pytest.mark.asyncio
async def test_get_minutes_not_found(client, db_session, seed_user, completed_meeting):
    """GET /api/meetings/{id}/minutes returns 404 when no minutes exist."""
    resp = await client.get(
        f"/api/meetings/{completed_meeting.id}/minutes",
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upsert_minutes(client, db_session, seed_user, completed_meeting):
    """POST /api/meetings/{id}/minutes again updates existing minutes (upsert)."""
    # Create initial minutes
    first_payload = {
        "html_content": "<p>First draft of minutes.</p>",
        "title": "Draft Minutes",
    }
    first_resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=first_payload,
        headers=ADMIN_HEADERS,
    )
    assert first_resp.status_code == 200
    first_doc_id = first_resp.json()["document_id"]

    # Update with new content
    second_payload = {
        "html_content": "<p>Final version of minutes with corrections.</p>",
        "title": "Final Minutes",
    }
    second_resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=second_payload,
        headers=ADMIN_HEADERS,
    )
    assert second_resp.status_code == 200
    data = second_resp.json()
    assert data["status"] == "updated"
    assert data["document_id"] == first_doc_id  # Same document updated, not new one

    # Verify content was updated
    get_resp = await client.get(
        f"/api/meetings/{completed_meeting.id}/minutes",
        headers=ADMIN_HEADERS,
    )
    assert "Final version" in get_resp.json()["html_content"]


@pytest.mark.asyncio
async def test_get_minutes_any_member(client, db_session, seed_user, seed_board_member, completed_meeting):
    """GET /api/meetings/{id}/minutes is accessible to board members (not just chair)."""
    # Create minutes as admin
    payload = {
        "html_content": "<p>Shared minutes.</p>",
        "title": "Shared Minutes",
    }
    await client.post(
        f"/api/meetings/{completed_meeting.id}/minutes",
        json=payload,
        headers=ADMIN_HEADERS,
    )

    # Read as board member
    resp = await client.get(
        f"/api/meetings/{completed_meeting.id}/minutes",
        headers={"X-User-Email": seed_board_member.email},
    )
    assert resp.status_code == 200
    assert "Shared minutes" in resp.json()["html_content"]
