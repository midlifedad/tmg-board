"""
Admin models for RBAC, invitations, settings, and sessions.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Invitation(Base):
    """Pending board member invitations."""
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    invited_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    invited_by = relationship("BoardMember", foreign_keys=[invited_by_id])


class Permission(Base):
    """Granular permission definitions."""
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)


class RolePermission(Base):
    """Many-to-many mapping of roles to permissions."""
    __tablename__ = "role_permissions"

    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id"), primary_key=True)

    # Relationships
    permission = relationship("Permission")


class Setting(Base):
    """Key-value settings store."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=True)

    # Relationships
    updated_by = relationship("BoardMember", foreign_keys=[updated_by_id])


class UserSession(Base):
    """User session tracking for last login."""
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("BoardMember", foreign_keys=[user_id])
