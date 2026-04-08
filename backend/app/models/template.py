from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MeetingTemplate(Base):
    """Reusable meeting template with pre-defined agenda items."""

    __tablename__ = "meeting_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    default_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    created_by: Mapped["BoardMember"] = relationship("BoardMember")
    items: Mapped[List["TemplateAgendaItem"]] = relationship(
        "TemplateAgendaItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateAgendaItem.order_index",
    )

    def __repr__(self) -> str:
        return f"<MeetingTemplate {self.name}>"


class TemplateAgendaItem(Base):
    """Pre-defined agenda item within a meeting template."""

    __tablename__ = "template_agenda_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_templates.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[str] = mapped_column(String(30), default="information", nullable=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_regulatory: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    template: Mapped["MeetingTemplate"] = relationship("MeetingTemplate", back_populates="items")

    def __repr__(self) -> str:
        return f"<TemplateAgendaItem {self.order_index}. {self.title}>"


# Import for type hints (at bottom to avoid circular imports)
from app.models.member import BoardMember
