"""Tests for the DocumentGeneratorService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_jinja2_template_rendering():
    """Verify template renders meeting context correctly."""
    from app.services.document_generator import DocumentGeneratorService
    from jinja2 import Environment, BaseLoader

    svc = DocumentGeneratorService.__new__(DocumentGeneratorService)
    svc.jinja_env = Environment(loader=BaseLoader())

    template_str = "Meeting: {{ meeting.title }} on {{ meeting.date }}"
    context = {
        "meeting": {"title": "Q1 Board Meeting", "date": "April 7, 2026"},
        "transcript": "Test transcript.",
    }

    template = svc.jinja_env.from_string(template_str)
    result = template.render(**context)

    assert "Q1 Board Meeting" in result
    assert "April 7, 2026" in result


@pytest.mark.asyncio
async def test_generate_meeting_minutes_calls_anthropic(mock_anthropic_client):
    """Verify service calls AsyncAnthropic with rendered prompt."""
    from app.services.document_generator import DocumentGeneratorService
    from jinja2 import Environment, BaseLoader

    svc = DocumentGeneratorService.__new__(DocumentGeneratorService)
    svc.client = mock_anthropic_client
    svc.jinja_env = Environment(loader=BaseLoader())

    meeting_context = {
        "meeting": {"title": "Test Meeting", "date": "2026-04-07", "location": "Virtual"},
        "attendees": [],
        "agenda_items": [],
    }
    result = await svc.generate_meeting_minutes(
        transcript="Test transcript.",
        meeting_context=meeting_context,
        system_prompt="You are a board secretary.",
        user_prompt_template="Meeting: {{ meeting.title }}\n\n{{ transcript }}",
    )

    mock_anthropic_client.messages.create.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_generate_meeting_minutes_returns_markdown(mock_anthropic_client):
    """Verify service returns the text from Anthropic response."""
    from app.services.document_generator import DocumentGeneratorService
    from jinja2 import Environment, BaseLoader

    svc = DocumentGeneratorService.__new__(DocumentGeneratorService)
    svc.client = mock_anthropic_client
    svc.jinja_env = Environment(loader=BaseLoader())

    meeting_context = {
        "meeting": {"title": "Test Meeting", "date": "2026-04-07", "location": "Virtual"},
        "attendees": [],
        "agenda_items": [],
    }
    result = await svc.generate_meeting_minutes(
        transcript="Test transcript.",
        meeting_context=meeting_context,
        system_prompt="You are a board secretary.",
        user_prompt_template="{{ meeting.title }}\n{{ transcript }}",
    )

    assert result == "# Mock Meeting Minutes\n\nTest content"
