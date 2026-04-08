"""Integration tests for Meeting CRUD, Agenda, Attendance, and Members endpoints.

Covers endpoints in backend/app/api/meetings.py via httpx AsyncClient.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.models.meeting import Meeting, AgendaItem, MeetingAttendance
from app.models.member import BoardMember


ADMIN_HEADERS = {"X-User-Email": "test@themany.com"}


# =============================================================================
# Meeting CRUD
# =============================================================================


@pytest.mark.asyncio
async def test_list_meetings(client, db_session, seed_user, seed_meeting):
    """GET /api/meetings returns a paginated list of meetings."""
    resp = await client.get("/api/meetings", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    titles = [m["title"] for m in data["items"]]
    assert "Test Board Meeting" in titles


@pytest.mark.asyncio
async def test_list_meetings_filter_status(client, db_session, seed_user, seed_meeting, completed_meeting):
    """GET /api/meetings?status=completed filters by status."""
    resp = await client.get(
        "/api/meetings", params={"status": "completed"}, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    statuses = [m["status"] for m in data["items"]]
    assert all(s == "completed" for s in statuses)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_meeting_detail(client, db_session, seed_user, seed_meeting):
    """GET /api/meetings/{id} returns meeting detail."""
    resp = await client.get(
        f"/api/meetings/{seed_meeting.id}", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Board Meeting"
    assert data["status"] == "scheduled"


@pytest.mark.asyncio
async def test_get_meeting_not_found(client, db_session, seed_user):
    """GET /api/meetings/99999 returns 404."""
    resp = await client.get("/api/meetings/99999", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_meeting(client, db_session, seed_user):
    """POST /api/meetings creates a new meeting."""
    payload = {
        "title": "New Board Meeting",
        "date": "2026-05-01T10:00:00",
        "duration_minutes": 60,
        "location": "Virtual",
    }
    resp = await client.post("/api/meetings", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Board Meeting"
    assert data["status"] == "scheduled"
    assert data["duration_minutes"] == 60


@pytest.mark.asyncio
async def test_create_meeting_requires_chair(client, db_session, seed_user, seed_shareholder):
    """POST /api/meetings returns 403 for shareholder role."""
    payload = {
        "title": "Unauthorized Meeting",
        "date": "2026-06-01T10:00:00",
    }
    resp = await client.post(
        "/api/meetings",
        json=payload,
        headers={"X-User-Email": seed_shareholder.email},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_meeting(client, db_session, seed_user, seed_meeting):
    """PATCH /api/meetings/{id} updates meeting fields."""
    payload = {"title": "Updated Board Meeting", "location": "New Room"}
    resp = await client.patch(
        f"/api/meetings/{seed_meeting.id}", json=payload, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Board Meeting"
    assert data["location"] == "New Room"


@pytest.mark.asyncio
async def test_cancel_meeting(client, db_session, seed_user, seed_meeting):
    """DELETE /api/meetings/{id} sets status to cancelled."""
    resp = await client.delete(
        f"/api/meetings/{seed_meeting.id}", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_start_meeting(client, db_session, seed_user, seed_meeting):
    """POST /api/meetings/{id}/start transitions scheduled -> in_progress."""
    resp = await client.post(
        f"/api/meetings/{seed_meeting.id}/start", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"
    assert "started_at" in data


@pytest.mark.asyncio
async def test_start_meeting_not_scheduled(client, db_session, seed_user, completed_meeting):
    """POST /api/meetings/{id}/start on completed meeting returns 400."""
    resp = await client.post(
        f"/api/meetings/{completed_meeting.id}/start", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_end_meeting(client, db_session, seed_user, seed_meeting):
    """POST /api/meetings/{id}/end transitions in_progress -> completed."""
    # First start the meeting
    seed_meeting.status = "in_progress"
    seed_meeting.started_at = datetime(2026, 3, 15, 10, 0)
    db_session.commit()

    resp = await client.post(
        f"/api/meetings/{seed_meeting.id}/end", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "ended_at" in data


@pytest.mark.asyncio
async def test_end_meeting_not_in_progress(client, db_session, seed_user, seed_meeting):
    """POST /api/meetings/{id}/end on scheduled meeting returns 400."""
    resp = await client.post(
        f"/api/meetings/{seed_meeting.id}/end", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 400


# =============================================================================
# Agenda Item CRUD
# =============================================================================


@pytest.mark.asyncio
async def test_get_agenda(client, db_session, seed_user, seed_meeting, seed_agenda_item):
    """GET /api/meetings/{id}/agenda returns ordered agenda items."""
    resp = await client.get(
        f"/api/meetings/{seed_meeting.id}/agenda", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Call to Order"


@pytest.mark.asyncio
async def test_add_agenda_item(client, db_session, seed_user, seed_meeting):
    """POST /api/meetings/{id}/agenda adds an agenda item."""
    payload = {
        "title": "Financial Report",
        "description": "Q1 financials review",
        "item_type": "information",
        "duration_minutes": 15,
    }
    resp = await client.post(
        f"/api/meetings/{seed_meeting.id}/agenda",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Financial Report"
    assert data["duration_minutes"] == 15


@pytest.mark.asyncio
async def test_update_agenda_item(client, db_session, seed_user, seed_meeting, seed_agenda_item):
    """PATCH /api/meetings/{id}/agenda/{item_id} updates agenda item fields."""
    payload = {"title": "Updated Call to Order", "duration_minutes": 10}
    resp = await client.patch(
        f"/api/meetings/{seed_meeting.id}/agenda/{seed_agenda_item.id}",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Call to Order"
    assert data["duration_minutes"] == 10


@pytest.mark.asyncio
async def test_delete_agenda_item(client, db_session, seed_user, seed_meeting, seed_agenda_item):
    """DELETE /api/meetings/{id}/agenda/{item_id} removes the item."""
    resp = await client.delete(
        f"/api/meetings/{seed_meeting.id}/agenda/{seed_agenda_item.id}",
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"

    # Verify it's gone
    agenda_resp = await client.get(
        f"/api/meetings/{seed_meeting.id}/agenda", headers=ADMIN_HEADERS
    )
    assert len(agenda_resp.json()) == 0


@pytest.mark.asyncio
async def test_reorder_agenda(client, db_session, seed_user, seed_meeting):
    """PATCH /api/meetings/{id}/agenda/reorder reorders items correctly."""
    # Create two agenda items
    item1 = AgendaItem(
        meeting_id=seed_meeting.id, title="Item A", item_type="information", order_index=0
    )
    item2 = AgendaItem(
        meeting_id=seed_meeting.id, title="Item B", item_type="discussion", order_index=1
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    # Reorder: B before A
    payload = {"item_ids": [item2.id, item1.id]}
    resp = await client.patch(
        f"/api/meetings/{seed_meeting.id}/agenda/reorder",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title"] == "Item B"
    assert data[1]["title"] == "Item A"


# =============================================================================
# Attendance
# =============================================================================


@pytest.mark.asyncio
async def test_get_attendance(client, db_session, seed_user, seed_meeting):
    """GET /api/meetings/{id}/attendance returns attendance list."""
    resp = await client.get(
        f"/api/meetings/{seed_meeting.id}/attendance", headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_record_attendance(client, db_session, seed_user, seed_meeting):
    """POST /api/meetings/{id}/attendance records batch attendance."""
    payload = {
        "attendance": [
            {"member_id": seed_user.id, "status": "present"},
        ]
    }
    resp = await client.post(
        f"/api/meetings/{seed_meeting.id}/attendance",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["count"] == 1


# =============================================================================
# Members
# =============================================================================


@pytest.mark.asyncio
async def test_list_members(client, db_session, seed_user):
    """GET /api/meetings/members returns board members list."""
    resp = await client.get("/api/meetings/members", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [m["name"] for m in data]
    assert "Test User" in names


# =============================================================================
# Create Meeting with Agenda (single-call)
# =============================================================================


@pytest.mark.asyncio
async def test_create_meeting_with_agenda(client, db_session, seed_user):
    """POST /api/meetings/with-agenda creates meeting + agenda items."""
    payload = {
        "title": "Combined Meeting",
        "date": "2026-07-01T14:00:00",
        "duration_minutes": 120,
        "location": "Board Room",
        "agenda_items": [
            {"title": "Opening", "item_type": "information", "duration_minutes": 5},
            {"title": "Budget Review", "item_type": "discussion", "duration_minutes": 30},
        ],
    }
    resp = await client.post(
        "/api/meetings/with-agenda", json=payload, headers=ADMIN_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Combined Meeting"
    assert len(data["agenda_items"]) == 2
    assert data["agenda_items"][0]["title"] == "Opening"
    assert data["agenda_items"][1]["title"] == "Budget Review"


@pytest.mark.asyncio
async def test_create_meeting_with_agenda_requires_chair(client, db_session, seed_user, seed_shareholder):
    """POST /api/meetings/with-agenda returns 403 for shareholder."""
    payload = {
        "title": "Unauthorized",
        "date": "2026-08-01T10:00:00",
        "agenda_items": [],
    }
    resp = await client.post(
        "/api/meetings/with-agenda",
        json=payload,
        headers={"X-User-Email": seed_shareholder.email},
    )
    assert resp.status_code == 403


# =============================================================================
# Auth edge cases
# =============================================================================


@pytest.mark.asyncio
async def test_meetings_requires_auth(client):
    """GET /api/meetings without X-User-Email returns 401."""
    resp = await client.get("/api/meetings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_meetings_rejects_unknown_email(client, db_session):
    """GET /api/meetings with unknown email returns 401."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": "nobody@unknown.com"}
    )
    assert resp.status_code == 401
