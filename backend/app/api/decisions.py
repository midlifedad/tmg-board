"""
Decisions API endpoints - Full CRUD for decisions and voting.
"""
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.decision import Decision, Vote
from app.models.audit import AuditLog
from app.api.auth import require_member, require_chair

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class CreateDecisionRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str  # vote/consent/resolution
    visibility: str = "standard"  # standard/anonymous/transparent
    meeting_id: Optional[int] = None
    deadline: Optional[datetime] = None
    resolution_number: Optional[str] = None
    document_id: Optional[int] = None


class UpdateDecisionRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    visibility: Optional[str] = None
    meeting_id: Optional[int] = None
    deadline: Optional[datetime] = None
    resolution_number: Optional[str] = None
    document_id: Optional[int] = None


class ArchiveDecisionRequest(BaseModel):
    reason: Optional[str] = None


class ExtendDeadlineRequest(BaseModel):
    new_deadline: datetime


class CastVoteRequest(BaseModel):
    vote: str  # yes/no/abstain


# =============================================================================
# Decision CRUD
# =============================================================================

@router.get("/")
async def list_decisions(
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    include_archived: bool = Query(False, description="Include archived decisions"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List decisions with optional filtering."""
    query = db.query(Decision).filter(Decision.deleted_at.is_(None))

    if not include_archived:
        query = query.filter(Decision.archived_at.is_(None))

    if status:
        query = query.filter(Decision.status == status)
    if type:
        query = query.filter(Decision.type == type)

    total = query.count()
    decisions = query.order_by(Decision.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": decisions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/archived")
async def list_archived_decisions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List archived decisions."""
    query = db.query(Decision).filter(
        Decision.deleted_at.is_(None),
        Decision.archived_at.isnot(None)
    )

    total = query.count()
    decisions = query.order_by(Decision.archived_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": decisions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{decision_id}")
async def get_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get a single decision with votes."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Get user's vote
    user_vote = db.query(Vote).filter(
        Vote.decision_id == decision_id,
        Vote.member_id == current_user.id
    ).first()

    # Determine if results should be shown based on visibility
    show_results = False
    if decision.status == "closed":
        show_results = True
    elif decision.visibility == "transparent":
        show_results = True
    elif current_user.role in ("admin", "chair"):
        show_results = True

    return {
        "decision": decision,
        "user_vote": user_vote.vote if user_vote else None,
        "results": decision.get_results() if show_results else None
    }


@router.post("/")
async def create_decision(
    request: CreateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Create a new decision (Chair or Admin only)."""
    valid_types = ["vote", "consent", "resolution"]
    if request.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {valid_types}")

    valid_visibility = ["standard", "anonymous", "transparent"]
    if request.visibility not in valid_visibility:
        raise HTTPException(status_code=400, detail=f"Invalid visibility. Must be one of: {valid_visibility}")

    decision = Decision(
        title=request.title,
        description=request.description,
        type=request.type,
        visibility=request.visibility,
        status="draft",
        meeting_id=request.meeting_id,
        deadline=request.deadline,
        resolution_number=request.resolution_number,
        document_id=request.document_id,
        created_by_id=current_user.id
    )

    db.add(decision)

    db.add(AuditLog(
        entity_type="decision",
        entity_id=0,
        entity_name=request.title,
        action="create",
        changed_by_id=current_user.id
    ))

    db.commit()
    db.refresh(decision)

    return decision


@router.patch("/{decision_id}")
async def update_decision(
    decision_id: int,
    request: UpdateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update a decision (Chair or Admin only). Cannot update closed decisions."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status == "closed":
        raise HTTPException(status_code=400, detail="Cannot update closed decision")

    if decision.archived_at:
        raise HTTPException(status_code=400, detail="Cannot update archived decision")

    changes = {}

    if request.title is not None and request.title != decision.title:
        changes["title"] = {"old": decision.title, "new": request.title}
        decision.title = request.title

    if request.description is not None and request.description != decision.description:
        changes["description"] = {"old": decision.description, "new": request.description}
        decision.description = request.description

    if request.type is not None and request.type != decision.type:
        valid_types = ["vote", "consent", "resolution"]
        if request.type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: {valid_types}")
        changes["type"] = {"old": decision.type, "new": request.type}
        decision.type = request.type

    if request.visibility is not None and request.visibility != decision.visibility:
        valid_visibility = ["standard", "anonymous", "transparent"]
        if request.visibility not in valid_visibility:
            raise HTTPException(status_code=400, detail=f"Invalid visibility. Must be one of: {valid_visibility}")
        changes["visibility"] = {"old": decision.visibility, "new": request.visibility}
        decision.visibility = request.visibility

    if request.meeting_id is not None and request.meeting_id != decision.meeting_id:
        changes["meeting_id"] = {"old": decision.meeting_id, "new": request.meeting_id}
        decision.meeting_id = request.meeting_id

    if request.deadline is not None and request.deadline != decision.deadline:
        changes["deadline"] = {"old": str(decision.deadline), "new": str(request.deadline)}
        decision.deadline = request.deadline

    if request.resolution_number is not None and request.resolution_number != decision.resolution_number:
        changes["resolution_number"] = {"old": decision.resolution_number, "new": request.resolution_number}
        decision.resolution_number = request.resolution_number

    if request.document_id is not None and request.document_id != decision.document_id:
        changes["document_id"] = {"old": decision.document_id, "new": request.document_id}
        decision.document_id = request.document_id

    if changes:
        db.add(AuditLog(
            entity_type="decision",
            entity_id=decision_id,
            entity_name=decision.title,
            action="update",
            changed_by_id=current_user.id,
            changes=changes
        ))

    db.commit()
    db.refresh(decision)

    return decision


@router.delete("/{decision_id}")
async def delete_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Soft delete a decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.deleted_at = datetime.utcnow()
    decision.deleted_by_id = current_user.id

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="delete",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "deleted", "id": decision_id}


# =============================================================================
# Decision Lifecycle (Open/Close/Reopen/Archive)
# =============================================================================

@router.post("/{decision_id}/open")
async def open_voting(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Open voting on a decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status == "open":
        raise HTTPException(status_code=400, detail="Decision is already open")

    if decision.archived_at:
        raise HTTPException(status_code=400, detail="Cannot open archived decision")

    decision.status = "open"

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="open",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "open", "id": decision_id}


@router.post("/{decision_id}/close")
async def close_voting(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Close voting on a decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "open":
        raise HTTPException(status_code=400, detail="Decision is not open")

    decision.status = "closed"
    decision.closed_at = datetime.utcnow()

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="close",
        changed_by_id=current_user.id,
        changes={"results": decision.get_results()}
    ))

    db.commit()

    return {"status": "closed", "id": decision_id, "results": decision.get_results()}


@router.post("/{decision_id}/reopen")
async def reopen_voting(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Reopen voting on a closed decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "closed":
        raise HTTPException(status_code=400, detail="Decision is not closed")

    if decision.archived_at:
        raise HTTPException(status_code=400, detail="Cannot reopen archived decision")

    decision.status = "open"
    decision.closed_at = None

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="reopen",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "open", "id": decision_id}


@router.post("/{decision_id}/archive")
async def archive_decision(
    decision_id: int,
    request: ArchiveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Archive a decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.archived_at:
        raise HTTPException(status_code=400, detail="Decision is already archived")

    # Close voting if still open
    if decision.status == "open":
        decision.status = "closed"
        decision.closed_at = datetime.utcnow()

    decision.archived_at = datetime.utcnow()
    decision.archived_by_id = current_user.id
    decision.archived_reason = request.reason

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="archive",
        changed_by_id=current_user.id,
        changes={"reason": request.reason}
    ))

    db.commit()

    return {"status": "archived", "id": decision_id}


@router.post("/{decision_id}/unarchive")
async def unarchive_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Unarchive a decision (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None),
        Decision.archived_at.isnot(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found or not archived")

    decision.archived_at = None
    decision.archived_by_id = None
    decision.archived_reason = None

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="unarchive",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "unarchived", "id": decision_id}


# =============================================================================
# Voting
# =============================================================================

@router.post("/{decision_id}/vote")
async def cast_vote(
    decision_id: int,
    request: CastVoteRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Cast a vote on a decision."""
    if request.vote not in ("yes", "no", "abstain"):
        raise HTTPException(status_code=400, detail="Invalid vote. Must be yes, no, or abstain")

    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "open":
        raise HTTPException(status_code=400, detail="Voting is not open for this decision")

    # Check deadline
    if decision.deadline and datetime.utcnow() > decision.deadline:
        raise HTTPException(status_code=400, detail="Voting deadline has passed")

    # Check if user already voted
    existing_vote = db.query(Vote).filter(
        Vote.decision_id == decision_id,
        Vote.member_id == current_user.id
    ).first()

    if existing_vote:
        old_vote = existing_vote.vote
        existing_vote.vote = request.vote
        existing_vote.cast_at = datetime.utcnow()

        db.add(AuditLog(
            entity_type="vote",
            entity_id=decision_id,
            entity_name=decision.title,
            action="change_vote",
            changed_by_id=current_user.id,
            changes={"old": old_vote, "new": request.vote}
        ))
    else:
        new_vote = Vote(
            decision_id=decision_id,
            member_id=current_user.id,
            vote=request.vote
        )
        db.add(new_vote)

        db.add(AuditLog(
            entity_type="vote",
            entity_id=decision_id,
            entity_name=decision.title,
            action="cast_vote",
            changed_by_id=current_user.id,
            changes={"vote": request.vote}
        ))

    db.commit()

    return {"status": "voted", "vote": request.vote}


@router.get("/{decision_id}/results")
async def get_results(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get voting results for a decision."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Check if results should be visible based on visibility setting
    can_view = False
    if decision.status == "closed":
        can_view = True
    elif decision.visibility == "transparent":
        can_view = True
    elif current_user.role in ("admin", "chair"):
        can_view = True

    if not can_view:
        raise HTTPException(status_code=403, detail="Results not available until voting closes")

    # Get detailed voter breakdown if not anonymous
    voters = None
    if decision.visibility != "anonymous":
        votes = db.query(Vote).filter(Vote.decision_id == decision_id).all()
        voters = [{
            "member_id": v.member_id,
            "member_name": v.member.name if v.member else None,
            "vote": v.vote,
            "cast_at": v.cast_at
        } for v in votes]

    return {
        "decision_id": decision_id,
        "status": decision.status,
        "visibility": decision.visibility,
        "results": decision.get_results(),
        "voters": voters
    }


# =============================================================================
# Deadline Extension and Reminders
# =============================================================================

@router.post("/{decision_id}/extend")
async def extend_deadline(
    decision_id: int,
    request: ExtendDeadlineRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Extend the voting deadline (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "open":
        raise HTTPException(status_code=400, detail="Can only extend deadline for open decisions")

    old_deadline = decision.deadline
    decision.deadline = request.new_deadline

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="extend_deadline",
        changed_by_id=current_user.id,
        changes={"old_deadline": str(old_deadline), "new_deadline": str(request.new_deadline)}
    ))

    db.commit()

    return {
        "status": "extended",
        "id": decision_id,
        "old_deadline": old_deadline,
        "new_deadline": request.new_deadline
    }


@router.post("/{decision_id}/remind")
async def send_reminder(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Send reminder to members who haven't voted (Chair or Admin only)."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "open":
        raise HTTPException(status_code=400, detail="Can only send reminders for open decisions")

    # Get members who have voted
    voted_member_ids = {v.member_id for v in decision.votes}

    # Get all active members
    all_members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None)
    ).all()

    pending_members = [m for m in all_members if m.id not in voted_member_ids]

    db.add(AuditLog(
        entity_type="decision",
        entity_id=decision_id,
        entity_name=decision.title,
        action="send_reminder",
        changed_by_id=current_user.id,
        changes={"pending_count": len(pending_members)}
    ))

    db.commit()

    # TODO: Integrate with email service to actually send reminders
    # For now, just return the list of pending members

    return {
        "status": "reminder_queued",
        "decision_id": decision_id,
        "pending_count": len(pending_members),
        "pending_members": [{"id": m.id, "name": m.name, "email": m.email} for m in pending_members]
    }


# =============================================================================
# Audit Trail
# =============================================================================

@router.get("/{decision_id}/audit")
async def get_decision_audit(
    decision_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get audit trail for a decision."""
    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    logs = db.query(AuditLog).filter(
        AuditLog.entity_type.in_(["decision", "vote"]),
        AuditLog.entity_id == decision_id
    ).order_by(AuditLog.changed_at.desc()).limit(limit).all()

    return [{
        "id": log.id,
        "action": log.action,
        "changed_by_id": log.changed_by_id,
        "changed_by_name": log.changed_by.name if log.changed_by else None,
        "changed_at": log.changed_at,
        "changes": log.changes
    } for log in logs]
