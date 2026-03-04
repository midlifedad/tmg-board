"""LiteLLM wrapper with API key validation and model configuration.

LiteLLM reads API keys from environment variables automatically:
  ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY
This module provides a thin wrapper for centralized imports and easy mocking.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from litellm import acompletion


async def get_completion(
    model: str,
    messages: List[dict],
    tools: Optional[List[dict]] = None,
    stream: bool = False,
    temperature: float = 0.3,
):
    """Thin wrapper around litellm.acompletion for centralized import and mocking."""
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


def validate_provider_keys() -> Dict[str, bool]:
    """Check which LLM providers have API keys configured.

    Returns a dict of provider name -> bool (True if key is non-empty).
    """
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY", "")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY", "")),
        "groq": bool(os.environ.get("GROQ_API_KEY", "")),
    }
