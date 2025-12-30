"""
Runtime settings for the agent system.

These settings can be modified at runtime via the API, unlike config.py which
is loaded from environment variables at startup.
"""

from dataclasses import dataclass, field
from typing import Optional
import threading


def _get_default_auto_model() -> str:
    """Get default auto model based on available API keys."""
    from .api_keys import get_api_key
    if get_api_key("OPENROUTER_API_KEY"):
        return "google/gemini-3-pro-preview"
    return "claude-sonnet-4-5-20250929"


@dataclass
class RuntimeSettings:
    """Runtime-configurable settings."""

    # Model settings
    chat_model: str = "claude-sonnet-4-5-20250929"  # Model for chat agent (Anthropic API)
    evaluator_model: str = "claude-sonnet-4-5-20250929"  # Model for evaluate_claim skill
    entailment_model: str = "claude-sonnet-4-5-20250929"  # Model for check_entailment skill
    auto_model: str = field(default_factory=_get_default_auto_model)  # Model for auto agent

    # Tool toggles
    edison_tools_enabled: bool = False
    gapmap_tools_enabled: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "chatModel": self.chat_model,
            "evaluatorModel": self.evaluator_model,
            "entailmentModel": self.entailment_model,
            "autoModel": self.auto_model,
            "edisonToolsEnabled": self.edison_tools_enabled,
            "gapMapToolsEnabled": self.gapmap_tools_enabled,
        }

    def update_from_dict(self, data: dict) -> None:
        """Update settings from dictionary (API request)."""
        if "chatModel" in data:
            self.chat_model = data["chatModel"]
        if "evaluatorModel" in data:
            self.evaluator_model = data["evaluatorModel"]
        if "entailmentModel" in data:
            self.entailment_model = data["entailmentModel"]
        if "autoModel" in data:
            self.auto_model = data["autoModel"]
        if "edisonToolsEnabled" in data:
            self.edison_tools_enabled = data["edisonToolsEnabled"]
        if "gapMapToolsEnabled" in data:
            self.gapmap_tools_enabled = data["gapMapToolsEnabled"]


# Thread-safe singleton for runtime settings
_settings_lock = threading.Lock()
_settings: Optional[RuntimeSettings] = None


def get_settings() -> RuntimeSettings:
    """Get the global runtime settings instance."""
    global _settings
    with _settings_lock:
        if _settings is None:
            _settings = RuntimeSettings()
        return _settings


def update_settings(data: dict) -> RuntimeSettings:
    """Update runtime settings from dictionary."""
    settings = get_settings()
    with _settings_lock:
        settings.update_from_dict(data)
    return settings
