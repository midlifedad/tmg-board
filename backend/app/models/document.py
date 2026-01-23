from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Document(Base):
    """Document model for board documents."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # resolution/minutes/consent/financial/legal
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)

    # DocuSign integration
    docusign_envelope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signing_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # sent/delivered/completed/declined/voided
    signed_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    uploaded_by: Mapped["BoardMember"] = relationship(
        "BoardMember", foreign_keys=[uploaded_by_id]
    )
    deleted_by: Mapped[Optional["BoardMember"]] = relationship(
        "BoardMember", foreign_keys=[deleted_by_id]
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def needs_signature(self) -> bool:
        return self.docusign_envelope_id is not None and self.signing_status not in ("completed", "voided", "declined")

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.type})>"


# Import for type hints
from app.models.member import BoardMember
