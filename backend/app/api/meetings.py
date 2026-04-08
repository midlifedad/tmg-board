"""
Meetings API endpoints - Full CRUD for meetings, agenda items, attendance, and minutes.
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.meeting import Meeting, AgendaItem, MeetingAttendance, MeetingDocument
from app.models.document import Document
from app.models.audit import AuditLog
from app.api.auth import require_member, require_chair

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class CreateMeetingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: datetime = Field(..., alias="date")  # Accept 'date' from frontend
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both 'date' and 'scheduled_date'


class UpdateMeetingRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class CreateAgendaItemRequest(BaseModel):
    title: str
    description: Optional[str] = None
    item_type: Optional[str] = "information"  # information, discussion, decision_required, consent_agenda
    duration_minutes: Optional[int] = None
    presenter_id: Optional[int] = None
    decision_id: Optional[int] = None


class UpdateAgendaItemRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None  # information, discussion, decision_required, consent_agenda
    duration_minutes: Optional[int] = None
    presenter_id: Optional[int] = None
    decision_id: Optional[int] = None


class AgendaItemInput(BaseModel):
    title: str
    description: Optional[str] = None
    item_type: str = "information"
    duration_minutes: Optional[int] = None
    presenter_id: Optional[int] = None


class CreateMeetingWithAgendaRequest(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: datetime = Field(..., alias="date")
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    template_id: Optional[int] = None
    agenda_items: Optional[List[AgendaItemInput]] = None

    class Config:
        populate_by_name = True


class ReorderAgendaRequest(BaseModel):
    item_ids: List[int]  # Ordered list of agenda item IDs


class AttendanceRecord(BaseModel):
    member_id: int
    status: str  # present/absent/excused


class RecordAttendanceRequest(BaseModel):
    attendance: List[AttendanceRecord]


class UpdateAttendanceRequest(BaseModel):
    status: str  # present/absent/excused
    notes: Optional[str] = None


# =============================================================================
# Meeting CRUD
# =============================================================================

@router.get("/members")
async def list_members(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List active board members (id and name only) for presenter dropdowns."""
    members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None)
    ).order_by(BoardMember.name).all()
    return [{"id": m.id, "name": m.name} for m in members]


@router.get("")
async def list_meetings(
    status: Optional[str] = Query(None, description="Filter by status"),
    upcoming: bool = Query(False, description="Only show upcoming meetings"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List meetings with optional filtering."""
    query = db.query(Meeting).filter(Meeting.deleted_at.is_(None))

    if status:
        query = query.filter(Meeting.status == status)

    if upcoming:
        query = query.filter(
            Meeting.scheduled_date >= datetime.utcnow(),
            Meeting.status.in_(["scheduled", "in_progress"])
        )

    total = query.count()
    meetings = query.order_by(Meeting.scheduled_date.desc()).offset(offset).limit(limit).all()

    result_items = []
    for meeting in meetings:
        item_dict = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "scheduled_date": meeting.scheduled_date.isoformat() if meeting.scheduled_date else None,
            "duration_minutes": meeting.duration_minutes,
            "location": meeting.location,
            "meeting_link": meeting.meeting_link,
            "status": meeting.status,
            "created_by_id": meeting.created_by_id,
            "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
            "agenda_items_count": len(meeting.agenda_items),
            "has_minutes": meeting.status == "completed",
            "decisions_count": sum(1 for item in meeting.agenda_items if item.decision_id is not None),
        }
        result_items.append(item_dict)

    return {
        "items": result_items,
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


@router.post("/with-agenda")
async def create_meeting_with_agenda(
    request: CreateMeetingWithAgendaRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Create a meeting with agenda items in a single call (Chair/Board/Admin)."""
    meeting = Meeting(
        title=request.title,
        description=request.description,
        scheduled_date=request.scheduled_date,
        duration_minutes=request.duration_minutes,
        location=request.location,
        meeting_link=request.meeting_link,
        status="scheduled",
        created_by_id=current_user.id,
    )
    db.add(meeting)
    db.flush()  # Get meeting ID

    agenda_items_data = []

    if request.agenda_items:
        agenda_items_data = request.agenda_items
    elif request.template_id:
        # Load template and populate from it
        from app.models.template import MeetingTemplate
        template = db.query(MeetingTemplate).filter(
            MeetingTemplate.id == request.template_id,
            MeetingTemplate.is_active == True,
        ).first()
        if template:
            for t_item in template.items:
                agenda_items_data.append(AgendaItemInput(
                    title=t_item.title,
                    description=t_item.description,
                    item_type=t_item.item_type,
                    duration_minutes=t_item.duration_minutes,
                ))

    for idx, item_input in enumerate(agenda_items_data):
        item = AgendaItem(
            meeting_id=meeting.id,
            title=item_input.title,
            description=item_input.description,
            item_type=item_input.item_type,
            duration_minutes=item_input.duration_minutes,
            presenter_id=item_input.presenter_id,
            order_index=idx,
        )
        db.add(item)

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=meeting.id,
        entity_name=request.title,
        action="create",
        changed_by_id=current_user.id,
    ))

    db.commit()
    db.refresh(meeting)

    # Return meeting with agenda items
    return {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "scheduled_date": meeting.scheduled_date.isoformat() if meeting.scheduled_date else None,
        "duration_minutes": meeting.duration_minutes,
        "location": meeting.location,
        "meeting_link": meeting.meeting_link,
        "status": meeting.status,
        "created_by_id": meeting.created_by_id,
        "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
        "agenda_items": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "item_type": item.item_type,
                "duration_minutes": item.duration_minutes,
                "presenter_id": item.presenter_id,
                "order_index": item.order_index,
            }
            for item in meeting.agenda_items
        ],
    }


@router.post("")
async def create_meeting(
    request: CreateMeetingRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Schedule a new meeting (Chair or Admin only)."""
    meeting = Meeting(
        title=request.title,
        description=request.description,
        scheduled_date=request.scheduled_date,
        duration_minutes=request.duration_minutes,
        location=request.location,
        meeting_link=request.meeting_link,
        status="scheduled",
        created_by_id=current_user.id
    )

    db.add(meeting)

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=0,  # Will be set after commit
        entity_name=request.title,
        action="create",
        changed_by_id=current_user.id
    ))

    db.commit()
    db.refresh(meeting)

    return meeting


@router.patch("/{meeting_id}")
async def update_meeting(
    meeting_id: int,
    request: UpdateMeetingRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update a meeting (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot update completed meeting")

    changes = {}

    if request.title is not None and request.title != meeting.title:
        changes["title"] = {"old": meeting.title, "new": request.title}
        meeting.title = request.title

    if request.description is not None and request.description != meeting.description:
        changes["description"] = {"old": meeting.description, "new": request.description}
        meeting.description = request.description

    if request.scheduled_date is not None and request.scheduled_date != meeting.scheduled_date:
        changes["scheduled_date"] = {"old": str(meeting.scheduled_date), "new": str(request.scheduled_date)}
        meeting.scheduled_date = request.scheduled_date

    if request.duration_minutes is not None and request.duration_minutes != meeting.duration_minutes:
        changes["duration_minutes"] = {"old": meeting.duration_minutes, "new": request.duration_minutes}
        meeting.duration_minutes = request.duration_minutes

    if request.location is not None and request.location != meeting.location:
        changes["location"] = {"old": meeting.location, "new": request.location}
        meeting.location = request.location

    if request.meeting_link is not None and request.meeting_link != meeting.meeting_link:
        changes["meeting_link"] = {"old": meeting.meeting_link, "new": request.meeting_link}
        meeting.meeting_link = request.meeting_link

    if changes:
        db.add(AuditLog(
            entity_type="meeting",
            entity_id=meeting_id,
            entity_name=meeting.title,
            action="update",
            changed_by_id=current_user.id,
            changes=changes
        ))

    db.commit()
    db.refresh(meeting)

    return meeting


@router.delete("/{meeting_id}")
async def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Cancel a meeting (Chair or Admin only). Sets status to cancelled."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed meeting")

    if meeting.status == "cancelled":
        raise HTTPException(status_code=400, detail="Meeting is already cancelled")

    meeting.status = "cancelled"

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="cancel",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "cancelled", "id": meeting_id}


# =============================================================================
# Meeting Lifecycle (Start/End)
# =============================================================================

@router.post("/{meeting_id}/start")
async def start_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Start a meeting (set status to in_progress)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != "scheduled":
        raise HTTPException(status_code=400, detail=f"Cannot start meeting with status '{meeting.status}'")

    meeting.status = "in_progress"
    meeting.started_at = datetime.utcnow()

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="start",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "in_progress", "id": meeting_id, "started_at": meeting.started_at}


@router.post("/{meeting_id}/end")
async def end_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """End a meeting (set status to completed)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Cannot end meeting with status '{meeting.status}'")

    meeting.status = "completed"
    meeting.ended_at = datetime.utcnow()

    db.add(AuditLog(
        entity_type="meeting",
        entity_id=meeting_id,
        entity_name=meeting.title,
        action="end",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "completed", "id": meeting_id, "ended_at": meeting.ended_at}


# =============================================================================
# Agenda Item CRUD
# =============================================================================

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

    items = db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id
    ).order_by(AgendaItem.order_index).all()

    result = []
    for item in items:
        item_dict = {
            "id": item.id,
            "meeting_id": item.meeting_id,
            "title": item.title,
            "description": item.description,
            "duration_minutes": item.duration_minutes,
            "order_index": item.order_index,
            "item_type": item.item_type,
            "presenter_id": item.presenter_id,
            "presenter": item.presenter.name if item.presenter else None,
            "decision_id": item.decision_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        result.append(item_dict)
    return result


@router.post("/{meeting_id}/agenda")
async def add_agenda_item(
    meeting_id: int,
    request: CreateAgendaItemRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Add an agenda item (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot add agenda to completed meeting")

    # Get next order index
    max_order = db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id
    ).count()

    item = AgendaItem(
        meeting_id=meeting_id,
        title=request.title,
        description=request.description,
        item_type=request.item_type,
        duration_minutes=request.duration_minutes,
        presenter_id=request.presenter_id,
        decision_id=request.decision_id,
        order_index=max_order
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.patch("/{meeting_id}/agenda/reorder")
async def reorder_agenda(
    meeting_id: int,
    request: ReorderAgendaRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Reorder agenda items (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot reorder agenda of completed meeting")

    # Verify all item IDs belong to this meeting
    items = db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id
    ).all()

    item_map = {item.id: item for item in items}

    if set(request.item_ids) != set(item_map.keys()):
        raise HTTPException(status_code=400, detail="Item IDs must match all agenda items for this meeting")

    # Update order
    for new_index, item_id in enumerate(request.item_ids):
        item_map[item_id].order_index = new_index

    db.commit()

    # Return reordered items
    return db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id
    ).order_by(AgendaItem.order_index).all()


@router.patch("/{meeting_id}/agenda/{item_id}")
async def update_agenda_item(
    meeting_id: int,
    item_id: int,
    request: UpdateAgendaItemRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update an agenda item (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    item = db.query(AgendaItem).filter(
        AgendaItem.id == item_id,
        AgendaItem.meeting_id == meeting_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Agenda item not found")

    if request.title is not None:
        item.title = request.title
    if request.description is not None:
        item.description = request.description
    if request.item_type is not None:
        item.item_type = request.item_type
    if request.duration_minutes is not None:
        item.duration_minutes = request.duration_minutes
    if request.presenter_id is not None:
        item.presenter_id = request.presenter_id
    if request.decision_id is not None:
        item.decision_id = request.decision_id

    db.commit()
    db.refresh(item)

    return item


@router.delete("/{meeting_id}/agenda/{item_id}")
async def delete_agenda_item(
    meeting_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Delete an agenda item (Chair or Admin only)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot modify agenda of completed meeting")

    item = db.query(AgendaItem).filter(
        AgendaItem.id == item_id,
        AgendaItem.meeting_id == meeting_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Agenda item not found")

    deleted_order = item.order_index
    db.delete(item)

    # Reorder remaining items
    remaining = db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id,
        AgendaItem.order_index > deleted_order
    ).all()

    for remaining_item in remaining:
        remaining_item.order_index -= 1

    db.commit()

    return {"status": "deleted", "id": item_id}


# =============================================================================
# Attendance Tracking
# =============================================================================

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

    # Get attendance with member info
    attendance = db.query(MeetingAttendance).filter(
        MeetingAttendance.meeting_id == meeting_id
    ).all()

    result = []
    for record in attendance:
        result.append({
            "meeting_id": record.meeting_id,
            "member_id": record.member_id,
            "member_name": record.member.name if record.member else None,
            "status": record.status,
            "joined_at": record.joined_at,
            "left_at": record.left_at
        })

    return result


@router.post("/{meeting_id}/attendance")
async def record_attendance(
    meeting_id: int,
    request: RecordAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Record attendance for a meeting (batch operation)."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    valid_statuses = ["present", "absent", "excused"]

    for record in request.attendance:
        if record.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{record.status}'. Must be one of: {valid_statuses}"
            )

        # Check if member exists
        member = db.query(BoardMember).filter(
            BoardMember.id == record.member_id,
            BoardMember.deleted_at.is_(None)
        ).first()

        if not member:
            raise HTTPException(status_code=404, detail=f"Member {record.member_id} not found")

        # Upsert attendance record
        existing = db.query(MeetingAttendance).filter(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.member_id == record.member_id
        ).first()

        if existing:
            existing.status = record.status
            if record.status == "present" and not existing.joined_at:
                existing.joined_at = datetime.utcnow()
        else:
            attendance = MeetingAttendance(
                meeting_id=meeting_id,
                member_id=record.member_id,
                status=record.status,
                joined_at=datetime.utcnow() if record.status == "present" else None
            )
            db.add(attendance)

    db.commit()

    return {"status": "recorded", "count": len(request.attendance)}


@router.patch("/{meeting_id}/attendance/{member_id}")
async def update_attendance(
    meeting_id: int,
    member_id: int,
    request: UpdateAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update attendance for a single member."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    valid_statuses = ["present", "absent", "excused"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{request.status}'. Must be one of: {valid_statuses}"
        )

    attendance = db.query(MeetingAttendance).filter(
        MeetingAttendance.meeting_id == meeting_id,
        MeetingAttendance.member_id == member_id
    ).first()

    if not attendance:
        # Create new record
        member = db.query(BoardMember).filter(
            BoardMember.id == member_id,
            BoardMember.deleted_at.is_(None)
        ).first()

        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        attendance = MeetingAttendance(
            meeting_id=meeting_id,
            member_id=member_id,
            status=request.status,
            joined_at=datetime.utcnow() if request.status == "present" else None
        )
        db.add(attendance)
    else:
        old_status = attendance.status
        attendance.status = request.status

        # Track join/leave times
        if request.status == "present" and old_status != "present":
            attendance.joined_at = datetime.utcnow()
        elif request.status != "present" and old_status == "present":
            attendance.left_at = datetime.utcnow()

    db.commit()

    return {
        "meeting_id": meeting_id,
        "member_id": member_id,
        "status": request.status
    }


# =============================================================================
# Meeting Minutes
# =============================================================================

class CreateMinutesRequest(BaseModel):
    html_content: str
    title: str


@router.post("/{meeting_id}/minutes")
async def create_meeting_minutes(
    meeting_id: int,
    request: CreateMinutesRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Create or update minutes for a completed meeting.

    Creates a Document of type 'minutes' and links it via MeetingDocument.
    If minutes already exist for this meeting, updates the existing document.
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Check if minutes already exist for this meeting (upsert logic)
    existing_link = db.query(MeetingDocument).filter(
        MeetingDocument.meeting_id == meeting_id,
        MeetingDocument.relationship_type == "minutes",
    ).first()

    if existing_link:
        # Update existing minutes document
        doc = db.query(Document).filter(Document.id == existing_link.document_id).first()
        if doc:
            doc.title = request.title
            doc.file_path = f"minutes://{meeting_id}"  # Virtual path for HTML-stored minutes
            doc.description = request.html_content
            doc.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(doc)

            db.add(AuditLog(
                entity_type="document",
                entity_id=doc.id,
                entity_name=request.title,
                action="update_minutes",
                changed_by_id=current_user.id,
            ))
            db.commit()

            return {
                "document_id": doc.id,
                "meeting_id": meeting_id,
                "title": doc.title,
                "status": "updated",
            }

    # Create new minutes document
    doc = Document(
        title=request.title,
        type="minutes",
        description=request.html_content,
        file_path=f"minutes://{meeting_id}",
        uploaded_by_id=current_user.id,
    )
    db.add(doc)
    db.flush()  # Get document ID

    # Link document to meeting
    link = MeetingDocument(
        meeting_id=meeting_id,
        document_id=doc.id,
        relationship_type="minutes",
        created_by_id=current_user.id,
    )
    db.add(link)

    db.add(AuditLog(
        entity_type="document",
        entity_id=doc.id,
        entity_name=request.title,
        action="create_minutes",
        changed_by_id=current_user.id,
    ))

    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "meeting_id": meeting_id,
        "title": doc.title,
        "status": "created",
    }


@router.get("/{meeting_id}/minutes")
async def get_meeting_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get the minutes document for a meeting.

    Returns the HTML content and metadata, or 404 if no minutes exist.
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None)
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Look up minutes document via MeetingDocument junction
    link = db.query(MeetingDocument).filter(
        MeetingDocument.meeting_id == meeting_id,
        MeetingDocument.relationship_type == "minutes",
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="No minutes found for this meeting")

    doc = db.query(Document).filter(Document.id == link.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Minutes document not found")

    return {
        "document_id": doc.id,
        "meeting_id": meeting_id,
        "title": doc.title,
        "html_content": doc.description or "",
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
