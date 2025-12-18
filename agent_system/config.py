"""
Configuration for the agent system.

Environment Variables:
- ANTHROPIC_API_KEY: Your Anthropic API key (required)
- APPROACHES_DIR: Directory for approach folders (default: "approaches")
- EVALUATION_MODEL: Claude model for evaluate_claim and check_entailment
                    (default: "claude-sonnet-4-5-20250929")
- OPENROUTER_API_KEY: API key for OpenRouter (required for Auto mode)
- OPENROUTER_DEFAULT_MODEL: Default model for Auto agent
                            (default: "anthropic/claude-3-haiku")
- AUTO_MODE_MAX_TURNS: Max turns for Auto mode (default: 20)

Example:
    export EVALUATION_MODEL="claude-opus-4-20250514"
    # Now both evaluate_claim and check_entailment use Opus

    export OPENROUTER_API_KEY="sk-or-..."
    export OPENROUTER_DEFAULT_MODEL="anthropic/claude-3.5-sonnet"
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """Configuration for agent system."""

    # Paths
    approaches_dir: Path = Path("approaches")
    explorations_dir: Path = Path("explorations")
    visualizer_dir: Path = Path("entailment_hypergraph")
    logs_dir: Path = Path("logs")  # Centralized logs for all sessions

    # Claude Code settings
    claude_api_key: Optional[str] = None  # Will be read from environment
    model: str = "claude-sonnet-4-5-20250929"

    # Evaluation model (used by evaluate_claim and check_entailment)
    evaluation_model: str = "claude-sonnet-4-5-20250929"

    # Agent behavior
    max_turns: int = 50  # Max conversation turns before requiring reset
    auto_validate: bool = True  # Validate hypergraph after each update
    require_approval: bool = True  # Require user approval for simulations

    # Auto mode settings (OpenRouter)
    openrouter_api_key: Optional[str] = None  # Will be read from environment
    openrouter_default_model: str = "anthropic/claude-3-haiku"
    auto_mode_max_turns: int = 20

    def __post_init__(self):
        """Ensure directories exist."""
        self.approaches_dir.mkdir(parents=True, exist_ok=True)
        self.explorations_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Load config from environment variables."""
        import os

        return cls(
            claude_api_key=os.getenv('ANTHROPIC_API_KEY'),
            approaches_dir=Path(os.getenv('APPROACHES_DIR', 'approaches')),
            explorations_dir=Path(os.getenv('EXPLORATIONS_DIR', 'explorations')),
            evaluation_model=os.getenv('EVALUATION_MODEL', 'claude-sonnet-4-5-20250929'),
            openrouter_api_key=os.getenv('OPENROUTER_API_KEY'),
            openrouter_default_model=os.getenv('OPENROUTER_DEFAULT_MODEL', 'anthropic/claude-3-haiku'),
            auto_mode_max_turns=int(os.getenv('AUTO_MODE_MAX_TURNS', '20')),
        )


# Default configuration
DEFAULT_CONFIG = AgentConfig()
