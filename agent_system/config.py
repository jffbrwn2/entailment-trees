"""
Configuration for the agent system.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for agent system."""

    # Paths
    approaches_dir: Path = Path("approaches")
    visualizer_dir: Path = Path("entailment_hypergraph")

    # Claude Code settings
    claude_api_key: Optional[str] = None  # Will be read from environment
    model: str = "claude-sonnet-4-5-20250929"

    # Agent behavior
    max_turns: int = 50  # Max conversation turns before requiring reset
    auto_validate: bool = True  # Validate hypergraph after each update
    require_approval: bool = True  # Require user approval for simulations

    def __post_init__(self):
        """Ensure directories exist."""
        self.approaches_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Load config from environment variables."""
        import os

        return cls(
            claude_api_key=os.getenv('ANTHROPIC_API_KEY'),
            approaches_dir=Path(os.getenv('APPROACHES_DIR', 'approaches')),
        )


# Default configuration
DEFAULT_CONFIG = AgentConfig()
