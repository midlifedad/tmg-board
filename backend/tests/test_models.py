"""Tests for DocumentTemplate and MeetingMinutes SQLAlchemy models.

Wave 0 stubs — unskipped and implemented in Task 2.
"""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 2")
def test_document_template_creation(db_session):
    """Verify DocumentTemplate can be created with required fields."""
    from app.models.generation import DocumentTemplate

    template = DocumentTemplate(
        name="Test Template",
        template_type="meeting_minutes",
        system_prompt="You are a board secretary.",
        user_prompt_template="Generate minutes for {{ meeting.title }}.",
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    assert template.id is not None
    assert template.name == "Test Template"
    assert template.template_type == "meeting_minutes"
    assert template.is_active is True
    assert template.created_at is not None


@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 2")
def test_meeting_minutes_creation(db_session, sample_meeting, admin_user):
    """Verify MeetingMinutes can be created linked to a meeting."""
    from app.models.generation import DocumentTemplate, MeetingMinutes

    template = DocumentTemplate(
        name="Default",
        template_type="meeting_minutes",
        system_prompt="You are a board secretary.",
        user_prompt_template="Generate minutes for {{ meeting.title }}.",
    )
    db_session.add(template)
    db_session.flush()

    minutes = MeetingMinutes(
        meeting_id=sample_meeting.id,
        content_markdown="# Q1 2026 Board Meeting Minutes\n\nTest content.",
        generated_by_id=admin_user.id,
        template_id=template.id,
    )
    db_session.add(minutes)
    db_session.commit()
    db_session.refresh(minutes)

    assert minutes.id is not None
    assert minutes.meeting_id == sample_meeting.id
    assert minutes.generated_by_id == admin_user.id
    assert minutes.content_markdown.startswith("# Q1")
    assert minutes.created_at is not None


@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 2")
def test_meeting_minutes_unique_per_meeting(db_session, sample_meeting, admin_user):
    """Verify unique constraint on meeting_id prevents duplicates."""
    from app.models.generation import MeetingMinutes

    minutes1 = MeetingMinutes(
        meeting_id=sample_meeting.id,
        content_markdown="# First Minutes",
        generated_by_id=admin_user.id,
    )
    db_session.add(minutes1)
    db_session.commit()

    minutes2 = MeetingMinutes(
        meeting_id=sample_meeting.id,
        content_markdown="# Duplicate Minutes",
        generated_by_id=admin_user.id,
    )
    db_session.add(minutes2)
    with pytest.raises(IntegrityError):
        db_session.commit()
