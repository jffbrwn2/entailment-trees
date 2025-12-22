"""
OpenRouter API Client

Provides access to multiple LLM providers through OpenRouter's unified API.
https://openrouter.ai/

Used by Auto mode to drive hypothesis evaluation.
"""

import os
import json
import httpx
from typing import AsyncIterator, Optional


BASE_URL = "https://openrouter.ai/api/v1"


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
        """
        async with httpx.AsyncClient() as client:
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
            data = response.json()
            return data["choices"][0]["message"]["content"]

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
