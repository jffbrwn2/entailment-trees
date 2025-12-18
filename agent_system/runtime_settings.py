"""
Runtime settings for the agent system.

These settings can be modified at runtime via the API, unlike config.py which
is loaded from environment variables at startup.
"""

from dataclasses import dataclass, field
from typing import Optional
import threading


@dataclass
class RuntimeSettings:
    """Runtime-configurable settings."""

    # Model settings
    chat_model: str = "claude-sonnet-4-5-20250929"  # Model for chat agent (Anthropic API)
    evaluator_model: str = "claude-sonnet-4-5-20250929"  # Model for evaluate_claim and check_entailment
    auto_model: str = "anthropic/claude-3-haiku"  # Model for auto agent (OpenRouter)

    # Tool toggles
    edison_tools_enabled: bool = True
    gapmap_tools_enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "chatModel": self.chat_model,
            "evaluatorModel": self.evaluator_model,
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
