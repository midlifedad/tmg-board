"""Shared test fixtures for the TMG Board backend test suite."""
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db import get_db
from app.main import app
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
    """Mock litellm.acompletion for testing agent invocations."""
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
