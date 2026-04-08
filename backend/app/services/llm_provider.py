"""LiteLLM wrapper with API key validation and model configuration.

API keys are resolved in this order:
  1. Database settings table (keys: anthropic_api_key, groq_api_key)
  2. Environment variables (ANTHROPIC_API_KEY, GROQ_API_KEY)

LiteLLM reads from env vars, so we sync DB keys into os.environ before each call.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from litellm import acompletion
from sqlalchemy.orm import Session

from app.models.admin import Setting

# Map of provider name -> (settings DB key, env var name)
PROVIDER_KEY_MAP = {
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "groq": ("groq_api_key", "GROQ_API_KEY"),
}

# Single source of truth for available models.
# Only models whose provider has a configured API key will be returned by the
# GET /api/agents/available-models endpoint.
SUPPORTED_MODELS = [
    {"value": "anthropic/claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5", "provider": "anthropic"},
    {"value": "anthropic/claude-haiku-3-5-20241022", "label": "Claude Haiku 3.5", "provider": "anthropic"},
    {"value": "groq/llama-3.3-70b-versatile", "label": "Llama 3.3 70B", "provider": "groq"},
    {"value": "groq/llama-3.1-8b-instant", "label": "Llama 3.1 8B (Fast)", "provider": "groq"},
]


def load_api_keys_from_db(db: Session) -> Dict[str, str]:
    """Load LLM API keys from the settings table.

    Returns a dict of env var name -> key value for all non-empty keys.
    """
    db_keys = [v[0] for v in PROVIDER_KEY_MAP.values()]
    settings = db.query(Setting).filter(Setting.key.in_(db_keys)).all()
    settings_map = {s.key: s.value for s in settings if s.value}

    result = {}
    for provider, (db_key, env_key) in PROVIDER_KEY_MAP.items():
        if db_key in settings_map:
            result[env_key] = settings_map[db_key]
    return result


def sync_api_keys(db: Session) -> None:
    """Sync API keys from DB settings into os.environ so LiteLLM can read them.

    DB values take priority over existing env vars.
    """
    db_keys = load_api_keys_from_db(db)
    for env_key, value in db_keys.items():
        os.environ[env_key] = value


async def get_completion(
    model: str,
    messages: List[dict],
    tools: Optional[List[dict]] = None,
    stream: bool = False,
    temperature: float = 0.3,
    db: Optional[Session] = None,
):
    """Thin wrapper around litellm.acompletion for centralized import and mocking.

    If db is provided, syncs API keys from the settings table before calling LiteLLM.
    """
    if db:
        sync_api_keys(db)

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    return await acompletion(**kwargs)


def validate_provider_keys(db: Optional[Session] = None) -> Dict[str, bool]:
    """Check which LLM providers have API keys configured.

    Checks DB settings first (if db provided), then falls back to env vars.
    Returns a dict of provider name -> bool (True if key is non-empty).
    """
    if db:
        sync_api_keys(db)

    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY", "")),
        "groq": bool(os.environ.get("GROQ_API_KEY", "")),
    }
