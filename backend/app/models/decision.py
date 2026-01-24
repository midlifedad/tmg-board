from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Decision(Base):
    """Decision model for board votes and resolutions."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # vote/consent/resolution
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/open/closed

    # Voting visibility: standard (results after close), anonymous (no voter names), transparent (live results)
    visibility: Mapped[str] = mapped_column(String(20), default="standard")

    meeting_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("meetings.id"), nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # For resolutions
    resolution_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documents.id"), nullable=True)

    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Archive (different from delete - archived decisions are kept for records)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )
    archived_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    meeting: Mapped[Optional["Meeting"]] = relationship("Meeting")
    document: Mapped[Optional["Document"]] = relationship("Document")
    created_by: Mapped["BoardMember"] = relationship("BoardMember", foreign_keys=[created_by_id])
    deleted_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[deleted_by_id])
    archived_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember", foreign_keys=[archived_by_id])
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="decision", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def get_results(self) -> dict:
        """Get voting results summary."""
        results = {"yes": 0, "no": 0, "abstain": 0, "pending": 0}
        for vote in self.votes:
            if vote.vote in results:
                results[vote.vote] += 1
        return results

    def __repr__(self) -> str:
        return f"<Decision {self.title} ({self.status})>"


class Vote(Base):
    """Vote record for a decision."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    decision_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    vote: Mapped[str] = mapped_column(String(10), nullable=False)  # yes/no/abstain
    cast_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    decision: Mapped["Decision"] = relationship("Decision", back_populates="votes")
    member: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<Vote {self.member_id} on {self.decision_id}: {self.vote}>"


# Import for type hints
from app.models.member import BoardMember
from app.models.meeting import Meeting
from app.models.document import Document
