"""
Agent system for collaborative hypergraph exploration.

This package provides a thin wrapper around Headless Claude Code to help users
evaluate ideas using entailment hypergraphs backed by simulations and literature.

Package structure:
- clients/: LLM and external API clients (Claude, OpenRouter, GapMap)
- hypergraph/: Hypergraph operations (CRUD, evaluation, entailment checking)
- config/: Configuration and settings
- utils/: Logging and path utilities
- prompts/: System prompts for Claude
"""

from .orchestrator import AgentOrchestrator
from .hypergraph import HypergraphManager, parse_simulation_evidence, format_literature_evidence
from .config import AgentConfig
from .clients import (
    ClaudeCodeClient,
    ClaudeResponse,
    TextEvent,
    ToolUseEvent,
    ToolResultEvent,
    ErrorEvent,
    DoneEvent,
)

__all__ = [
    'AgentOrchestrator',
    'AgentConfig',
    'HypergraphManager',
    'ClaudeCodeClient',
    'ClaudeResponse',
    # Streaming event types
    'TextEvent',
    'ToolUseEvent',
    'ToolResultEvent',
    'ErrorEvent',
    'DoneEvent',
    'parse_simulation_evidence',
    'format_literature_evidence',
]
