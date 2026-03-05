"""Tests for transcript management: models, API endpoints, and recording_url removal."""
from __future__ import annotations

import pytest
from datetime import datetime


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def seed_completed_meeting(db_session, seed_user):
    """Create a completed meeting for transcript tests."""
    from app.models.meeting import Meeting
    meeting = Meeting(
        title="Board Meeting Q1",
        scheduled_date=datetime(2026, 1, 15, 10, 0),
        status="completed",
        created_by_id=seed_user.id,
        started_at=datetime(2026, 1, 15, 10, 0),
        ended_at=datetime(2026, 1, 15, 11, 0),
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


# =============================================================================
# Task 1 Tests: Models and recording_url removal
# =============================================================================

def test_meeting_transcript_model_exists(db_session):
    """MeetingTranscript model can be imported and has expected fields."""
    from app.models.meeting import MeetingTranscript
    assert hasattr(MeetingTranscript, "id")
    assert hasattr(MeetingTranscript, "meeting_id")
    assert hasattr(MeetingTranscript, "content")
    assert hasattr(MeetingTranscript, "source")
    assert hasattr(MeetingTranscript, "original_filename")
    assert hasattr(MeetingTranscript, "char_count")
    assert hasattr(MeetingTranscript, "created_by_id")
    assert hasattr(MeetingTranscript, "created_at")
    assert hasattr(MeetingTranscript, "updated_at")


def test_meeting_document_model_exists(db_session):
    """MeetingDocument model can be imported and has expected fields."""
    from app.models.meeting import MeetingDocument
    assert hasattr(MeetingDocument, "meeting_id")
    assert hasattr(MeetingDocument, "document_id")
    assert hasattr(MeetingDocument, "relationship_type")
    assert hasattr(MeetingDocument, "created_by_id")
    assert hasattr(MeetingDocument, "created_at")


def test_meeting_transcript_create(db_session, seed_user, seed_completed_meeting):
    """Can create a MeetingTranscript record."""
    from app.models.meeting import MeetingTranscript
    transcript = MeetingTranscript(
        meeting_id=seed_completed_meeting.id,
        content="This is the transcript text for the meeting.",
        source="paste",
        char_count=45,
        created_by_id=seed_user.id,
    )
    db_session.add(transcript)
    db_session.commit()
    db_session.refresh(transcript)

    assert transcript.id is not None
    assert transcript.meeting_id == seed_completed_meeting.id
    assert transcript.source == "paste"
    assert transcript.char_count == 45


def test_recording_url_removed_from_model():
    """Meeting model no longer has recording_url attribute."""
    from app.models.meeting import Meeting
    assert not hasattr(Meeting, "recording_url"), "recording_url should be removed from Meeting model"


def test_recording_url_removed_from_schema():
    """UpdateMeetingRequest no longer has recording_url field."""
    from app.api.meetings import UpdateMeetingRequest
    fields = UpdateMeetingRequest.model_fields
    assert "recording_url" not in fields, "recording_url should be removed from UpdateMeetingRequest"


def test_models_importable_from_init():
    """MeetingTranscript and MeetingDocument are importable from app.models."""
    from app.models import MeetingTranscript, MeetingDocument
    assert MeetingTranscript is not None
    assert MeetingDocument is not None


# =============================================================================
# Task 2 Tests: Transcript API endpoints
# =============================================================================

@pytest.mark.anyio
async def test_paste_transcript(client, db_session, seed_user, seed_completed_meeting):
    """POST /api/meetings/{id}/transcript with JSON body creates transcript."""
    response = await client.post(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        json={"content": "This is the full transcript of the board meeting. It contains important discussions."},
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "This is the full transcript of the board meeting. It contains important discussions."
    assert data["source"] == "paste"
    assert data["char_count"] == len("This is the full transcript of the board meeting. It contains important discussions.")


@pytest.mark.anyio
async def test_paste_transcript_not_completed(client, db_session, seed_user):
    """POST transcript on a non-completed meeting returns 400."""
    from app.models.meeting import Meeting
    meeting = Meeting(
        title="Scheduled Meeting",
        scheduled_date=datetime(2026, 2, 15, 10, 0),
        status="scheduled",
        created_by_id=seed_user.id,
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    response = await client.post(
        f"/api/meetings/{meeting.id}/transcript",
        json={"content": "This is some transcript text content."},
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_paste_transcript_duplicate(client, db_session, seed_user, seed_completed_meeting):
    """POST transcript twice returns 400 on second attempt."""
    body = {"content": "First transcript content for the meeting."}
    headers = {"X-User-Email": seed_user.email}

    resp1 = await client.post(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        json=body,
        headers=headers,
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        json=body,
        headers=headers,
    )
    assert resp2.status_code == 400


@pytest.mark.anyio
async def test_upload_transcript(client, db_session, seed_user, seed_completed_meeting):
    """POST /api/meetings/{id}/transcript/upload with .txt file creates transcript."""
    file_content = b"This is uploaded transcript content from a file."
    response = await client.post(
        f"/api/meetings/{seed_completed_meeting.id}/transcript/upload",
        files={"file": ("meeting_transcript.txt", file_content, "text/plain")},
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "upload"
    assert data["original_filename"] == "meeting_transcript.txt"
    assert "uploaded transcript content" in data["content"]


@pytest.mark.anyio
async def test_upload_non_txt_rejected(client, db_session, seed_user, seed_completed_meeting):
    """POST upload with non-.txt file returns 400."""
    response = await client.post(
        f"/api/meetings/{seed_completed_meeting.id}/transcript/upload",
        files={"file": ("notes.pdf", b"fake pdf content", "application/pdf")},
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_view_transcript(client, db_session, seed_user, seed_completed_meeting):
    """GET /api/meetings/{id}/transcript returns the transcript."""
    # First create a transcript
    from app.models.meeting import MeetingTranscript
    transcript = MeetingTranscript(
        meeting_id=seed_completed_meeting.id,
        content="Transcript for viewing test content.",
        source="paste",
        char_count=35,
        created_by_id=seed_user.id,
    )
    db_session.add(transcript)
    db_session.commit()

    response = await client.get(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Transcript for viewing" in data["content"]


@pytest.mark.anyio
async def test_view_transcript_not_found(client, db_session, seed_user, seed_completed_meeting):
    """GET transcript for meeting with no transcript returns 404."""
    response = await client.get(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_replace_transcript(client, db_session, seed_user, seed_completed_meeting):
    """PUT /api/meetings/{id}/transcript replaces content."""
    from app.models.meeting import MeetingTranscript
    transcript = MeetingTranscript(
        meeting_id=seed_completed_meeting.id,
        content="Original transcript content here.",
        source="paste",
        char_count=33,
        created_by_id=seed_user.id,
    )
    db_session.add(transcript)
    db_session.commit()

    response = await client.put(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        json={"content": "Updated transcript content with corrections applied."},
        headers={"X-User-Email": seed_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Updated transcript" in data["content"]
    assert data["char_count"] == len("Updated transcript content with corrections applied.")


@pytest.mark.anyio
async def test_delete_transcript(client, db_session, seed_user, seed_completed_meeting):
    """DELETE /api/meetings/{id}/transcript removes it, then GET returns 404."""
    from app.models.meeting import MeetingTranscript
    transcript = MeetingTranscript(
        meeting_id=seed_completed_meeting.id,
        content="Transcript to be deleted content.",
        source="paste",
        char_count=33,
        created_by_id=seed_user.id,
    )
    db_session.add(transcript)
    db_session.commit()

    headers = {"X-User-Email": seed_user.email}

    del_resp = await client.delete(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        headers=headers,
    )
    assert del_resp.status_code == 200

    get_resp = await client.get(
        f"/api/meetings/{seed_completed_meeting.id}/transcript",
        headers=headers,
    )
    assert get_resp.status_code == 404
