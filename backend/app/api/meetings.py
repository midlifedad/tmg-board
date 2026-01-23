from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.meeting import Meeting, AgendaItem, MeetingAttendance
from app.api.auth import require_member, require_chair

router = APIRouter()


@router.get("/")
async def list_meetings(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List meetings with optional filtering."""
    query = db.query(Meeting).filter(Meeting.deleted_at.is_(None))

    if status:
        query = query.filter(Meeting.status == status)

    total = query.count()
    meetings = query.order_by(Meeting.scheduled_date.desc()).offset(offset).limit(limit).all()

    return {
        "items": meetings,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get a single meeting with agenda."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return meeting


@router.post("/")
async def create_meeting(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Schedule a new meeting (Chair or Admin only)."""
    # TODO: Implement meeting creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{meeting_id}")
async def update_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update a meeting (Chair or Admin only)."""
    # TODO: Implement meeting update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{meeting_id}")
async def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Cancel a meeting (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.status = "cancelled"
    db.commit()

    return {"status": "cancelled", "id": meeting_id}


# Agenda endpoints

@router.get("/{meeting_id}/agenda")
async def get_agenda(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get agenda items for a meeting."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return meeting.agenda_items


@router.post("/{meeting_id}/agenda")
async def add_agenda_item(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Add an agenda item (Chair or Admin only)."""
    # TODO: Implement agenda item creation
    raise HTTPException(status_code=501, detail="Not implemented")


# Attendance endpoints

@router.get("/{meeting_id}/attendance")
async def get_attendance(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get attendance records for a meeting."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return meeting.attendance


@router.post("/{meeting_id}/attendance")
async def record_attendance(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Record attendance for a meeting (Chair or Admin only)."""
    # TODO: Implement attendance recording
    raise HTTPException(status_code=501, detail="Not implemented")
