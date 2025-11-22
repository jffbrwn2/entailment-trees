"""
Claude Code Client - Wrapper for headless Claude Code CLI.

Provides Python interface to the `claude` command for programmatic interaction.
"""

import json
import subprocess
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClaudeMessage:
    """Represents a message in the conversation."""
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ClaudeResponse:
    """Response from Claude Code."""
    content: str
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    raw_output: Optional[Dict[str, Any]] = None


class ClaudeCodeClient:
    """
    Python wrapper for headless Claude Code CLI.

    Enables programmatic interaction with Claude Code by calling the
    `claude` command with appropriate flags.
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        allowed_tools: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """
        Initialize Claude Code client.

        Args:
            working_dir: Working directory for Claude Code (affects file operations)
            allowed_tools: List of tools to allow (e.g., ["Write", "Read", "Bash"])
            verbose: Enable verbose logging
        """
        self.working_dir = working_dir or Path.cwd()
        self.allowed_tools = allowed_tools
        self.verbose = verbose
        self.current_session: Optional[str] = None

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        resume_session: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Send a query to Claude Code.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions
            resume_session: Optional session ID to continue conversation

        Returns:
            ClaudeResponse with content and metadata
        """
        # Build command
        cmd = ["claude", "--print", prompt]

        # Add system prompt if provided
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Resume session if provided
        if resume_session:
            cmd.extend(["--resume", resume_session])

        # Set output format to JSON for structured parsing
        cmd.extend(["--output-format", "json"])

        # Add allowed tools
        if self.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.allowed_tools)])

        # Add verbose flag
        if self.verbose:
            cmd.append("--verbose")

        # Execute command
        result = subprocess.run(
            cmd,
            cwd=self.working_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        # Parse JSON output
        try:
            output = json.loads(result.stdout)

            return ClaudeResponse(
                content=output.get("result", ""),
                session_id=output.get("session_id"),
                cost_usd=output.get("total_cost_usd"),
                raw_output=output
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return ClaudeResponse(
                content=result.stdout,
                raw_output=None
            )

    def start_conversation(
        self,
        initial_prompt: str,
        system_prompt: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Start a new conversation and track the session.

        Args:
            initial_prompt: Initial user message
            system_prompt: System instructions

        Returns:
            Response with session ID stored for future turns
        """
        response = self.query(initial_prompt, system_prompt=system_prompt)
        self.current_session = response.session_id
        return response

    def continue_conversation(self, prompt: str) -> ClaudeResponse:
        """
        Continue the current conversation.

        Args:
            prompt: Next user message

        Returns:
            Response continuing the session
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_conversation() first.")

        response = self.query(prompt, resume_session=self.current_session)
        # Update session ID in case it changed
        if response.session_id:
            self.current_session = response.session_id
        return response

    def end_conversation(self):
        """End the current conversation session."""
        self.current_session = None


class ClaudeCodeError(Exception):
    """Exception raised when Claude Code execution fails."""
    pass
