"""SQLAlchemy models for document generation: DocumentTemplate and MeetingMinutes."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DocumentTemplate(Base):
    """Admin-configurable Jinja2 prompt template for document generation."""

    __tablename__ = "document_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "meeting_minutes"
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<DocumentTemplate {self.name} ({self.template_type})>"


class MeetingMinutes(Base):
    """Generated meeting minutes linked to a meeting (one set per meeting)."""

    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=False, unique=True
    )
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=False
    )
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("document_templates.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting")
    generated_by: Mapped["BoardMember"] = relationship("BoardMember")
    template: Mapped[Optional["DocumentTemplate"]] = relationship("DocumentTemplate")

    def __repr__(self) -> str:
        return f"<MeetingMinutes meeting_id={self.meeting_id}>"


# Deferred imports to avoid circular dependencies
from app.models.meeting import Meeting  # noqa: E402, F401
from app.models.member import BoardMember  # noqa: E402, F401
