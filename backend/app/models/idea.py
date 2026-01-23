from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Idea(Base):
    """Idea model for board idea backlog."""

    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new/under_review/approved/rejected/promoted

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
    submitted_by: Mapped["BoardMember"] = relationship("BoardMember", foreign_keys=[submitted_by_id])
    deleted_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[deleted_by_id])
    promoted_to_decision: Mapped[Optional["Decision"]] = relationship("Decision")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="idea", cascade="all, delete-orphan", order_by="Comment.created_at"
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def comment_count(self) -> int:
        return len([c for c in self.comments if c.deleted_at is None])

    def __repr__(self) -> str:
        return f"<Idea {self.title} ({self.status})>"


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

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    idea: Mapped["Idea"] = relationship("Idea", back_populates="comments")
    author: Mapped["BoardMember"] = relationship("BoardMember", foreign_keys=[author_id])
    deleted_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[deleted_by_id])

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    def __repr__(self) -> str:
        return f"<Comment by {self.author_id} on idea {self.idea_id}>"


# Import for type hints
from app.models.member import BoardMember
from app.models.decision import Decision
