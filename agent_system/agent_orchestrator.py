"""
Agent Orchestrator - Thin wrapper around Headless Claude Code.

Provides hypergraph structure and context to Claude Code, which does the heavy lifting
of writing simulations, running them, and searching literature.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .hypergraph_manager import HypergraphManager
from .config import AgentConfig
from .claude_client import ClaudeCodeClient, ClaudeResponse, ClientMode
from .conversation_logger import ConversationLogger
from .prompts import get_system_prompt_template, get_exploration_prompt


def _load_session_id(approach_dir: Path) -> Optional[str]:
    """Load session ID from approach's session.json file."""
    session_file = approach_dir / "session.json"
    if session_file.exists():
        try:
            with open(session_file) as f:
                data = json.load(f)
                return data.get("session_id")
        except Exception:
            pass
    return None


def _save_session_id(approach_dir: Path, session_id: str) -> None:
    """Save session ID to approach's session.json file."""
    session_file = approach_dir / "session.json"
    data = {"session_id": session_id, "updated_at": datetime.now().isoformat()}
    with open(session_file, "w") as f:
        json.dump(data, f, indent=2)


@dataclass
class Session:
    """Represents an agent session for evaluating an approach."""
    approach_name: str
    approach_dir: Path
    created: datetime = field(default_factory=datetime.now)
    turn_count: int = 0
    last_activity: datetime = field(default_factory=datetime.now)


class AgentOrchestrator:
    """
    Orchestrates interaction between user, Claude Code, and hypergraph.

    This is a thin wrapper that:
    1. Initializes approach folders with hypergraph templates
    2. Provides system prompts explaining hypergraph schema
    3. Validates hypergraph after updates
    4. Tracks conversation state
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize orchestrator.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfig()
        self.current_session: Optional[Session] = None
        self.hypergraph_mgr: Optional[HypergraphManager] = None
        self.current_logger: Optional[ConversationLogger] = None

        # Initialize single client in exploration mode by default
        exploration_mode = ClientMode(working_dir=self.config.explorations_dir)
        self.claude_client = ClaudeCodeClient(
            mode=exploration_mode,
            allowed_tools=["Write", "Read", "Edit", "Bash", "WebSearch", "Glob", "Grep"],
            verbose=False,
            logger=None  # Logger will be set when first used
        )

    def start_approach(
        self,
        name: str,
        initial_claim: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Start a new approach session.

        Args:
            name: Name for the approach (used as folder name)
            initial_claim: The hypothesis/claim to evaluate
            description: Optional description

        Returns:
            Session info and initial context
        """
        # Clean name for folder
        folder_name = name.lower().replace(' ', '_').replace('/', '_')
        approach_dir = self.config.approaches_dir / folder_name

        # Create session
        self.current_session = Session(
            approach_name=name,
            approach_dir=approach_dir
        )

        # Initialize hypergraph manager
        self.hypergraph_mgr = HypergraphManager(approach_dir)

        # Create initial hypergraph
        hypergraph = self.hypergraph_mgr.create_approach(
            name=name,
            initial_claim=initial_claim,
            description=description
        )

        # End previous logger session if switching approaches
        if self.current_logger is not None:
            self.current_logger.end_session()

        # Always create new logger for new approach
        self.current_logger = ConversationLogger(
            logs_dir=self.config.logs_dir,
            approach_name=name,
            approach_dir=approach_dir,
            working_dir=approach_dir
        )
        self.claude_client.logger = self.current_logger
        # Update global logger for hooks
        from . import claude_client as cc
        cc._current_logger = self.current_logger

        # Switch client to approach mode
        approach_mode = ClientMode(
            working_dir=approach_dir,
            approach_name=name,
            approach_dir=approach_dir
        )
        self.claude_client.switch_mode(approach_mode)

        # New approach - no session to resume yet
        self.claude_client.set_session_id(None)
        print(f"[SESSION] Starting new session for {folder_name}")

        return {
            "session": {
                "name": name,
                "folder": str(folder_name),
                "path": str(approach_dir),
                "session_id": None
            },
            "hypergraph": hypergraph,
            "system_prompt": self.get_system_prompt()
        }

    def load_approach(self, approach_dir: Path) -> Dict[str, Any]:
        """
        Load an existing approach session.

        Args:
            approach_dir: Path to existing approach directory

        Returns:
            Session info and initial context
        """
        # Initialize hypergraph manager
        self.hypergraph_mgr = HypergraphManager(approach_dir)

        # Load existing hypergraph
        hypergraph = self.hypergraph_mgr.load_hypergraph()
        name = hypergraph['metadata'].get('name', approach_dir.name)

        # Create session
        self.current_session = Session(
            approach_name=name,
            approach_dir=approach_dir
        )

        # End previous logger session if switching approaches
        if self.current_logger is not None:
            self.current_logger.end_session()

        # Always create new logger for new approach
        self.current_logger = ConversationLogger(
            logs_dir=self.config.logs_dir,
            approach_name=name,
            approach_dir=approach_dir,
            working_dir=approach_dir
        )
        self.claude_client.logger = self.current_logger
        # Update global logger for hooks
        from . import claude_client as cc
        cc._current_logger = self.current_logger

        # Switch client to approach mode
        approach_mode = ClientMode(
            working_dir=approach_dir,
            approach_name=name,
            approach_dir=approach_dir
        )
        self.claude_client.switch_mode(approach_mode)

        # Load session_id from file for conversation resumption
        saved_session_id = _load_session_id(approach_dir)
        if saved_session_id:
            self.claude_client.set_session_id(saved_session_id)
            print(f"[SESSION] Resuming session: {saved_session_id[:40]}...")
        else:
            self.claude_client.set_session_id(None)
            print(f"[SESSION] Starting new session for {approach_dir.name}")

        return {
            "session": {
                "name": name,
                "folder": str(approach_dir.name),
                "path": str(approach_dir),
                "session_id": saved_session_id
            },
            "hypergraph": hypergraph,
            "system_prompt": self.get_system_prompt()
        }

    def process_user_input(self, user_input: str) -> ClaudeResponse:
        """
        Process user input by sending to Claude Code.

        Args:
            user_input: User's message/question

        Returns:
            Claude's response
        """
        # Initialize logger on first use if needed
        if self.current_logger is None:
            self.current_logger = ConversationLogger(
                logs_dir=self.config.logs_dir,
                approach_name=self.current_session.approach_name if self.current_session else None,
                approach_dir=self.current_session.approach_dir if self.current_session else None,
                working_dir=self.claude_client.mode.working_dir
            )
            self.claude_client.logger = self.current_logger
            # Update global logger for hooks
            from . import claude_client as cc
            cc._current_logger = self.current_logger

        # Determine system prompt based on mode
        system_prompt = None
        if self.claude_client.sdk_client is None:  # First turn
            if self.current_session:
                # In approach mode - use full hypergraph prompt
                system_prompt = self.get_system_prompt()
            else:
                # In exploration mode - use simple prompt
                system_prompt = get_exploration_prompt()

        # SDK handles conversation continuity automatically
        response = self.claude_client.query(user_input, system_prompt=system_prompt)

        # Save session_id for future resumption (if we got one from the response)
        if self.current_session and self.claude_client.session_id:
            _save_session_id(self.current_session.approach_dir, self.claude_client.session_id)

        # Increment turn counter if in approach mode
        if self.current_session:
            self.increment_turn()

            # Validate hypergraph if it might have been modified
            if self.config.auto_validate:
                try:
                    errors, warnings = self.hypergraph_mgr.validate()
                    if errors:
                        response.content += f"\n\n⚠️  Hypergraph validation failed:\n" + "\n".join(errors)
                except Exception:
                    pass

        return response


    def get_system_prompt(self) -> str:
        """
        Generate system prompt with hypergraph instructions for Claude Code.

        This teaches Claude Code how to work with hypergraphs.
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_approach() first.")

        template = get_system_prompt_template()
        # Use replace instead of format to avoid conflicts with JSON examples in template
        return template.replace("{approach_name}", self.current_session.approach_name)

    def validate_hypergraph(self) -> Dict[str, Any]:
        """
        Validate current hypergraph.

        Returns:
            Dict with validation results
        """
        if not self.hypergraph_mgr:
            raise RuntimeError("No active session")

        errors, warnings = self.hypergraph_mgr.validate()

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current session status and hypergraph stats.

        Returns:
            Status information
        """
        if not self.current_session or not self.hypergraph_mgr:
            return {"active": False}

        stats = self.hypergraph_mgr.get_stats()

        return {
            "active": True,
            "approach": self.current_session.approach_name,
            "folder": str(self.current_session.approach_dir),
            "turns": self.current_session.turn_count,
            "stats": stats
        }

    def increment_turn(self):
        """Increment turn counter and update last activity."""
        if self.current_session:
            self.current_session.turn_count += 1
            self.current_session.last_activity = datetime.now()
