from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, Float, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentConfig(Base):
    """Configuration for an AI agent."""

    __tablename__ = "agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_tool_names: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    usage_logs: Mapped[List["AgentUsageLog"]] = relationship(
        "AgentUsageLog", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AgentConfig {self.slug} ({self.model})>"


class AgentUsageLog(Base):
    """Log of agent invocations for tracking usage and cost."""

    __tablename__ = "agent_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_configs.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("board_members.id"), nullable=False, index=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent: Mapped["AgentConfig"] = relationship("AgentConfig", back_populates="usage_logs")
    user: Mapped["BoardMember"] = relationship("BoardMember")

    def __repr__(self) -> str:
        return f"<AgentUsageLog agent={self.agent_id} user={self.user_id} cost=${self.total_cost_usd:.4f}>"


# Import for type hints
from app.models.member import BoardMember
