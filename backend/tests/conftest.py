"""Shared test fixtures for the TMG Board backend test suite."""
from datetime import datetime

import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db import get_db
from app.main import app
from app.models.agent import AgentConfig, AgentUsageLog
from app.models.member import BoardMember
from app.models.meeting import Meeting, AgendaItem


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


@pytest.fixture
def seeded_db_session(db_session):
    """Database session with seed agents pre-loaded."""
    from app.main import _seed_agents
    _seed_agents(db_session)
    return db_session


@pytest.fixture
def client(db_session):
    """FastAPI test client with database override."""
    from httpx import AsyncClient, ASGITransport

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_agent(db_session):
    """Create a test AgentConfig."""
    agent = AgentConfig(
        name="Test Agent",
        slug="test-agent",
        system_prompt="You are a test assistant.",
        model="anthropic/claude-sonnet-4-5-20250929",
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def seed_user(db_session):
    """Create a test BoardMember."""
    user = BoardMember(
        email="test@themany.com",
        name="Test User",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def seed_template(db_session, seed_user):
    """Create a test MeetingTemplate with 2 TemplateAgendaItems (one regulatory)."""
    from app.models.template import MeetingTemplate, TemplateAgendaItem

    template = MeetingTemplate(
        name="Board Meeting",
        description="Standard board meeting template",
        default_duration_minutes=90,
        default_location="Conference Room A",
        created_by_id=seed_user.id,
    )
    db_session.add(template)
    db_session.commit()

    item1 = TemplateAgendaItem(
        template_id=template.id,
        title="Call to Order",
        description="Opening the meeting",
        item_type="information",
        duration_minutes=5,
        order_index=0,
        is_regulatory=False,
    )
    item2 = TemplateAgendaItem(
        template_id=template.id,
        title="Financial Report",
        description="Quarterly financial review",
        item_type="information",
        duration_minutes=15,
        order_index=1,
        is_regulatory=True,
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(template)
    return template


@pytest.fixture
def mock_litellm():
    """Mock litellm.acompletion for testing agent invocations.

    Available for any test that needs to mock LLM calls.
    """
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(
            message=AsyncMock(
                content="Test response",
                tool_calls=None,
            )
        )
    ]
    mock_response.usage = AsyncMock(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mock:
        yield mock


# =============================================================================
# Meeting & Role Fixtures
# =============================================================================


@pytest.fixture
def seed_meeting(db_session, seed_user):
    """Create a scheduled Meeting linked to seed_user."""
    meeting = Meeting(
        title="Test Board Meeting",
        description="A test meeting for unit tests",
        scheduled_date=datetime(2026, 3, 15, 10, 0),
        duration_minutes=90,
        location="Conference Room A",
        status="scheduled",
        created_by_id=seed_user.id,
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


@pytest.fixture
def completed_meeting(db_session, seed_user):
    """Create a completed Meeting for transcript/minutes tests."""
    meeting = Meeting(
        title="Completed Board Meeting",
        description="A completed meeting for testing minutes and transcripts",
        scheduled_date=datetime(2026, 2, 15, 10, 0),
        duration_minutes=60,
        location="Board Room",
        status="completed",
        created_by_id=seed_user.id,
        started_at=datetime(2026, 2, 15, 10, 0),
        ended_at=datetime(2026, 2, 15, 11, 0),
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


@pytest.fixture
def seed_shareholder(db_session):
    """Create a BoardMember with role='shareholder' for permission testing."""
    member = BoardMember(
        email="shareholder@themany.com",
        name="Shareholder User",
        role="shareholder",
    )
    db_session.add(member)
    db_session.commit()
    return member


@pytest.fixture
def seed_board_member(db_session):
    """Create a BoardMember with role='board' for permission testing."""
    member = BoardMember(
        email="board@themany.com",
        name="Board Member",
        role="board",
    )
    db_session.add(member)
    db_session.commit()
    return member


@pytest.fixture
def seed_chair_member(db_session):
    """Create a BoardMember with role='chair' for permission testing."""
    member = BoardMember(
        email="chair@themany.com",
        name="Chair Member",
        role="chair",
    )
    db_session.add(member)
    db_session.commit()
    return member


@pytest.fixture
def seed_agenda_item(db_session, seed_meeting):
    """Create an AgendaItem linked to seed_meeting."""
    item = AgendaItem(
        meeting_id=seed_meeting.id,
        title="Call to Order",
        description="Opening the meeting",
        item_type="information",
        duration_minutes=5,
        order_index=0,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item
