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
    tool,
    create_sdk_mcp_server,
    HookMatcher,
    HookContext
)

from .entailment_checker import check_entailment_skill as check_entailment_impl


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
                "Returns validation errors and suggestions for fixing invalid entailments.",
    input_schema={"hypergraph_path": str}
)
async def check_entailment_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool for checking entailment in hypergraphs.

    Args:
        args: Dictionary with 'hypergraph_path' key

    Returns:
        Tool response with validation results
    """
    hypergraph_path = args.get("hypergraph_path", "")

    # Call the actual implementation
    result = check_entailment_impl(hypergraph_path)

    return {
        "content": [{"type": "text", "text": result}]
    }


# Create MCP server with entailment tool
entailment_server = create_sdk_mcp_server(
    name="entailment",
    version="1.0.0",
    tools=[check_entailment_tool]
)


# Hook that runs after Edit/Write on hypergraph.json
async def post_hypergraph_edit_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> Dict[str, Any]:
    """
    Auto-validate entailment after hypergraph modifications.

    Runs after Edit or Write tools modify hypergraph.json.
    """
    tool_name = input_data.get("name", "")
    tool_input = input_data.get("input", {})

    # Check if this was a hypergraph edit
    file_path = tool_input.get("file_path", "")
    if "hypergraph.json" not in file_path:
        return {}  # Not a hypergraph edit, skip

    print(f"\n[ENTAILMENT CHECK] Validating {file_path}...")

    # Run entailment check
    result = check_entailment_impl(file_path)

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
        system_prompt: Optional[str] = None,
        resume_conversation: bool = False
    ) -> ClaudeResponse:
        """
        Send a query to Claude Code (async implementation).

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions
            resume_conversation: Whether to resume previous conversation

        Returns:
            ClaudeResponse with content and metadata
        """
        # Initialize SDK client if not already done or if system prompt changed
        if self.sdk_client is None or (system_prompt and system_prompt != self.current_system_prompt):
            # Build allowed tools list (include built-in tools + entailment tool)
            allowed = self.allowed_tools.copy() if self.allowed_tools else []
            allowed.append("mcp__entailment__check_entailment")

            options = ClaudeAgentOptions(
                system_prompt=system_prompt or "claude_code",
                allowed_tools=allowed if allowed else None,
                cwd=str(self.working_dir),
                mcp_servers={"entailment": entailment_server},
                hooks={
                    "PostToolUse": [
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

            # Collect response content
            response_text = []
            async for message in self.sdk_client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text.append(block.text)

            return ClaudeResponse(
                content="\n".join(response_text),
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
        resume_session: Optional[str] = None
    ) -> ClaudeResponse:
        """
        Send a query to Claude Code (sync wrapper).

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions
            resume_session: Optional session ID (kept for compatibility)

        Returns:
            ClaudeResponse with content and metadata
        """
        return self._run_async(
            self._query_async(prompt, system_prompt, resume_session is not None)
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
        return self.query(prompt, resume_session="active")

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
