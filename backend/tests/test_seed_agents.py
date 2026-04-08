"""Tests for agent seed data in lifespan."""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.agent import AgentConfig


def test_seed_agents_exist(seeded_db_session):
    """Three seed agents exist after lifespan seed runs."""
    agents = seeded_db_session.query(AgentConfig).all()
    slugs = {a.slug for a in agents}
    assert "meeting-setup" in slugs
    assert "minutes-generator" in slugs
    assert "resolution-writer" in slugs
    assert len(agents) == 3


def test_meeting_setup_agent_config(seeded_db_session):
    """Meeting Setup agent has correct configuration."""
    agent = seeded_db_session.query(AgentConfig).filter_by(slug="meeting-setup").first()
    assert agent is not None
    assert agent.name == "Meeting Setup"
    assert agent.model == "anthropic/claude-sonnet-4-5-20250929"
    assert agent.temperature == 0.3
    assert agent.max_iterations == 5
    assert "create_meeting_with_agenda" in agent.allowed_tool_names
    assert "create_agenda_item" in agent.allowed_tool_names
    assert "get_meeting" in agent.allowed_tool_names
    assert "list_meetings" in agent.allowed_tool_names


def test_minutes_generator_agent_config(seeded_db_session):
    """Minutes Generator agent has correct configuration."""
    agent = seeded_db_session.query(AgentConfig).filter_by(slug="minutes-generator").first()
    assert agent is not None
    assert agent.name == "Minutes Generator"
    assert agent.temperature == 0.2
    assert agent.max_iterations == 5


def test_resolution_writer_agent_config(seeded_db_session):
    """Resolution Writer agent has correct configuration."""
    agent = seeded_db_session.query(AgentConfig).filter_by(slug="resolution-writer").first()
    assert agent is not None
    assert agent.name == "Resolution Writer"
    assert agent.temperature == 0.3
    assert agent.max_iterations == 3
    assert "create_resolution" in agent.allowed_tool_names
