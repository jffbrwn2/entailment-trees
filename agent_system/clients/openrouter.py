"""
OpenRouter API Client

Provides access to multiple LLM providers through OpenRouter's unified API.
https://openrouter.ai/

Used by Auto mode to drive hypothesis evaluation.
"""

import asyncio
import os
import json
import httpx
from typing import AsyncIterator, Optional


BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterError(Exception):
    """Raised when OpenRouter API returns an error or unexpected response."""
    pass


class OpenRouterClient:
    """Async client for OpenRouter API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client.

        Args:
            api_key: OpenRouter API key. If not provided, reads from session or OPENROUTER_API_KEY env var.
        """
        from ..config.api_keys import get_api_key
        self.api_key = api_key or get_api_key("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY env var or provide via session.")

        self._models_cache: Optional[list] = None

    def _headers(self) -> dict:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jbrown/ai-simulations",  # Required by OpenRouter
            "X-Title": "AI Simulations - Auto Mode",
        }

    async def chat(
        self,
        messages: list[dict],
        model: str = "google/gemini-3-pro-preview",
    ) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "google/gemini-3-pro-preview")

        Returns:
            The assistant's response text

        Raises:
            OpenRouterError: If the API returns an error or empty response
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": model,
                        "messages": messages,
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_data = e.response.json()
                    error_detail = f": {error_data.get('error', {}).get('message', str(error_data))}"
                except Exception:
                    error_detail = f": {e.response.text[:200]}" if e.response.text else ""
                raise OpenRouterError(
                    f"OpenRouter API error (HTTP {e.response.status_code}){error_detail}"
                ) from e
            except httpx.TimeoutException as e:
                raise OpenRouterError(f"OpenRouter request timed out after 120s") from e
            except httpx.RequestError as e:
                raise OpenRouterError(f"OpenRouter request failed: {e}") from e

            data = response.json()

            # Check for API-level errors in response
            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                raise OpenRouterError(f"OpenRouter API error: {error_msg}")

            # Extract content with validation
            choices = data.get("choices", [])
            if not choices:
                raise OpenRouterError(f"OpenRouter returned no choices for model {model}")

            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise OpenRouterError(f"OpenRouter returned null content for model {model}")

            if not content.strip():
                raise OpenRouterError(f"OpenRouter returned empty/whitespace response for model {model}")

            return content

    def chat_sync(
        self,
        messages: list[dict],
        model: str = "google/gemini-3-pro-preview",
    ) -> str:
        """Synchronous version of chat() for use in non-async contexts.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "google/gemini-3-pro-preview")

        Returns:
            The assistant's response text

        Raises:
            OpenRouterError: If the API returns an error or empty response
        """
        return asyncio.run(self.chat(messages, model))

    async def stream_chat(
        self,
        messages: list[dict],
        model: str = "google/gemini-3-pro-preview",
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier

        Yields:
            Text chunks as they arrive
        """
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{BASE_URL}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                },
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if delta := chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                                yield delta
                        except json.JSONDecodeError:
                            continue

    async def list_models(self) -> list[dict]:
        """Get available models from OpenRouter.

        Returns:
            List of model info dicts with 'id', 'name', 'pricing', etc.
        """
        if self._models_cache is not None:
            return self._models_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/models",
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            self._models_cache = data.get("data", [])
            return self._models_cache


if __name__ == "__main__":
    import asyncio

    async def test():
        client = OpenRouterClient()

        # Test list models
        models = await client.list_models()
        print(f"Available models: {len(models)}")

        # Test simple chat
        response = await client.chat(
            messages=[{"role": "user", "content": "Say hello in exactly 3 words."}],
            model="anthropic/claude-3-haiku",
        )
        print(f"Response: {response}")

    asyncio.run(test())
