"""Tests for auth dependency functions (require_member, require_chair, require_admin).

Tests are exercised through actual API calls to endpoints with known auth requirements:
- /api/meetings (require_member aka require_board)
- /api/meetings POST (require_chair)
- /api/agents/api-keys (require_admin)

Auth hierarchy:
- require_member (alias for require_board): allows admin, chair, board. Denies shareholder.
- require_chair: allows admin, chair, board. Denies shareholder.
- require_admin: allows admin only. Denies board, chair, shareholder.
"""
from __future__ import annotations

import pytest

from app.models.member import BoardMember


# =============================================================================
# require_member (alias for require_board)
# =============================================================================


@pytest.mark.asyncio
async def test_require_member_allows_admin(client, db_session, seed_user):
    """Admin passes require_member (GET /api/meetings)."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": seed_user.email}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_member_allows_board(client, db_session, seed_user, seed_board_member):
    """Board member passes require_member."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": seed_board_member.email}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_member_allows_chair(client, db_session, seed_user, seed_chair_member):
    """Chair passes require_member."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": seed_chair_member.email}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_member_rejects_shareholder(client, db_session, seed_user, seed_shareholder):
    """Shareholder is rejected by require_member (which is require_board)."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": seed_shareholder.email}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_require_member_rejects_unknown(client, db_session):
    """Unknown email returns 401 on require_member."""
    resp = await client.get(
        "/api/meetings", headers={"X-User-Email": "unknown@example.com"}
    )
    assert resp.status_code == 401


# =============================================================================
# require_chair
# =============================================================================


@pytest.mark.asyncio
async def test_require_chair_allows_admin(client, db_session, seed_user):
    """Admin passes require_chair (POST /api/meetings)."""
    payload = {"title": "Auth Test Meeting", "date": "2026-09-01T10:00:00"}
    resp = await client.post(
        "/api/meetings",
        json=payload,
        headers={"X-User-Email": seed_user.email},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_chair_allows_board(client, db_session, seed_user, seed_board_member):
    """Board member passes require_chair (current behavior: board has same perms as chair)."""
    payload = {"title": "Board Auth Test", "date": "2026-09-02T10:00:00"}
    resp = await client.post(
        "/api/meetings",
        json=payload,
        headers={"X-User-Email": seed_board_member.email},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_chair_allows_chair(client, db_session, seed_user, seed_chair_member):
    """Chair passes require_chair."""
    payload = {"title": "Chair Auth Test", "date": "2026-09-03T10:00:00"}
    resp = await client.post(
        "/api/meetings",
        json=payload,
        headers={"X-User-Email": seed_chair_member.email},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_chair_rejects_shareholder(client, db_session, seed_user, seed_shareholder):
    """Shareholder is rejected by require_chair."""
    payload = {"title": "Unauthorized", "date": "2026-09-04T10:00:00"}
    resp = await client.post(
        "/api/meetings",
        json=payload,
        headers={"X-User-Email": seed_shareholder.email},
    )
    assert resp.status_code == 403


# =============================================================================
# require_admin
# =============================================================================


@pytest.mark.asyncio
async def test_require_admin_allows_admin(client, db_session, seed_user, seed_agent):
    """Admin passes require_admin (GET /api/agents/api-keys)."""
    resp = await client.get(
        "/api/agents/api-keys",
        headers={"X-User-Email": seed_user.email},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_admin_rejects_board(client, db_session, seed_user, seed_board_member):
    """Board member is rejected by require_admin."""
    resp = await client.get(
        "/api/agents/api-keys",
        headers={"X-User-Email": seed_board_member.email},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_rejects_chair(client, db_session, seed_user, seed_chair_member):
    """Chair is rejected by require_admin."""
    resp = await client.get(
        "/api/agents/api-keys",
        headers={"X-User-Email": seed_chair_member.email},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_no_header_returns_401(client, db_session):
    """Missing X-User-Email header returns 401."""
    resp = await client.get("/api/meetings")
    assert resp.status_code == 401
