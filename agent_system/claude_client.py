"""
Claude Code Client - Wrapper for Claude Agent SDK.

Provides Python interface to the Claude Agent SDK for programmatic interaction.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
    HookMatcher,
    HookContext
)

from .entailment_checker import check_entailment_skill as check_entailment_impl
from .claim_evaluator import evaluate_claim_skill as evaluate_claim_impl


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


# Define entailment checker as SDK tool
@tool(
    name="check_entailment",
    description="Check if implications in the hypergraph are logically valid. "
                "Validates that 'if all premises are true, then conclusion is true' for each implication. "
                "Returns validation errors and suggestions for fixing invalid entailments. "
                "By default only checks implications that haven't been checked or where premises changed. "
                "Use force_check=true to re-check all, or implication_ids to check specific ones.",
    input_schema={
        "hypergraph_path": str,
        "force_check": {"type": "boolean", "default": False},
        "implication_ids": {"type": "string", "default": None}
    }
)
async def check_entailment_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool for checking entailment in hypergraphs.

    Args:
        args: Dictionary with keys:
            - hypergraph_path: Path to hypergraph.json
            - force_check: Re-check all implications even if already checked
            - implication_ids: Comma-separated IDs to check (e.g., "i1,i3,i5")

    Returns:
        Tool response with validation results
    """
    hypergraph_path = args.get("hypergraph_path", "")
    force_check = args.get("force_check", False)
    implication_ids = args.get("implication_ids", None)

    # Call the actual implementation
    result = check_entailment_impl(hypergraph_path, force_check, implication_ids)

    return {
        "content": [{"type": "text", "text": result}]
    }


# Define claim evaluator as SDK tool
@tool(
    name="evaluate_claim",
    description="Evaluate a claim by assigning a score based on evidence. "
                "This is Phase 2 after building the logical structure - gather evidence "
                "(simulations, literature, calculations) and assign scores to show whether "
                "requirements are actually met. Scores: 0=false, 10=true, 5=unsure.",
    input_schema={
        "hypergraph_path": str,
        "claim_id": str,
        "score": float,
        "reasoning": str,
        "evidence": {"type": "string", "default": None},
        "uncertainties": {"type": "string", "default": None},
        "tags": {"type": "string", "default": None}
    }
)
async def evaluate_claim_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool for evaluating claims with evidence and scoring.

    Args:
        args: Dictionary with keys:
            - hypergraph_path: Path to hypergraph.json
            - claim_id: ID of claim to evaluate (e.g., "c1")
            - score: Score 0-10
            - reasoning: Why this score was assigned
            - evidence: JSON array string of evidence items (optional)
            - uncertainties: Comma-separated uncertainties (optional)
            - tags: Comma-separated tags like "CRITICAL_BLOCKER" (optional)

    Returns:
        Tool response with confirmation or error
    """
    result = evaluate_claim_impl(
        args.get("hypergraph_path", ""),
        args.get("claim_id", ""),
        args.get("score", 5.0),
        args.get("reasoning", ""),
        args.get("evidence", None),
        args.get("uncertainties", None),
        args.get("tags", None)
    )

    return {
        "content": [{"type": "text", "text": result}]
    }


# Create MCP server with both tools
entailment_server = create_sdk_mcp_server(
    name="entailment",
    version="1.0.0",
    tools=[check_entailment_tool, evaluate_claim_tool]
)


# Hook that runs at end of Claude's turn
async def post_hypergraph_edit_hook(
    input_data: Dict[str, Any],
    _tool_use_id: Optional[str] = None,
    _context: Optional[HookContext] = None
) -> Dict[str, Any]:
    """
    Auto-validate entailment and save history after Claude's turn completes.

    Checks if hypergraph.json was modified during the turn, and if so:
    1. Saves current version to history
    2. Runs entailment validation

    NOTE: Cleanup is NOT automatic - it must be manually invoked by agent or user.
    """
    # Import here to avoid circular imports
    from .hypergraph_manager import HypergraphManager
    import hashlib

    # Get cwd to check for hypergraph files
    cwd = input_data.get("cwd", ".")
    cwd_path = Path(cwd)

    # Check if there's a hypergraph.json in the working directory
    hypergraph_path = cwd_path / "hypergraph.json"
    if not hypergraph_path.exists():
        return {}  # No hypergraph in this directory

    # Resolve to absolute path
    absolute_path = hypergraph_path.resolve()

    # Check if hypergraph has actually changed by comparing hash
    # (to avoid saving history when nothing changed)
    history_dir = absolute_path.parent / ".hypergraph_history"
    history_dir.mkdir(exist_ok=True)

    # Get hash of current file
    with open(absolute_path, 'rb') as f:
        current_hash = hashlib.md5(f.read()).hexdigest()

    # Check if we have a previous hash stored
    hash_file = history_dir / ".last_hash"
    previous_hash = None
    if hash_file.exists():
        with open(hash_file, 'r') as f:
            previous_hash = f.read().strip()

    # If content changed, save to history
    if current_hash != previous_hash:
        print(f"\n[VERSION CONTROL] Saving hypergraph snapshot...")
        mgr = HypergraphManager(absolute_path.parent)

        # Load and re-save to trigger history
        hypergraph = mgr.load_hypergraph()
        mgr._save_hypergraph(hypergraph)

        # Update hash
        with open(hash_file, 'w') as f:
            f.write(current_hash)

        print(f"[VERSION CONTROL] Snapshot saved to .hypergraph_history/")

    # Run entailment check
    print(f"\n[ENTAILMENT CHECK] Validating implications in {absolute_path}...")
    result = check_entailment_impl(str(absolute_path))

    # If there are errors, inject message for Claude to see
    if "❌" in result:
        print(result)
        return {
            "inject_message": {
                "role": "user",
                "content": f"⚠️  Entailment validation failed:\n\n{result}\n\nPlease fix the invalid implications."
            }
        }

    print("✓ All implications passed entailment checking")
    return {}


class ClaudeCodeClient:
    """
    Python wrapper for Claude Agent SDK.

    Enables programmatic interaction with Claude Code using the native SDK.
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
        self.allowed_tools = allowed_tools or []
        self.verbose = verbose
        self.sdk_client: Optional[ClaudeSDKClient] = None
        self.current_system_prompt: Optional[str] = None
        self._loop = None

    def _get_or_create_loop(self):
        """Get or create event loop for async operations."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        loop = self._get_or_create_loop()
        if loop.is_running():
            # Already in async context - create task
            return asyncio.create_task(coro)
        return loop.run_until_complete(coro)

    async def _query_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Send a query to Claude Code (async implementation).

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions

        Returns:
            ClaudeResponse with content and metadata
        """
        # Initialize SDK client if not already done or if system prompt changed
        if self.sdk_client is None or (system_prompt and system_prompt != self.current_system_prompt):
            # Build allowed tools list (include built-in tools + MCP tools)
            allowed = self.allowed_tools.copy() if self.allowed_tools else []
            allowed.append("mcp__entailment__check_entailment")
            allowed.append("mcp__entailment__evaluate_claim")

            options = ClaudeAgentOptions(
                system_prompt=system_prompt or "claude_code",
                allowed_tools=allowed if allowed else None,
                cwd=str(self.working_dir),
                mcp_servers={"entailment": entailment_server},
                hooks={
                    "Stop": [
                        HookMatcher(hooks=[post_hypergraph_edit_hook])
                    ]
                }
            )

            # Close existing client if changing system prompt
            if self.sdk_client is not None:
                try:
                    await self.sdk_client.__aexit__(None, None, None)
                except:
                    pass

            self.sdk_client = ClaudeSDKClient(options=options)
            await self.sdk_client.__aenter__()
            self.current_system_prompt = system_prompt

        # Send query
        try:
            await self.sdk_client.query(prompt)

            # Collect response content with streaming
            response_text = []
            last_was_tool = False

            async for message in self.sdk_client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Add spacing before text if previous was a tool
                            if last_was_tool and block.text.strip():
                                print("\n", end="", flush=True)

                            # Print streaming output
                            print(block.text, end="", flush=True)
                            response_text.append(block.text)
                            last_was_tool = False
                        elif isinstance(block, ToolUseBlock):
                            # Tool use - mark that we need spacing after
                            last_was_tool = True

            print()  # Newline after streaming completes

            return ClaudeResponse(
                content="".join(response_text),
                session_id="active",  # SDK manages sessions internally
                cost_usd=None,  # SDK doesn't expose cost in response
                raw_output={"messages": response_text}
            )
        except Exception as e:
            raise RuntimeError(f"Claude SDK failed: {str(e)}")

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        _resume_session: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Send a query to Claude Code (sync wrapper).

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions
            _resume_session: Optional session ID (kept for compatibility, unused)

        Returns:
            ClaudeResponse with content and metadata
        """
        return self._run_async(
            self._query_async(prompt, system_prompt)
        )

    def start_conversation(
        self,
        initial_prompt: str,
        system_prompt: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Start a new conversation.

        Args:
            initial_prompt: Initial user message
            system_prompt: System instructions

        Returns:
            Response from Claude
        """
        # Close existing client to start fresh
        if self.sdk_client is not None:
            self._run_async(self.sdk_client.__aexit__(None, None, None))
            self.sdk_client = None
            self.current_system_prompt = None

        return self.query(initial_prompt, system_prompt=system_prompt)

    def continue_conversation(self, prompt: str) -> ClaudeResponse:
        """
        Continue the current conversation.

        Args:
            prompt: Next user message

        Returns:
            Response continuing the session
        """
        if self.sdk_client is None:
            raise RuntimeError("No active session. Call start_conversation() first.")

        # Pass resume flag to maintain conversation context
        return self.query(prompt, _resume_session="active")

    def end_conversation(self):
        """End the current conversation session."""
        if self.sdk_client is not None:
            self._run_async(self.sdk_client.__aexit__(None, None, None))
            self.sdk_client = None
            self.current_system_prompt = None

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.sdk_client is not None:
            try:
                self.end_conversation()
            except:
                pass


class ClaudeCodeError(Exception):
    """Exception raised when Claude Code execution fails."""
    pass
