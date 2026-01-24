from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class IdeaCategory(Base):
    """Category for organizing ideas."""

    __tablename__ = "idea_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)  # hex color e.g. #FF5733
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ideas: Mapped[List["Idea"]] = relationship("Idea", back_populates="category")

    def __repr__(self) -> str:
        return f"<IdeaCategory {self.name}>"


class Idea(Base):
    """Idea model for board idea backlog."""

    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new/under_review/approved/rejected/promoted
    status_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Reason for status change

    # Category
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("idea_categories.id"), nullable=True
    )

    submitted_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # If promoted to decision
    promoted_to_decision_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("decisions.id"), nullable=True
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    category: Mapped[Optional["IdeaCategory"]] = relationship("IdeaCategory", back_populates="ideas")
    submitted_by: Mapped["BoardMember"] = relationship("BoardMember", foreign_keys=[submitted_by_id])
    deleted_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[deleted_by_id])
    promoted_to_decision: Mapped[Optional["Decision"]] = relationship("Decision")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="idea", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    history: Mapped[List["IdeaHistory"]] = relationship(
        "IdeaHistory", back_populates="idea", cascade="all, delete-orphan", order_by="IdeaHistory.changed_at.desc()"
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def comment_count(self) -> int:
        return len([c for c in self.comments if c.deleted_at is None])

    def __repr__(self) -> str:
        return f"<Idea {self.title} ({self.status})>"


class IdeaHistory(Base):
    """Change history for ideas."""

    __tablename__ = "idea_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idea_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_changed: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Optional reason for change
    changed_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="history")
    changed_by: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<IdeaHistory {self.idea_id}: {self.field_changed}>"


class Comment(Base):
    """Comment on an idea."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idea_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Threading support
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )

    # Pinning (chair can pin important comments)
    is_pinned: Mapped[bool] = mapped_column(default=False)

    # Edit tracking
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="comments")
    author: Mapped["BoardMember"] = relationship("BoardMember", foreign_keys=[author_id])
    deleted_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[deleted_by_id])
    parent: Mapped[Optional["Comment"]] = relationship("Comment", remote_side="Comment.id", backref="replies")
    reactions: Mapped[List["CommentReaction"]] = relationship(
        "CommentReaction", back_populates="comment", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def is_edited(self) -> bool:
        return self.edited_at is not None

    @property
    def reaction_counts(self) -> dict:
        """Get reaction counts by type."""
        counts = {}
        for reaction in self.reactions:
            counts[reaction.reaction_type] = counts.get(reaction.reaction_type, 0) + 1
        return counts

    def __repr__(self) -> str:
        return f"<Comment by {self.author_id} on idea {self.idea_id}>"


class CommentReaction(Base):
    """Reaction on a comment."""

    __tablename__ = "comment_reactions"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", "reaction_type", name="uq_comment_reaction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # thumbs_up, lightbulb, heart, warning
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    comment: Mapped["Comment"] = relationship("Comment", back_populates="reactions")
    user: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<CommentReaction {self.reaction_type} by {self.user_id}>"


# Import for type hints
from app.models.member import BoardMember
from app.models.decision import Decision
