"""Tests for resolution API: list, sign, signatures, and validation."""
from __future__ import annotations

import pytest
from datetime import datetime

from app.models.decision import Decision, Vote


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def seed_closed_resolution(db_session, seed_user):
    """Create a closed resolution for signature tests."""
    resolution = Decision(
        title="Approve Q1 Budget",
        description="Resolution to approve the Q1 2026 operating budget.",
        type="resolution",
        status="closed",
        closed_at=datetime(2026, 3, 1, 12, 0),
        created_by_id=seed_user.id,
    )
    db_session.add(resolution)
    db_session.commit()
    db_session.refresh(resolution)
    return resolution


@pytest.fixture
def seed_open_resolution(db_session, seed_user):
    """Create an open (not closed) resolution."""
    resolution = Decision(
        title="Draft Policy Change",
        description="Proposed policy change for review.",
        type="resolution",
        status="open",
        created_by_id=seed_user.id,
    )
    db_session.add(resolution)
    db_session.commit()
    db_session.refresh(resolution)
    return resolution


@pytest.fixture
def seed_vote_decision(db_session, seed_user):
    """Create a vote-type (non-resolution) decision."""
    decision = Decision(
        title="Vote on Meeting Time",
        type="vote",
        status="closed",
        closed_at=datetime(2026, 3, 1, 12, 0),
        created_by_id=seed_user.id,
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    return decision


@pytest.fixture
def seed_board_member(db_session):
    """Create a second board member for signature status tests."""
    from app.models.member import BoardMember
    member = BoardMember(
        email="board@themany.com",
        name="Board Member",
        role="board",
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member


# =============================================================================
# Tests: List resolutions
# =============================================================================

@pytest.mark.asyncio
async def test_list_resolutions_only(
    client, db_session, seed_user, seed_closed_resolution, seed_vote_decision
):
    """GET /api/resolutions returns only type=resolution decisions."""
    response = await client.get(
        "/api/resolutions",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["type"] == "resolution"
    assert data["items"][0]["title"] == "Approve Q1 Budget"
    # Should include signature count fields
    assert "signature_count" in data["items"][0]
    assert "total_signers" in data["items"][0]


@pytest.mark.asyncio
async def test_list_resolutions_empty(client, db_session, seed_user):
    """GET /api/resolutions returns empty list when no resolutions exist."""
    response = await client.get(
        "/api/resolutions",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# =============================================================================
# Tests: Sign resolution
# =============================================================================

@pytest.mark.asyncio
async def test_sign_resolution(client, db_session, seed_user, seed_closed_resolution):
    """POST /api/resolutions/{id}/sign records signature with IP."""
    response = await client.post(
        f"/api/resolutions/{seed_closed_resolution.id}/sign",
        headers={
            "X-User-Email": seed_user.email,
            "X-Forwarded-For": "192.168.1.100",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "signed"
    assert "signature_id" in data
    assert "signed_at" in data


@pytest.mark.asyncio
async def test_sign_non_resolution_rejected(
    client, db_session, seed_user, seed_vote_decision
):
    """POST sign on a vote-type decision returns 400."""
    response = await client.post(
        f"/api/resolutions/{seed_vote_decision.id}/sign",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 400
    assert "Only resolutions can be signed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sign_not_closed_rejected(
    client, db_session, seed_user, seed_open_resolution
):
    """POST sign on an open resolution returns 400."""
    response = await client.post(
        f"/api/resolutions/{seed_open_resolution.id}/sign",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 400
    assert "closed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_duplicate_signature_rejected(
    client, db_session, seed_user, seed_closed_resolution
):
    """Signing the same resolution twice returns 400."""
    headers = {"X-User-Email": seed_user.email}

    # First sign -- should succeed
    resp1 = await client.post(
        f"/api/resolutions/{seed_closed_resolution.id}/sign",
        headers=headers,
    )
    assert resp1.status_code == 200

    # Second sign -- should fail
    resp2 = await client.post(
        f"/api/resolutions/{seed_closed_resolution.id}/sign",
        headers=headers,
    )
    assert resp2.status_code == 400
    assert "already signed" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sign_nonexistent_resolution(client, db_session, seed_user):
    """POST sign on nonexistent decision returns 404."""
    response = await client.post(
        "/api/resolutions/99999/sign",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 404


# =============================================================================
# Tests: Signature status
# =============================================================================

@pytest.mark.asyncio
async def test_signature_status(
    client, db_session, seed_user, seed_board_member, seed_closed_resolution
):
    """GET /api/resolutions/{id}/signatures shows signed and unsigned members."""
    # Sign with seed_user (admin role, so counted as board-level)
    await client.post(
        f"/api/resolutions/{seed_closed_resolution.id}/sign",
        headers={"X-User-Email": seed_user.email},
    )

    # Get signature status
    response = await client.get(
        f"/api/resolutions/{seed_closed_resolution.id}/signatures",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolution_id"] == seed_closed_resolution.id
    assert data["signed_count"] == 1
    assert data["total_members"] == 2  # seed_user (admin) + seed_board_member (board)

    # Check that one member signed and one did not
    signed = [s for s in data["signatures"] if s["signed_at"] is not None]
    unsigned = [s for s in data["signatures"] if s["signed_at"] is None]
    assert len(signed) == 1
    assert len(unsigned) == 1
    assert signed[0]["member_name"] == seed_user.name
    assert unsigned[0]["member_name"] == seed_board_member.name


@pytest.mark.asyncio
async def test_signature_status_nonexistent(client, db_session, seed_user):
    """GET signatures for nonexistent resolution returns 404."""
    response = await client.get(
        "/api/resolutions/99999/signatures",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 404


# =============================================================================
# Tests: Get resolution detail
# =============================================================================

@pytest.mark.asyncio
async def test_get_resolution_detail(
    client, db_session, seed_user, seed_closed_resolution
):
    """GET /api/resolutions/{id} returns resolution with detail."""
    response = await client.get(
        f"/api/resolutions/{seed_closed_resolution.id}",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["signature_count"] == 0
    assert "total_signers" in data


@pytest.mark.asyncio
async def test_get_vote_as_resolution_rejected(
    client, db_session, seed_user, seed_vote_decision
):
    """GET /api/resolutions/{id} for a vote-type decision returns 404."""
    response = await client.get(
        f"/api/resolutions/{seed_vote_decision.id}",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 404


# =============================================================================
# Tests: Resolution auto-numbering
# =============================================================================

@pytest.mark.asyncio
async def test_resolution_auto_numbering(client, db_session, seed_user):
    """Resolutions without resolution_number get auto-generated YYYY-NNN format."""
    resolution = Decision(
        title="New Resolution Without Number",
        type="resolution",
        status="closed",
        closed_at=datetime(2026, 3, 1),
        created_by_id=seed_user.id,
    )
    db_session.add(resolution)
    db_session.commit()
    db_session.refresh(resolution)

    response = await client.get(
        "/api/resolutions",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    assert item["resolution_number"] is not None
    assert item["resolution_number"].startswith("2026-")


# =============================================================================
# Tests: Agent tools registration (xfail - registered in Plan 02)
# =============================================================================

@pytest.mark.xfail(reason="Agent tools registered in Plan 02")
def test_resolution_tools_registered():
    """Resolution Writer tools should be registered in TOOL_REGISTRY."""
    from app.tools import TOOL_REGISTRY
    tool_names = [t.name for t in TOOL_REGISTRY]
    assert "create_resolution" in tool_names
    assert "list_resolutions" in tool_names
