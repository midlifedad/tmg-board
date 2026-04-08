"""AI-powered document generation service using Anthropic SDK + Jinja2.

Follows the StorageService singleton pattern from app/services/storage.py.
"""
from anthropic import AsyncAnthropic
from jinja2 import Environment, BaseLoader

from app.config import get_settings

settings = get_settings()

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


class DocumentGeneratorService:
    """Service for generating documents (meeting minutes, etc.) via Anthropic."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.jinja_env = Environment(loader=BaseLoader())

    async def generate_meeting_minutes(
        self,
        transcript: str,
        meeting_context: dict,
        system_prompt: str,
        user_prompt_template: str,
    ) -> str:
        """Render Jinja2 template with meeting context, then call Anthropic.

        Args:
            transcript: Raw meeting transcript text.
            meeting_context: Dict with meeting, attendees, agenda_items keys.
            system_prompt: System prompt string from DocumentTemplate.
            user_prompt_template: Jinja2 template string from DocumentTemplate.

        Returns:
            Generated markdown string from Anthropic.
        """
        template = self.jinja_env.from_string(user_prompt_template)
        rendered_prompt = template.render(**meeting_context, transcript=transcript)

        message = await self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": rendered_prompt}],
            system=system_prompt,
        )
        return message.content[0].text


# Singleton — only instantiate if API key is configured (avoids crash on import when key is empty)
document_generator = DocumentGeneratorService() if settings.anthropic_api_key else None
