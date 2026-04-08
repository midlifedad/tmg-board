"""Shared test fixtures for TMG Board backend tests."""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.db.session import Base, get_db
from app.main import app
from app.models.member import BoardMember
from app.models.meeting import Meeting, AgendaItem, MeetingAttendance


# ============================================================================
# Test Database Setup
# ============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite engine and yield a test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite does not enforce foreign keys by default — enable them
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import all models so that Base.metadata knows about them
    from app.models import (  # noqa: F401
        BoardMember, Meeting, AgendaItem, MeetingAttendance,
        Document, DocumentVersion, RelatedDocument,
        Decision, Vote,
        Idea, Comment, IdeaCategory, IdeaHistory, CommentReaction,
        AuditLog, DocumentAccessLog,
        Invitation, Permission, RolePermission, Setting, UserSession,
    )
    # generation models imported after they are created in Task 2
    try:
        from app.models.generation import DocumentTemplate, MeetingMinutes  # noqa: F401
    except ImportError:
        pass

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ============================================================================
# Mock Anthropic Client
# ============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock AsyncAnthropic client that returns a canned response."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock()]
    mock_message.content[0].text = "# Mock Meeting Minutes\n\nTest content"

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    return mock_client


# ============================================================================
# HTTP Test Client
# ============================================================================

@pytest_asyncio.fixture
async def test_client(db_session):
    """AsyncClient wrapping the FastAPI app with DB dependency overridden."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db_session):
    """Create and return an admin BoardMember."""
    user = BoardMember(
        email="admin@test.com",
        name="Test Admin",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def chair_user(db_session):
    """Create and return a chair BoardMember."""
    user = BoardMember(
        email="chair@test.com",
        name="Test Chair",
        role="chair",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# Meeting Fixture
# ============================================================================

@pytest.fixture
def sample_meeting(db_session, admin_user):
    """Create a Meeting with AgendaItems and MeetingAttendance rows."""
    meeting = Meeting(
        title="Q1 2026 Board Meeting",
        scheduled_date=datetime(2026, 4, 7, 10, 0, 0),
        location="Conference Room A",
        duration_minutes=60,
        status="completed",
        created_by_id=admin_user.id,
    )
    db_session.add(meeting)
    db_session.flush()

    agenda_item = AgendaItem(
        meeting_id=meeting.id,
        title="Review Q1 Results",
        item_type="discussion",
        order_index=0,
        description="Review quarterly financial and operational results",
        presenter_id=admin_user.id,
    )
    db_session.add(agenda_item)

    attendance = MeetingAttendance(
        meeting_id=meeting.id,
        member_id=admin_user.id,
        status="present",
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


# ============================================================================
# Document Template Fixture
# ============================================================================

@pytest.fixture
def seeded_template(db_session):
    """Create a DocumentTemplate row with template_type='meeting_minutes'."""
    try:
        from app.models.generation import DocumentTemplate
    except ImportError:
        pytest.skip("DocumentTemplate model not yet created")

    template = DocumentTemplate(
        name="Meeting Minutes",
        template_type="meeting_minutes",
        system_prompt=(
            "You are a professional board secretary generating formal meeting minutes. "
            "Output clean, well-structured markdown suitable for a board of directors."
        ),
        user_prompt_template=(
            "# Meeting Minutes Request\n\n"
            "**Meeting:** {{ meeting.title }}\n"
            "**Date:** {{ meeting.date }}\n\n"
            "## Transcript\n{{ transcript }}\n\n"
            "Please generate formal meeting minutes."
        ),
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template
