from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.idea import Idea, Comment
from app.api.auth import require_member, require_chair, require_admin

router = APIRouter()


@router.get("/")
async def list_ideas(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List ideas with optional filtering."""
    query = db.query(Idea).filter(Idea.deleted_at.is_(None))

    if status:
        query = query.filter(Idea.status == status)

    total = query.count()
    ideas = query.order_by(Idea.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": ideas,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{idea_id}")
async def get_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get a single idea with comments."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    return idea


@router.post("/")
async def create_idea(
    title: str,
    description: str,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Submit a new idea (any member can submit)."""
    idea = Idea(
        title=title,
        description=description,
        submitted_by_id=current_user.id
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    return idea


@router.patch("/{idea_id}")
async def update_idea(
    idea_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Update an idea (owner or chair/admin)."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Check permissions: owner or chair/admin
    if idea.submitted_by_id != current_user.id and not current_user.is_chair:
        raise HTTPException(status_code=403, detail="Not authorized to update this idea")

    # Status changes require chair/admin
    if status and not current_user.is_chair:
        raise HTTPException(status_code=403, detail="Only chair/admin can change status")

    if title:
        idea.title = title
    if description:
        idea.description = description
    if status:
        idea.status = status

    db.commit()
    db.refresh(idea)

    return idea


@router.delete("/{idea_id}")
async def delete_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Soft delete an idea (Admin only)."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    from datetime import datetime
    idea.deleted_at = datetime.utcnow()
    idea.deleted_by_id = current_user.id
    db.commit()

    return {"status": "deleted", "id": idea_id}


# Comments

@router.get("/{idea_id}/comments")
async def get_comments(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get comments for an idea."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Filter out deleted comments
    return [c for c in idea.comments if c.deleted_at is None]


@router.post("/{idea_id}/comments")
async def add_comment(
    idea_id: int,
    content: str,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Add a comment to an idea."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    comment = Comment(
        idea_id=idea_id,
        author_id=current_user.id,
        content=content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/{idea_id}/comments/{comment_id}")
async def delete_comment(
    idea_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Delete a comment (owner or admin only)."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.idea_id == idea_id,
        Comment.deleted_at.is_(None)
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check permissions: comment author or admin
    if comment.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    from datetime import datetime
    comment.deleted_at = datetime.utcnow()
    comment.deleted_by_id = current_user.id
    db.commit()

    return {"status": "deleted", "id": comment_id}


@router.post("/{idea_id}/promote")
async def promote_to_decision(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Promote an idea to a decision (Chair or Admin only)."""
    # TODO: Implement idea promotion to decision
    raise HTTPException(status_code=501, detail="Not implemented")
