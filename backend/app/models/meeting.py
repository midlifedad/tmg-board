from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Meeting(Base):
    """Meeting model for board meetings."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Room name or "Virtual"
    meeting_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Zoom/Meet URL
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled/in_progress/completed/cancelled

    # Meeting lifecycle timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    created_by: Mapped[BoardMember] = relationship("BoardMember", foreign_keys=[created_by_id])
    deleted_by: Mapped[Optional[BoardMember]] = relationship("BoardMember", foreign_keys=[deleted_by_id])
    agenda_items: Mapped[List[AgendaItem]] = relationship(
        "AgendaItem", back_populates="meeting", cascade="all, delete-orphan", order_by="AgendaItem.order_index"
    )
    attendance: Mapped[List[MeetingAttendance]] = relationship(
        "MeetingAttendance", back_populates="meeting", cascade="all, delete-orphan"
    )
    transcript: Mapped[Optional[MeetingTranscript]] = relationship(
        "MeetingTranscript", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    documents: Mapped[List[MeetingDocument]] = relationship(
        "MeetingDocument", back_populates="meeting", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    def __repr__(self) -> str:
        return f"<Meeting {self.title} ({self.scheduled_date})>"


class AgendaItem(Base):
    """Agenda item for a meeting."""

    __tablename__ = "agenda_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[str] = mapped_column(String(30), default="information", nullable=False, server_default="information")
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    presenter_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("decisions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="agenda_items")
    presenter: Mapped[Optional["BoardMember"]] = relationship("BoardMember")
    decision: Mapped[Optional["Decision"]] = relationship("Decision")

    def __repr__(self) -> str:
        return f"<AgendaItem {self.order_index}. {self.title}>"


class MeetingAttendance(Base):
    """Attendance record for a meeting."""

    __tablename__ = "meeting_attendance"

    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("board_members.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # present/absent/excused
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="attendance")
    member: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<Attendance {self.member_id} @ {self.meeting_id}: {self.status}>"


class MeetingTranscript(Base):
    """Transcript text for a completed meeting. One transcript per meeting."""

    __tablename__ = "meeting_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "paste" or "upload"
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="transcript")
    created_by: Mapped[BoardMember] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<MeetingTranscript meeting={self.meeting_id} source={self.source}>"


class MeetingDocument(Base):
    """Links documents to meetings (e.g., generated minutes)."""

    __tablename__ = "meeting_documents"

    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="documents")
    document: Mapped[Document] = relationship("Document")
    created_by: Mapped[Optional[BoardMember]] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<MeetingDocument meeting={self.meeting_id} doc={self.document_id}>"


# Import for type hints
from app.models.member import BoardMember
from app.models.decision import Decision
from app.models.document import Document
