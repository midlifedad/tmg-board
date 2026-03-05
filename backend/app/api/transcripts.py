"""Transcript API endpoints - CRUD for meeting transcripts."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.meeting import Meeting, MeetingTranscript
from app.models.audit import AuditLog
from app.api.auth import require_member, require_chair

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class CreateTranscriptRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=5_000_000)


class ReplaceTranscriptRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=5_000_000)


class TranscriptResponse(BaseModel):
    id: int
    meeting_id: int
    content: str
    source: str
    original_filename: Optional[str] = None
    char_count: int
    created_by_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# =============================================================================
# Helper
# =============================================================================

def _get_completed_meeting(db: Session, meeting_id: int) -> Meeting:
    """Get a meeting that exists, is not deleted, and is completed."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Transcripts can only be added to completed meetings",
        )
    return meeting


def _transcript_to_dict(t: MeetingTranscript) -> dict:
    """Convert a MeetingTranscript to a JSON-serializable dict."""
    return {
        "id": t.id,
        "meeting_id": t.meeting_id,
        "content": t.content,
        "source": t.source,
        "original_filename": t.original_filename,
        "char_count": t.char_count,
        "created_by_id": t.created_by_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/{meeting_id}/transcript")
async def add_transcript(
    meeting_id: int,
    request: CreateTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Add a transcript to a completed meeting (paste). Chair/Admin only."""
    meeting = _get_completed_meeting(db, meeting_id)

    existing = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Transcript already exists for this meeting. Use PUT to replace.",
        )

    transcript = MeetingTranscript(
        meeting_id=meeting_id,
        content=request.content,
        source="paste",
        char_count=len(request.content),
        created_by_id=current_user.id,
    )
    db.add(transcript)

    db.add(AuditLog(
        entity_type="transcript",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="create",
        changed_by_id=current_user.id,
        changes={"source": "paste", "char_count": len(request.content)},
    ))

    db.commit()
    db.refresh(transcript)
    return _transcript_to_dict(transcript)


@router.post("/{meeting_id}/transcript/upload")
async def upload_transcript(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Upload a .txt transcript file for a completed meeting. Chair/Admin only."""
    meeting = _get_completed_meeting(db, meeting_id)

    existing = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Transcript already exists for this meeting. Use PUT to replace.",
        )

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted")

    # Read and decode
    raw = await file.read()
    if len(raw) > 5_000_000:  # 5MB limit
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    transcript = MeetingTranscript(
        meeting_id=meeting_id,
        content=content,
        source="upload",
        original_filename=file.filename,
        char_count=len(content),
        created_by_id=current_user.id,
    )
    db.add(transcript)

    db.add(AuditLog(
        entity_type="transcript",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="create",
        changed_by_id=current_user.id,
        changes={"source": "upload", "filename": file.filename, "char_count": len(content)},
    ))

    db.commit()
    db.refresh(transcript)
    return _transcript_to_dict(transcript)


@router.get("/{meeting_id}/transcript")
async def get_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """View a meeting's transcript. Any board member."""
    # Verify meeting exists
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found for this meeting")

    return _transcript_to_dict(transcript)


@router.put("/{meeting_id}/transcript")
async def replace_transcript(
    meeting_id: int,
    request: ReplaceTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Replace transcript content. Chair/Admin only."""
    # Verify meeting exists
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found for this meeting")

    old_count = transcript.char_count
    transcript.content = request.content
    transcript.char_count = len(request.content)
    transcript.updated_at = datetime.utcnow()

    db.add(AuditLog(
        entity_type="transcript",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="update",
        changed_by_id=current_user.id,
        changes={"old_char_count": old_count, "new_char_count": len(request.content)},
    ))

    db.commit()
    db.refresh(transcript)
    return _transcript_to_dict(transcript)


@router.delete("/{meeting_id}/transcript")
async def delete_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Delete a meeting's transcript. Chair/Admin only."""
    # Verify meeting exists
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = db.query(MeetingTranscript).filter(
        MeetingTranscript.meeting_id == meeting_id
    ).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found for this meeting")

    db.delete(transcript)

    db.add(AuditLog(
        entity_type="transcript",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="delete",
        changed_by_id=current_user.id,
    ))

    db.commit()
    return {"status": "deleted"}
