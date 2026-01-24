from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.idea import Idea, Comment, IdeaCategory, IdeaHistory, CommentReaction
from app.models.decision import Decision
from app.api.auth import require_member, require_chair, require_admin

router = APIRouter()


# ============================================================================
# Pydantic schemas
# ============================================================================

class IdeaCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[int] = None


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


class StatusChange(BaseModel):
    status: str
    reason: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    color: str
    description: Optional[str] = None


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


class ReactionToggle(BaseModel):
    reaction_type: str  # thumbs_up, lightbulb, heart, warning


class PromoteToDecision(BaseModel):
    title: Optional[str] = None  # Override idea title
    description: Optional[str] = None  # Override idea description
    decision_type: str = "vote"  # vote/consent/resolution
    visibility: str = "standard"  # standard/anonymous/transparent
    deadline: Optional[datetime] = None


# ============================================================================
# Category endpoints (static routes first)
# ============================================================================

@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List all idea categories."""
    categories = db.query(IdeaCategory).order_by(IdeaCategory.name).all()
    return categories


@router.post("/categories")
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Create a new idea category (Admin only)."""
    # Check for duplicate name
    existing = db.query(IdeaCategory).filter(IdeaCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    # Validate color format
    if not data.color.startswith("#") or len(data.color) != 7:
        raise HTTPException(status_code=400, detail="Color must be a hex code (e.g., #FF5733)")

    category = IdeaCategory(
        name=data.name,
        color=data.color,
        description=data.description
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: int,
    name: Optional[str] = None,
    color: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Update a category (Admin only)."""
    category = db.query(IdeaCategory).filter(IdeaCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if name:
        # Check for duplicate
        existing = db.query(IdeaCategory).filter(
            IdeaCategory.name == name,
            IdeaCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        category.name = name

    if color:
        if not color.startswith("#") or len(color) != 7:
            raise HTTPException(status_code=400, detail="Color must be a hex code (e.g., #FF5733)")
        category.color = color

    if description is not None:
        category.description = description

    db.commit()
    db.refresh(category)

    return category


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Delete a category (Admin only). Ideas will be uncategorized."""
    category = db.query(IdeaCategory).filter(IdeaCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Uncategorize ideas in this category
    db.query(Idea).filter(Idea.category_id == category_id).update({"category_id": None})

    db.delete(category)
    db.commit()

    return {"status": "deleted", "id": category_id}


# ============================================================================
# Ideas CRUD
# ============================================================================

@router.get("/")
async def list_ideas(
    status: Optional[str] = Query(None, description="Filter by status"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List ideas with optional filtering."""
    query = db.query(Idea).filter(Idea.deleted_at.is_(None))

    if status:
        query = query.filter(Idea.status == status)
    if category_id:
        query = query.filter(Idea.category_id == category_id)

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
    data: IdeaCreate,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Submit a new idea (any member can submit)."""
    # Validate category if provided
    if data.category_id:
        category = db.query(IdeaCategory).filter(IdeaCategory.id == data.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")

    idea = Idea(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        submitted_by_id=current_user.id
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)

    return idea


@router.patch("/{idea_id}")
async def update_idea(
    idea_id: int,
    data: IdeaUpdate,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Update an idea (owner or chair/admin). Status changes use /status endpoint."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Check permissions: owner or chair/admin
    if idea.submitted_by_id != current_user.id and not current_user.is_chair:
        raise HTTPException(status_code=403, detail="Not authorized to update this idea")

    # Track changes in history
    changes_made = []

    if data.title and data.title != idea.title:
        history = IdeaHistory(
            idea_id=idea_id,
            field_changed="title",
            old_value=idea.title,
            new_value=data.title,
            changed_by_id=current_user.id
        )
        db.add(history)
        idea.title = data.title
        changes_made.append("title")

    if data.description is not None and data.description != idea.description:
        history = IdeaHistory(
            idea_id=idea_id,
            field_changed="description",
            old_value=idea.description,
            new_value=data.description,
            changed_by_id=current_user.id
        )
        db.add(history)
        idea.description = data.description
        changes_made.append("description")

    if data.category_id is not None and data.category_id != idea.category_id:
        # Validate category
        if data.category_id:
            category = db.query(IdeaCategory).filter(IdeaCategory.id == data.category_id).first()
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category")

        history = IdeaHistory(
            idea_id=idea_id,
            field_changed="category_id",
            old_value=str(idea.category_id) if idea.category_id else None,
            new_value=str(data.category_id) if data.category_id else "null",
            changed_by_id=current_user.id
        )
        db.add(history)
        idea.category_id = data.category_id
        changes_made.append("category")

    db.commit()
    db.refresh(idea)

    return idea


@router.post("/{idea_id}/status")
async def change_status(
    idea_id: int,
    data: StatusChange,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Change idea status with reason (Chair/Admin only)."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    valid_statuses = ["new", "under_review", "approved", "rejected", "promoted"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    if data.status == idea.status:
        raise HTTPException(status_code=400, detail="Idea already has this status")

    # Record history
    history = IdeaHistory(
        idea_id=idea_id,
        field_changed="status",
        old_value=idea.status,
        new_value=data.status,
        reason=data.reason,
        changed_by_id=current_user.id
    )
    db.add(history)

    idea.status = data.status
    idea.status_reason = data.reason

    db.commit()
    db.refresh(idea)

    return idea


@router.get("/{idea_id}/history")
async def get_idea_history(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get change history for an idea."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    history = db.query(IdeaHistory).filter(
        IdeaHistory.idea_id == idea_id
    ).order_by(IdeaHistory.changed_at.desc()).all()

    return history


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

    idea.deleted_at = datetime.utcnow()
    idea.deleted_by_id = current_user.id
    db.commit()

    return {"status": "deleted", "id": idea_id}


@router.post("/{idea_id}/promote")
async def promote_to_decision(
    idea_id: int,
    data: PromoteToDecision,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Promote an idea to a decision (Chair/Admin only)."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.status == "promoted":
        raise HTTPException(status_code=400, detail="Idea already promoted")

    if idea.promoted_to_decision_id:
        raise HTTPException(status_code=400, detail="Idea already linked to a decision")

    # Save old status before changing
    old_status = idea.status

    # Create the decision
    decision = Decision(
        title=data.title or idea.title,
        description=data.description or idea.description,
        type=data.decision_type,
        visibility=data.visibility,
        deadline=data.deadline,
        created_by_id=current_user.id
    )
    db.add(decision)
    db.flush()  # Get the decision ID

    # Record history before updating
    history = IdeaHistory(
        idea_id=idea_id,
        field_changed="status",
        old_value=old_status,
        new_value="promoted",
        reason=f"Promoted to decision #{decision.id}",
        changed_by_id=current_user.id
    )
    db.add(history)

    # Link idea to decision and update status
    idea.promoted_to_decision_id = decision.id
    idea.status = "promoted"
    idea.status_reason = f"Promoted to decision #{decision.id}"

    db.commit()
    db.refresh(idea)
    db.refresh(decision)

    return {
        "idea": idea,
        "decision": decision
    }


# ============================================================================
# Comments
# ============================================================================

@router.get("/{idea_id}/comments")
async def get_comments(
    idea_id: int,
    include_replies: bool = Query(True, description="Include threaded replies"),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get comments for an idea with optional threading."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Get all active comments
    comments = db.query(Comment).filter(
        Comment.idea_id == idea_id,
        Comment.deleted_at.is_(None)
    ).order_by(Comment.created_at).all()

    if not include_replies:
        # Return flat list
        return comments

    # Build threaded structure - return top-level comments only
    # Replies are accessible via the 'replies' relationship
    top_level = [c for c in comments if c.parent_id is None]

    # Sort: pinned first, then by date
    top_level.sort(key=lambda c: (not c.is_pinned, c.created_at))

    return top_level


@router.post("/{idea_id}/comments")
async def add_comment(
    idea_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Add a comment to an idea (supports threading via parent_id)."""
    idea = db.query(Idea).filter(
        Idea.id == idea_id,
        Idea.deleted_at.is_(None)
    ).first()

    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Validate parent comment if provided
    if data.parent_id:
        parent = db.query(Comment).filter(
            Comment.id == data.parent_id,
            Comment.idea_id == idea_id,
            Comment.deleted_at.is_(None)
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent comment not found")

    comment = Comment(
        idea_id=idea_id,
        author_id=current_user.id,
        content=data.content,
        parent_id=data.parent_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.patch("/{idea_id}/comments/{comment_id}")
async def edit_comment(
    idea_id: int,
    comment_id: int,
    data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Edit a comment (author only)."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.idea_id == idea_id,
        Comment.deleted_at.is_(None)
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only author can edit
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the author can edit this comment")

    comment.content = data.content
    comment.edited_at = datetime.utcnow()
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
    """Delete a comment (author or admin only)."""
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

    comment.deleted_at = datetime.utcnow()
    comment.deleted_by_id = current_user.id
    db.commit()

    return {"status": "deleted", "id": comment_id}


@router.post("/{idea_id}/comments/{comment_id}/react")
async def toggle_reaction(
    idea_id: int,
    comment_id: int,
    data: ReactionToggle,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Add or remove a reaction from a comment (toggle)."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.idea_id == idea_id,
        Comment.deleted_at.is_(None)
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    valid_reactions = ["thumbs_up", "lightbulb", "heart", "warning"]
    if data.reaction_type not in valid_reactions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction type. Must be one of: {', '.join(valid_reactions)}"
        )

    # Check if reaction already exists
    existing = db.query(CommentReaction).filter(
        CommentReaction.comment_id == comment_id,
        CommentReaction.user_id == current_user.id,
        CommentReaction.reaction_type == data.reaction_type
    ).first()

    if existing:
        # Remove the reaction (toggle off)
        db.delete(existing)
        db.commit()
        return {"action": "removed", "reaction_type": data.reaction_type}
    else:
        # Add the reaction
        reaction = CommentReaction(
            comment_id=comment_id,
            user_id=current_user.id,
            reaction_type=data.reaction_type
        )
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
        return {"action": "added", "reaction_type": data.reaction_type, "id": reaction.id}


@router.post("/{idea_id}/comments/{comment_id}/pin")
async def toggle_pin(
    idea_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Pin or unpin a comment (Chair/Admin only)."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.idea_id == idea_id,
        Comment.deleted_at.is_(None)
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_pinned = not comment.is_pinned
    db.commit()
    db.refresh(comment)

    return {
        "id": comment_id,
        "is_pinned": comment.is_pinned
    }
