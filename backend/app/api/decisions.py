from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.decision import Decision, Vote
from app.api.auth import require_member, require_chair

router = APIRouter()


@router.get("/")
async def list_decisions(
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List decisions with optional filtering."""
    query = db.query(Decision).filter(Decision.deleted_at.is_(None))

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

    return {
        "decision": decision,
        "user_vote": user_vote.vote if user_vote else None,
        "results": decision.get_results() if decision.status == "closed" or current_user.is_chair else None
    }


@router.post("/")
async def create_decision(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Create a new decision (Chair or Admin only)."""
    # TODO: Implement decision creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{decision_id}")
async def update_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Update a decision (Chair or Admin only)."""
    # TODO: Implement decision update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{decision_id}/vote")
async def cast_vote(
    decision_id: int,
    vote: str,  # yes/no/abstain
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Cast a vote on a decision."""
    if vote not in ("yes", "no", "abstain"):
        raise HTTPException(status_code=400, detail="Invalid vote. Must be yes, no, or abstain")

    decision = db.query(Decision).filter(
        Decision.id == decision_id,
        Decision.deleted_at.is_(None)
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "open":
        raise HTTPException(status_code=400, detail="Voting is not open for this decision")

    # Check if user already voted
    existing_vote = db.query(Vote).filter(
        Vote.decision_id == decision_id,
        Vote.member_id == current_user.id
    ).first()

    if existing_vote:
        # Update existing vote
        existing_vote.vote = vote
        from datetime import datetime
        existing_vote.cast_at = datetime.utcnow()
    else:
        # Create new vote
        new_vote = Vote(
            decision_id=decision_id,
            member_id=current_user.id,
            vote=vote
        )
        db.add(new_vote)

    db.commit()

    return {"status": "voted", "vote": vote}


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

    # Only show results if closed or if user is chair/admin
    if decision.status != "closed" and not current_user.is_chair:
        raise HTTPException(status_code=403, detail="Results not available until voting closes")

    return {
        "decision_id": decision_id,
        "status": decision.status,
        "results": decision.get_results()
    }


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

    from datetime import datetime
    decision.status = "closed"
    decision.closed_at = datetime.utcnow()
    db.commit()

    return {"status": "closed", "results": decision.get_results()}
