"""Tests for the Minutes Generator agent: tool registration, seed data, upgrade block."""
from __future__ import annotations

import pytest

from app.tools import TOOL_REGISTRY
from app.models.agent import AgentConfig


# -- Tool Registration Tests --


MINUTES_TOOLS = ["get_board_members", "get_meeting_details", "get_meeting_transcript", "create_minutes_document"]


def test_tools_registered():
    """All 3 Minutes Generator tools are registered in TOOL_REGISTRY."""
    for name in MINUTES_TOOLS:
        assert name in TOOL_REGISTRY, f"Tool '{name}' not found in TOOL_REGISTRY"


def test_tool_schemas():
    """Meeting-scoped tools have meeting_id as a required parameter."""
    meeting_tools = [t for t in MINUTES_TOOLS if t != "get_board_members"]
    for name in meeting_tools:
        tool = TOOL_REGISTRY[name]
        schema = tool.parameters_schema
        assert "meeting_id" in schema["properties"], (
            f"Tool '{name}' missing meeting_id in properties"
        )
        assert "meeting_id" in schema["required"], (
            f"Tool '{name}' missing meeting_id in required"
        )


def test_tool_categories():
    """All 3 tools have category='transcripts'."""
    for name in MINUTES_TOOLS:
        tool = TOOL_REGISTRY[name]
        assert tool.category == "transcripts", (
            f"Tool '{name}' has category '{tool.category}', expected 'transcripts'"
        )


# -- Seed Data Tests --


def test_minutes_generator_seed_prompt(seeded_db_session):
    """Minutes Generator seed data has production prompt, not placeholder."""
    agent = seeded_db_session.query(AgentConfig).filter(
        AgentConfig.slug == "minutes-generator"
    ).first()
    assert agent is not None, "Minutes Generator agent not found in seed data"
    assert "[Detailed prompt to be added in Phase 03]" not in agent.system_prompt, (
        "Minutes Generator still has placeholder prompt"
    )
    assert "markdown" in agent.system_prompt.lower(), (
        "Production prompt should mention markdown format"
    )
    assert "minutes" in agent.system_prompt.lower(), (
        "Production prompt should mention minutes"
    )


def test_minutes_generator_seed_tools(seeded_db_session):
    """Minutes Generator seed data has correct allowed_tool_names."""
    agent = seeded_db_session.query(AgentConfig).filter(
        AgentConfig.slug == "minutes-generator"
    ).first()
    assert agent is not None, "Minutes Generator agent not found in seed data"
    for tool_name in MINUTES_TOOLS:
        assert tool_name in agent.allowed_tool_names, (
            f"Tool '{tool_name}' not in allowed_tool_names: {agent.allowed_tool_names}"
        )


def test_seed_upgrade_replaces_placeholder(db_session):
    """Upgrade block detects placeholder prompt and updates it."""
    from app.main import _seed_agents

    # Create a Minutes Generator with the old placeholder prompt
    old_agent = AgentConfig(
        name="Minutes Generator",
        slug="minutes-generator",
        description="Creates formatted meeting minutes from transcripts",
        system_prompt=(
            "You are a minutes generator for The Many Group board. "
            "You create formatted meeting minutes from transcripts. "
            "[Detailed prompt to be added in Phase 03]"
        ),
        model="anthropic/claude-sonnet-4-5-20250929",
        temperature=0.2,
        max_iterations=3,
        allowed_tool_names=["get_meeting", "get_agenda", "get_attendance"],
    )
    db_session.add(old_agent)
    db_session.commit()

    # Also need other agents so the count > 0 (hits the else branch)
    other_agent = AgentConfig(
        name="Meeting Setup",
        slug="meeting-setup",
        description="Helps create meetings",
        system_prompt="test prompt",
        model="anthropic/claude-sonnet-4-5-20250929",
    )
    db_session.add(other_agent)
    db_session.commit()

    # Run seed again -- should trigger upgrade
    _seed_agents(db_session)

    # Verify prompt was upgraded
    updated = db_session.query(AgentConfig).filter(
        AgentConfig.slug == "minutes-generator"
    ).first()
    assert "[Detailed prompt to be added in Phase 03]" not in updated.system_prompt, (
        "Placeholder prompt was not replaced by upgrade block"
    )
    assert "markdown" in updated.system_prompt.lower(), (
        "Upgraded prompt should mention markdown format"
    )
    for tool_name in MINUTES_TOOLS:
        assert tool_name in updated.allowed_tool_names, (
            f"Upgraded agent should have {tool_name} tool"
        )
