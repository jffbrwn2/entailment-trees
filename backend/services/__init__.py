"""Backend services for business logic."""

from .state import (
    get_orchestrator,
    set_orchestrator,
    get_event_loop,
    set_event_loop,
    hypergraph_connections,
    auto_mode_sessions,
    get_openrouter_client,
    get_gapmap_client,
    get_auto_agent_client,
    clear_auto_agent_client,
)
from .file_watcher import HypergraphFileHandler
from .websocket import notify_hypergraph_update, notify_auto_event
from .auto_mode import AutoModeSession, run_auto_mode_loop, get_auto_agent_response

__all__ = [
    # State
    "get_orchestrator",
    "set_orchestrator",
    "get_event_loop",
    "set_event_loop",
    "hypergraph_connections",
    "auto_mode_sessions",
    "get_openrouter_client",
    "get_gapmap_client",
    "get_auto_agent_client",
    "clear_auto_agent_client",
    # File watcher
    "HypergraphFileHandler",
    # WebSocket
    "notify_hypergraph_update",
    "notify_auto_event",
    # Auto mode
    "AutoModeSession",
    "run_auto_mode_loop",
    "get_auto_agent_response",
]
