"""LiteLLM wrapper with API key validation, model discovery, and logging.

API keys are resolved in this order:
  1. Database settings table (keys: anthropic_api_key, groq_api_key)
  2. Environment variables (ANTHROPIC_API_KEY, GROQ_API_KEY)

LiteLLM reads from env vars, so we sync DB keys into os.environ before each call.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

from litellm import acompletion
from sqlalchemy.orm import Session

from app.models.admin import Setting

logger = logging.getLogger(__name__)

# Map of provider name -> (settings DB key, env var name)
PROVIDER_KEY_MAP = {
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "groq": ("groq_api_key", "GROQ_API_KEY"),
}

# Static fallback used when provider APIs are unreachable and for frontend label lookups.
FALLBACK_MODELS = [
    {"value": "anthropic/claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5", "provider": "anthropic"},
    {"value": "anthropic/claude-haiku-3-5-20241022", "label": "Claude Haiku 3.5", "provider": "anthropic"},
    {"value": "groq/llama-3.3-70b-versatile", "label": "Llama 3.3 70B", "provider": "groq"},
    {"value": "groq/llama-3.1-8b-instant", "label": "Llama 3.1 8B (Fast)", "provider": "groq"},
]

# Keep SUPPORTED_MODELS as alias for backward compatibility with frontend models.ts
SUPPORTED_MODELS = FALLBACK_MODELS

# Simple in-memory cache: { "models": [...], "fetched_at": float }
_model_cache: Dict = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


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
    configured = [p for p, (_, env) in PROVIDER_KEY_MAP.items() if os.environ.get(env)]
    logger.debug("API keys synced, configured providers: %s", configured)


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

    logger.info("LLM request: model=%s messages=%d tools=%d", model, len(messages), len(tools) if tools else 0)
    start = time.time()
    try:
        result = await acompletion(**kwargs)
        elapsed = time.time() - start
        if result.usage:
            logger.info(
                "LLM response: model=%s tokens=%d+%d elapsed=%.1fs",
                model, result.usage.prompt_tokens, result.usage.completion_tokens, elapsed,
            )
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error("LLM error: model=%s error=%s elapsed=%.1fs", model, e, elapsed)
        raise


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


async def _fetch_anthropic_models() -> List[dict]:
    """Fetch models from Anthropic's native Models API."""
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
        response = await client.models.list(limit=100)
        models = []
        for m in response.data:
            models.append({
                "value": f"anthropic/{m.id}",
                "label": m.display_name,
                "provider": "anthropic",
                "max_input_tokens": m.max_input_tokens,
                "max_output_tokens": getattr(m, "max_tokens", None),
            })
        logger.info("Fetched %d models from Anthropic API", len(models))
        return models
    except Exception as e:
        logger.warning("Failed to fetch Anthropic models: %s", e)
        return []


async def _fetch_groq_models() -> List[dict]:
    """Fetch models from Groq's OpenAI-compatible Models API."""
    try:
        from groq import AsyncGroq
        client = AsyncGroq()
        response = await client.models.list()
        models = []
        for m in response.data:
            if not getattr(m, "active", True):
                continue
            models.append({
                "value": f"groq/{m.id}",
                "label": m.id,
                "provider": "groq",
                "max_input_tokens": getattr(m, "context_window", None),
            })
        logger.info("Fetched %d models from Groq API", len(models))
        return models
    except Exception as e:
        logger.warning("Failed to fetch Groq models: %s", e)
        return []


def _get_fallback_models_for_provider(provider: str) -> List[dict]:
    """Get fallback models for a provider from the static list."""
    return [m for m in FALLBACK_MODELS if m["provider"] == provider]


async def fetch_available_models(db: Session) -> List[dict]:
    """Get available models from provider APIs, filtered by configured keys.

    Uses a 1-hour cache. Falls back to static FALLBACK_MODELS on API failure.
    """
    # Check cache
    now = time.time()
    if _model_cache.get("models") and (now - _model_cache.get("fetched_at", 0)) < _CACHE_TTL_SECONDS:
        # Filter cached models by currently configured providers
        provider_status = validate_provider_keys(db=db)
        return [m for m in _model_cache["models"] if provider_status.get(m["provider"], False)]

    provider_status = validate_provider_keys(db=db)
    all_models = []

    # Fetch from each configured provider
    if provider_status.get("anthropic"):
        models = await _fetch_anthropic_models()
        all_models.extend(models if models else _get_fallback_models_for_provider("anthropic"))

    if provider_status.get("groq"):
        models = await _fetch_groq_models()
        all_models.extend(models if models else _get_fallback_models_for_provider("groq"))

    # Update cache (even if some providers failed, cache what we got)
    if all_models:
        _model_cache["models"] = all_models
        _model_cache["fetched_at"] = now

    return all_models
