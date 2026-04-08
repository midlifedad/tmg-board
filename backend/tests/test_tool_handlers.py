"""Tests for transcript tool handlers (get_meeting_details, get_meeting_transcript, create_minutes_document).

Tool handlers in app/tools/transcripts.py use httpx.AsyncClient to call the board REST API.
Tests mock httpx.AsyncClient to verify correct URL construction, header passing, and response handling.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def user_context():
    """Standard user context for tool handler tests."""
    return {"email": "test@themany.com", "role": "admin", "user_id": 1}


def _mock_response(status_code=200, json_data=None, text=""):
    """Create a mock httpx Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _mock_client(**method_responses):
    """Create a mock httpx.AsyncClient with pre-configured method responses.

    Usage:
        client = _mock_client(get=response)  # All .get() calls return response
        client = _mock_client(post=response)  # All .post() calls return response
    """
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    for method, response in method_responses.items():
        getattr(mock, method).return_value = response
    return mock


# =============================================================================
# get_meeting_details
# =============================================================================


@pytest.mark.asyncio
async def test_get_meeting_details_success(user_context):
    """get_meeting_details fetches meeting, agenda, and attendance in parallel."""
    from app.tools.transcripts import _get_meeting_details

    meeting_data = {"id": 1, "title": "Board Meeting", "status": "completed"}
    agenda_data = [{"id": 1, "title": "Opening"}]
    attendance_data = [{"member_id": 1, "status": "present"}]

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)

    # Three concurrent GET calls: meeting, agenda, attendance
    mock.get = AsyncMock(side_effect=[
        _mock_response(200, meeting_data),
        _mock_response(200, agenda_data),
        _mock_response(200, attendance_data),
    ])

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _get_meeting_details({"meeting_id": 1}, user_context)

    parsed = json.loads(result)
    assert parsed["meeting"]["title"] == "Board Meeting"
    assert len(parsed["agenda"]) == 1
    assert len(parsed["attendance"]) == 1

    # Verify all three GET calls were made
    assert mock.get.call_count == 3


@pytest.mark.asyncio
async def test_get_meeting_details_meeting_not_found(user_context):
    """get_meeting_details returns error JSON when meeting returns 404."""
    from app.tools.transcripts import _get_meeting_details

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)

    mock.get = AsyncMock(side_effect=[
        _mock_response(404, text="Meeting not found"),
        _mock_response(404, text="Not found"),
        _mock_response(404, text="Not found"),
    ])

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _get_meeting_details({"meeting_id": 999}, user_context)

    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["status"] == 404


@pytest.mark.asyncio
async def test_get_meeting_details_partial_failure(user_context):
    """get_meeting_details returns empty lists for failed agenda/attendance."""
    from app.tools.transcripts import _get_meeting_details

    meeting_data = {"id": 1, "title": "Meeting"}

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)

    mock.get = AsyncMock(side_effect=[
        _mock_response(200, meeting_data),
        _mock_response(404, text="No agenda"),
        _mock_response(404, text="No attendance"),
    ])

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _get_meeting_details({"meeting_id": 1}, user_context)

    parsed = json.loads(result)
    assert parsed["meeting"]["id"] == 1
    assert parsed["agenda"] == []
    assert parsed["attendance"] == []


# =============================================================================
# get_meeting_transcript
# =============================================================================


@pytest.mark.asyncio
async def test_get_meeting_transcript_success(user_context):
    """get_meeting_transcript returns transcript content on success."""
    from app.tools.transcripts import _get_meeting_transcript

    transcript_data = {
        "content": "The meeting was called to order at 10:00 AM.",
        "source": "paste",
        "char_count": 44,
    }

    mock = _mock_client(get=_mock_response(200, transcript_data))

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _get_meeting_transcript({"meeting_id": 1}, user_context)

    parsed = json.loads(result)
    assert "called to order" in parsed["content"]
    assert parsed["source"] == "paste"


@pytest.mark.asyncio
async def test_get_meeting_transcript_not_found(user_context):
    """get_meeting_transcript returns error JSON on 404."""
    from app.tools.transcripts import _get_meeting_transcript

    mock = _mock_client(get=_mock_response(404, text="No transcript found"))

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _get_meeting_transcript({"meeting_id": 999}, user_context)

    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["status"] == 404


# =============================================================================
# create_minutes_document
# =============================================================================


@pytest.mark.asyncio
async def test_create_minutes_document_success(user_context):
    """create_minutes_document POSTs to /minutes endpoint and returns result."""
    from app.tools.transcripts import _create_minutes_document

    response_data = {
        "document_id": 42,
        "meeting_id": 1,
        "title": "Meeting Minutes - January 2026",
        "status": "created",
    }

    mock = _mock_client(post=_mock_response(200, response_data))

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _create_minutes_document(
            {
                "meeting_id": 1,
                "title": "Meeting Minutes - January 2026",
                "content": "# Minutes\n\nContent here.",
            },
            user_context,
        )

    parsed = json.loads(result)
    assert parsed["document_id"] == 42
    assert parsed["status"] == "created"

    # Verify the POST was called with correct body (markdown converted to HTML)
    mock.post.assert_called_once()
    call_kwargs = mock.post.call_args.kwargs
    assert call_kwargs["json"]["title"] == "Meeting Minutes - January 2026"
    assert "<h1>" in call_kwargs["json"]["html_content"]
    assert call_kwargs["headers"]["X-User-Email"] == "test@themany.com"


@pytest.mark.asyncio
async def test_create_minutes_document_fallback(user_context):
    """create_minutes_document returns error message when endpoint returns 404."""
    from app.tools.transcripts import _create_minutes_document

    mock = _mock_client(post=_mock_response(404, text="Not found"))

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _create_minutes_document(
            {
                "meeting_id": 1,
                "title": "Minutes",
                "content": "The generated content.",
            },
            user_context,
        )

    parsed = json.loads(result)
    assert "error" in parsed
    assert "not available" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_create_minutes_document_server_error(user_context):
    """create_minutes_document returns error JSON on 500."""
    from app.tools.transcripts import _create_minutes_document

    mock = _mock_client(post=_mock_response(500, text="Internal Server Error"))

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        result = await _create_minutes_document(
            {
                "meeting_id": 1,
                "title": "Minutes",
                "content": "Content",
            },
            user_context,
        )

    parsed = json.loads(result)
    assert "error" in parsed
    assert parsed["status"] == 500


@pytest.mark.asyncio
async def test_get_meeting_details_passes_email_header(user_context):
    """get_meeting_details passes X-User-Email header on all requests."""
    from app.tools.transcripts import _get_meeting_details

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)

    mock.get = AsyncMock(side_effect=[
        _mock_response(200, {"id": 1, "title": "Meeting"}),
        _mock_response(200, []),
        _mock_response(200, []),
    ])

    with patch("app.tools.transcripts.httpx.AsyncClient", return_value=mock):
        await _get_meeting_details({"meeting_id": 1}, user_context)

    # Verify all GET calls passed the email header
    for call in mock.get.call_args_list:
        headers = call.kwargs.get("headers", {})
        assert headers.get("X-User-Email") == "test@themany.com"
