"""
Unified Auto Agent Client

Provides a single interface for auto mode that:
- Uses OpenRouter if OPENROUTER_API_KEY is available
- Falls back to Anthropic SDK if not

This allows users to run auto mode without needing an OpenRouter account.
"""

from dataclasses import dataclass

from ..config.api_keys import get_api_key


@dataclass
class AutoAgentConfig:
    """Configuration for the auto agent provider."""
    provider: str  # "openrouter" or "anthropic"
    available_models: list[dict]
    default_model: str


# Anthropic models available for auto agent
ANTHROPIC_AUTO_MODELS = [
    {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5"},
    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5"},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"},
]


def get_auto_agent_provider() -> str:
    """Determine which provider to use for auto agent.

    Returns:
        "openrouter" if OPENROUTER_API_KEY is set, otherwise "anthropic"
    """
    if get_api_key("OPENROUTER_API_KEY"):
        return "openrouter"
    return "anthropic"


def get_auto_agent_config() -> AutoAgentConfig:
    """Get the configuration for the auto agent based on available keys.

    Returns:
        AutoAgentConfig with provider, available models, and default model
    """
    provider = get_auto_agent_provider()

    if provider == "openrouter":
        # OpenRouter models are fetched dynamically
        return AutoAgentConfig(
            provider="openrouter",
            available_models=[],  # Will be fetched via API
            default_model="google/gemini-3-pro-preview",
        )
    else:
        return AutoAgentConfig(
            provider="anthropic",
            available_models=ANTHROPIC_AUTO_MODELS,
            default_model="claude-sonnet-4-5-20250929",
        )


class AutoAgentClient:
    """Unified client for auto agent chat, supporting both OpenRouter and Anthropic."""

    def __init__(self):
        self.provider = get_auto_agent_provider()
        self._openrouter_client = None
        self._anthropic_client = None

    def _get_openrouter_client(self):
        """Lazy-load OpenRouter client."""
        if self._openrouter_client is None:
            from .openrouter import OpenRouterClient
            self._openrouter_client = OpenRouterClient()
        return self._openrouter_client

    def _get_anthropic_client(self):
        """Lazy-load Anthropic client."""
        if self._anthropic_client is None:
            import anthropic
            api_key = get_api_key("ANTHROPIC_API_KEY")
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._anthropic_client

    async def chat(self, messages: list[dict], model: str) -> str:
        """Send a chat request to the appropriate provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     For OpenRouter: includes system message in list
                     For Anthropic: system message should be first with role='system'
            model: Model identifier

        Returns:
            The assistant's response text
        """
        if self.provider == "openrouter":
            client = self._get_openrouter_client()
            return await client.chat(messages, model)
        else:
            # Anthropic API format: system prompt separate from messages
            client = self._get_anthropic_client()

            # Extract system message if present
            system_prompt = None
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    chat_messages.append(msg)

            response = await client.messages.create(
                model=model,
                max_tokens=16384,
                system=system_prompt or "",
                messages=chat_messages,
            )

            return response.content[0].text

    async def list_models(self) -> list[dict]:
        """Get available models for this provider.

        Returns:
            List of model dicts with 'id' and 'name'
        """
        if self.provider == "openrouter":
            client = self._get_openrouter_client()
            models = await client.list_models()
            return [
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "pricing": m.get("pricing", {}),
                    "context_length": m.get("context_length"),
                }
                for m in models
            ]
        else:
            return ANTHROPIC_AUTO_MODELS
