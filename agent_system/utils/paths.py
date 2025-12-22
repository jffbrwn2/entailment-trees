"""
Path utilities for resolving file paths in the agent system.

This module provides path resolution that works with relative paths
within the context of the current approach directory.
"""

from pathlib import Path
from typing import Optional


# Module-level approach directory for path resolution
# Set by ClaudeCodeClient when starting an approach session
_current_approach_dir: Optional[Path] = None


def get_approach_dir() -> Optional[Path]:
    """Get the current approach directory, if set."""
    return _current_approach_dir


def set_approach_dir(path: Optional[Path]) -> None:
    """Set the current approach directory."""
    global _current_approach_dir
    _current_approach_dir = path


def resolve_path(path_str: str) -> Path:
    """
    Resolve a path string to an absolute Path.

    If the path is relative and an approach directory is set,
    resolves relative to the approach directory.
    Otherwise, resolves relative to the current working directory.

    Args:
        path_str: Path string (can be relative or absolute)

    Returns:
        Resolved absolute Path
    """
    path = Path(path_str)
    if path.is_absolute():
        return path

    # If we have an approach directory and path is relative, resolve against it
    if _current_approach_dir is not None:
        return _current_approach_dir / path

    # Fall back to current working directory
    return path.resolve()
