"""Tests for AgentConfig and AgentUsageLog models."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.member import BoardMember


@pytest.fixture
def db_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestAgentConfig:
    """Tests for the AgentConfig model."""

    def test_agent_config_creation(self, db_session):
        """AgentConfig can be created with all required fields and persisted."""
        agent = AgentConfig(
            name="Test Agent",
            slug="test-agent",
            system_prompt="You are a test assistant.",
            model="anthropic/claude-sonnet-4-5-20250929",
            description="A test agent for unit tests",
            temperature=0.5,
            max_iterations=10,
            is_active=True,
            allowed_tool_names=["tool1", "tool2"],
        )
        db_session.add(agent)
        db_session.commit()

        retrieved = db_session.query(AgentConfig).filter_by(slug="test-agent").first()
        assert retrieved is not None
        assert retrieved.name == "Test Agent"
        assert retrieved.slug == "test-agent"
        assert retrieved.system_prompt == "You are a test assistant."
        assert retrieved.model == "anthropic/claude-sonnet-4-5-20250929"
        assert retrieved.description == "A test agent for unit tests"
        assert retrieved.temperature == 0.5
        assert retrieved.max_iterations == 10
        assert retrieved.is_active is True

    def test_agent_config_slug_unique(self, db_session):
        """Duplicate AgentConfig slug raises IntegrityError."""
        agent1 = AgentConfig(
            name="Agent One",
            slug="duplicate-slug",
            system_prompt="Prompt 1",
            model="anthropic/claude-sonnet-4-5-20250929",
        )
        db_session.add(agent1)
        db_session.commit()

        agent2 = AgentConfig(
            name="Agent Two",
            slug="duplicate-slug",
            system_prompt="Prompt 2",
            model="anthropic/claude-sonnet-4-5-20250929",
        )
        db_session.add(agent2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_agent_config_defaults(self, db_session):
        """AgentConfig defaults are applied correctly."""
        agent = AgentConfig(
            name="Default Agent",
            slug="default-agent",
            system_prompt="Default prompt",
            model="anthropic/claude-sonnet-4-5-20250929",
        )
        db_session.add(agent)
        db_session.commit()

        retrieved = db_session.query(AgentConfig).filter_by(slug="default-agent").first()
        assert retrieved.temperature == 0.3
        assert retrieved.max_iterations == 5
        assert retrieved.is_active is True

    def test_agent_config_allowed_tool_names(self, db_session):
        """allowed_tool_names stores and retrieves a JSON list correctly."""
        tools = ["create_agenda_item", "get_meeting", "list_members"]
        agent = AgentConfig(
            name="Tool Agent",
            slug="tool-agent",
            system_prompt="Tool prompt",
            model="anthropic/claude-sonnet-4-5-20250929",
            allowed_tool_names=tools,
        )
        db_session.add(agent)
        db_session.commit()

        retrieved = db_session.query(AgentConfig).filter_by(slug="tool-agent").first()
        assert retrieved.allowed_tool_names == ["create_agenda_item", "get_meeting", "list_members"]


class TestAgentUsageLog:
    """Tests for the AgentUsageLog model."""

    def test_usage_log_foreign_keys(self, db_session):
        """AgentUsageLog correctly links to AgentConfig and BoardMember."""
        agent = AgentConfig(
            name="Log Agent",
            slug="log-agent",
            system_prompt="Log prompt",
            model="anthropic/claude-sonnet-4-5-20250929",
        )
        db_session.add(agent)
        db_session.commit()

        user = BoardMember(
            email="test@themany.com",
            name="Test User",
            role="admin",
        )
        db_session.add(user)
        db_session.commit()

        log = AgentUsageLog(
            agent_id=agent.id,
            user_id=user.id,
            model_used="anthropic/claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.003,
            duration_ms=1500,
        )
        db_session.add(log)
        db_session.commit()

        retrieved = db_session.query(AgentUsageLog).first()
        assert retrieved.agent_id == agent.id
        assert retrieved.user_id == user.id
        assert retrieved.agent.name == "Log Agent"
        assert retrieved.user.name == "Test User"

    def test_usage_log_tracks_cost(self, db_session):
        """AgentUsageLog records prompt_tokens, completion_tokens, total_cost_usd, duration_ms."""
        agent = AgentConfig(
            name="Cost Agent",
            slug="cost-agent",
            system_prompt="Cost prompt",
            model="anthropic/claude-sonnet-4-5-20250929",
        )
        db_session.add(agent)
        db_session.commit()

        user = BoardMember(
            email="cost@themany.com",
            name="Cost User",
            role="board",
        )
        db_session.add(user)
        db_session.commit()

        log = AgentUsageLog(
            agent_id=agent.id,
            user_id=user.id,
            model_used="anthropic/claude-sonnet-4-5-20250929",
            prompt_tokens=500,
            completion_tokens=200,
            total_cost_usd=0.015,
            tool_calls_count=3,
            duration_ms=5000,
            success=True,
        )
        db_session.add(log)
        db_session.commit()

        retrieved = db_session.query(AgentUsageLog).first()
        assert retrieved.prompt_tokens == 500
        assert retrieved.completion_tokens == 200
        assert retrieved.total_cost_usd == 0.015
        assert retrieved.tool_calls_count == 3
        assert retrieved.duration_ms == 5000
        assert retrieved.success is True
        assert retrieved.error_message is None
