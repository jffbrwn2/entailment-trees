"""
Prompt management for the agent system.

This module provides functions for loading system prompts from files,
making them easier to version control and maintain separately from code.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """
    Load a prompt from the prompts directory.

    Args:
        name: Name of the prompt file (without extension)

    Returns:
        The prompt content as a string
    """
    prompt_file = PROMPTS_DIR / f"{name}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text()


def get_system_prompt_template() -> str:
    """Load the main system prompt template for approach mode."""
    return load_prompt("system_prompt")


def get_exploration_prompt() -> str:
    """Load the exploration mode prompt."""
    return load_prompt("exploration_prompt")
