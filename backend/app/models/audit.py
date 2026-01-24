from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AuditLog(Base):
    """General audit log for tracking changes."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document/meeting/decision/idea
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Human-readable name
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create/update/delete/restore
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Before/after values
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    changed_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"


class DocumentAccessLog(Base):
    """Log of document access (views, downloads, signatures)."""

    __tablename__ = "document_access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # view/download/sign
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document")
    member: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<DocumentAccess {self.action} by {self.member_id} on {self.document_id}>"


# Import for type hints
from app.models.member import BoardMember
from app.models.document import Document
