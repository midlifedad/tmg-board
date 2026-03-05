"""
Resolutions API endpoints - list, detail, sign, and signature status
for decisions with type=resolution.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.decision import Decision, ResolutionSignature, generate_signature_hash
from app.models.audit import AuditLog
from app.api.auth import require_member

router = APIRouter()


def _decision_to_dict(d: Decision) -> dict:
    """Convert a Decision model to a plain dict for JSON response."""
    return {
        "id": d.id,
        "title": d.title,
        "description": d.description,
        "type": d.type,
        "status": d.status,
        "visibility": d.visibility,
        "resolution_number": d.resolution_number,
        "document_id": d.document_id,
        "meeting_id": d.meeting_id,
        "created_by_id": d.created_by_id,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        "closed_at": d.closed_at.isoformat() if d.closed_at else None,
    }


def _auto_resolution_number(db: Session, decision: Decision) -> str:
    """Generate a YYYY-NNN resolution number if missing."""
    year = decision.created_at.year if decision.created_at else datetime.utcnow().year
    count = db.query(Decision).filter(
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
        Decision.resolution_number.isnot(None),
        Decision.resolution_number != "",
    ).count()
    return f"{year}-{count + 1:03d}"


# =============================================================================
# List resolutions
# =============================================================================

@router.get("")
async def list_resolutions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """List resolutions (decisions with type=resolution)."""
    query = db.query(Decision).filter(
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
        Decision.archived_at.is_(None),
    )
    if status:
        query = query.filter(Decision.status == status)

    total = query.count()
    resolutions = query.order_by(Decision.created_at.desc()).offset(offset).limit(limit).all()

    # Count total board-level members (reused across items)
    total_members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None),
        BoardMember.role.in_(["board", "chair", "admin"]),
    ).count()

    items = []
    for r in resolutions:
        # Auto-generate resolution_number if missing
        if not r.resolution_number:
            r.resolution_number = _auto_resolution_number(db, r)
            db.commit()

        sig_count = db.query(ResolutionSignature).filter(
            ResolutionSignature.decision_id == r.id
        ).count()
        items.append({
            **_decision_to_dict(r),
            "signature_count": sig_count,
            "total_signers": total_members,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


# =============================================================================
# Get resolution detail
# =============================================================================

@router.get("/{resolution_id}")
async def get_resolution(
    resolution_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get a single resolution with full detail."""
    decision = db.query(Decision).filter(
        Decision.id == resolution_id,
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Resolution not found")

    sig_count = db.query(ResolutionSignature).filter(
        ResolutionSignature.decision_id == resolution_id
    ).count()

    total_members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None),
        BoardMember.role.in_(["board", "chair", "admin"]),
    ).count()

    return {
        "decision": decision,
        "results": decision.get_results(),
        "signature_count": sig_count,
        "total_signers": total_members,
    }


# =============================================================================
# Sign resolution
# =============================================================================

@router.post("/{resolution_id}/sign")
async def sign_resolution(
    resolution_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Digitally sign a resolution (name + timestamp + IP)."""
    decision = db.query(Decision).filter(
        Decision.id == resolution_id,
        Decision.deleted_at.is_(None),
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Resolution not found")

    if decision.type != "resolution":
        raise HTTPException(status_code=400, detail="Only resolutions can be signed")

    if decision.status != "closed":
        raise HTTPException(status_code=400, detail="Resolution must be closed (voted on) before signing")

    # Check for existing signature
    existing = db.query(ResolutionSignature).filter(
        ResolutionSignature.decision_id == resolution_id,
        ResolutionSignature.member_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already signed this resolution")

    # Capture IP (proxy-aware)
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.client.host if request.client else None

    signed_at = datetime.utcnow()
    signature_hash = generate_signature_hash(
        current_user.name, current_user.email, resolution_id, signed_at
    )

    signature = ResolutionSignature(
        decision_id=resolution_id,
        member_id=current_user.id,
        signed_at=signed_at,
        ip_address=ip_address,
        signature_hash=signature_hash,
    )
    db.add(signature)
    db.add(AuditLog(
        entity_type="resolution_signature",
        entity_id=resolution_id,
        entity_name=decision.title,
        action="sign",
        changed_by_id=current_user.id,
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(signature)

    return {
        "status": "signed",
        "signature_id": signature.id,
        "signed_at": signature.signed_at.isoformat(),
    }


# =============================================================================
# Signature status
# =============================================================================

@router.get("/{resolution_id}/signatures")
async def get_signature_status(
    resolution_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get signature status -- who signed and who hasn't."""
    decision = db.query(Decision).filter(
        Decision.id == resolution_id,
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Resolution not found")

    # Get all board-level members
    members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None),
        BoardMember.role.in_(["board", "chair", "admin"]),
    ).all()

    # Get existing signatures
    signatures = db.query(ResolutionSignature).filter(
        ResolutionSignature.decision_id == resolution_id
    ).all()
    sig_map = {s.member_id: s for s in signatures}

    result = []
    for member in members:
        sig = sig_map.get(member.id)
        result.append({
            "member_id": member.id,
            "member_name": member.name,
            "signed_at": sig.signed_at.isoformat() if sig else None,
            "ip_address": sig.ip_address if sig else None,
        })

    return {
        "resolution_id": resolution_id,
        "signatures": result,
        "signed_count": len(signatures),
        "total_members": len(members),
    }
