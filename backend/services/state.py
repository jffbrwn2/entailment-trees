"""
Shared application state.

This module holds global state that needs to be accessed across routes and services.
Using a module for this keeps the state centralized and avoids circular imports.
"""

import asyncio
from typing import Optional, Dict, List
from fastapi import WebSocket

# Type hints for external imports (avoid importing heavy modules at module level)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agent_system import AgentOrchestrator
    from agent_system.openrouter_client import OpenRouterClient
    from agent_system.gapmap_client import GapMapClient
    from .auto_mode import AutoModeSession

# Global orchestrator instance
_orchestrator: Optional["AgentOrchestrator"] = None

# Event loop reference for async calls from file watcher thread
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None

# WebSocket connections for hypergraph updates (folder -> list of websockets)
hypergraph_connections: Dict[str, List[WebSocket]] = {}

# Active auto mode sessions by folder
auto_mode_sessions: Dict[str, "AutoModeSession"] = {}

# Lazy-initialized clients
_openrouter_client: Optional["OpenRouterClient"] = None
_gapmap_client: Optional["GapMapClient"] = None


def get_orchestrator() -> Optional["AgentOrchestrator"]:
    """Get the global orchestrator instance."""
    return _orchestrator


def set_orchestrator(orchestrator: Optional["AgentOrchestrator"]) -> None:
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


def get_event_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Get the main event loop reference."""
    return _main_event_loop


def set_event_loop(loop: Optional[asyncio.AbstractEventLoop]) -> None:
    """Set the main event loop reference."""
    global _main_event_loop
    _main_event_loop = loop


def get_openrouter_client() -> "OpenRouterClient":
    """Get or create the OpenRouter client."""
    global _openrouter_client
    if _openrouter_client is None:
        from agent_system.openrouter_client import OpenRouterClient
        _openrouter_client = OpenRouterClient()
    return _openrouter_client


def get_gapmap_client() -> "GapMapClient":
    """Get or create the Gap Map client."""
    global _gapmap_client
    if _gapmap_client is None:
        from agent_system.gapmap_client import GapMapClient
        _gapmap_client = GapMapClient()
    return _gapmap_client
