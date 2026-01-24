from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, UniqueConstraint
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

    # Current version tracking
    current_version: Mapped[int] = mapped_column(Integer, default=1)

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

    # Archive (different from delete - archived docs are still visible but inactive)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    uploaded_by: Mapped["BoardMember"] = relationship(
        "BoardMember", foreign_keys=[uploaded_by_id]
    )
    deleted_by: Mapped[Optional["BoardMember"]] = relationship(
        "BoardMember", foreign_keys=[deleted_by_id]
    )
    archived_by: Mapped[Optional["BoardMember"]] = relationship(
        "BoardMember", foreign_keys=[archived_by_id]
    )
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number.desc()"
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def needs_signature(self) -> bool:
        return self.docusign_envelope_id is not None and self.signing_status not in ("completed", "voided", "declined")

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.type})>"


class DocumentVersion(Base):
    """Version history for documents."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    upload_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    uploaded_by: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<DocumentVersion {self.document_id} v{self.version_number}>"


class RelatedDocument(Base):
    """Many-to-many relationship between related documents."""

    __tablename__ = "related_documents"

    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), primary_key=True
    )
    related_document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
    related_document: Mapped["Document"] = relationship("Document", foreign_keys=[related_document_id])
    created_by: Mapped[Optional["BoardMember"]] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<RelatedDocument {self.document_id} <-> {self.related_document_id}>"


# Import for type hints
from app.models.member import BoardMember
