"""
Agent system for collaborative hypergraph exploration.

This package provides a thin wrapper around Headless Claude Code to help users
evaluate ideas using entailment hypergraphs backed by simulations and literature.
"""

from .hypergraph_manager import HypergraphManager
from .evidence_parser import parse_simulation_evidence, format_literature_evidence
from .agent_orchestrator import AgentOrchestrator
from .claude_client import (
    ClaudeCodeClient,
    ClaudeResponse,
    StreamEvent,
    TextEvent,
    ToolUseEvent,
    ToolResultEvent,
    ErrorEvent,
    DoneEvent,
)

__all__ = [
    'HypergraphManager',
    'AgentOrchestrator',
    'ClaudeCodeClient',
    'ClaudeResponse',
    # Streaming event types
    'StreamEvent',
    'TextEvent',
    'ToolUseEvent',
    'ToolResultEvent',
    'ErrorEvent',
    'DoneEvent',
    'parse_simulation_evidence',
    'format_literature_evidence',
]
