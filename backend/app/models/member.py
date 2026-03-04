from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BoardMember(Base):
    """Board member model - pre-registered whitelist of authorized users."""

    __tablename__ = "board_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="board")  # admin/chair/board/shareholder
    google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # IANA timezone, null = use org default
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=True
    )

    # Relationships
    deleted_by: Mapped[Optional["BoardMember"]] = relationship(
        "BoardMember", remote_side=[id], foreign_keys=[deleted_by_id]
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_board(self) -> bool:
        return self.role in ("board", "chair", "admin")

    @property
    def is_chair(self) -> bool:
        return self.role in ("board", "chair", "admin")

    def __repr__(self) -> str:
        return f"<BoardMember {self.email} ({self.role})>"
