"""
Shared API key storage for session-based keys.

This module provides a way to store API keys in memory (session-only)
that can be set by the backend and used by agent_system modules.
"""

import os

# Session API keys (can be set at runtime, cleared on server restart)
_session_keys: dict[str, str] = {}


def get_api_key(key_name: str) -> str | None:
    """Get API key from session storage or environment variable.

    Session keys take precedence over environment variables.

    Args:
        key_name: Name of the API key (e.g., "ANTHROPIC_API_KEY")

    Returns:
        The API key value, or None if not set
    """
    return _session_keys.get(key_name) or os.getenv(key_name)


def set_api_key(key_name: str, value: str) -> None:
    """Set a session API key.

    Args:
        key_name: Name of the API key (e.g., "ANTHROPIC_API_KEY")
        value: The API key value
    """
    _session_keys[key_name] = value


def clear_api_keys() -> None:
    """Clear all session API keys."""
    _session_keys.clear()
