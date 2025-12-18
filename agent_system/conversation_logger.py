"""
Conversation Logger - Comprehensive logging for all agent interactions.

Logs everything:
- User inputs
- Claude responses
- Tool calls with parameters and results
- Session metadata (timestamps, costs, etc.)

Logs are stored centrally in logs/ directory at project root,
independent of whether user is in exploration mode or working on an approach.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ResponsePart:
    """Represents a part of the response - either text or a tool call."""
    type: str  # "text" or "tool"
    content: Optional[str] = None  # For text parts
    tool_name: Optional[str] = None  # For tool parts


@dataclass
class ToolCall:
    """Represents a single tool invocation."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None


@dataclass
class Turn:
    """Represents one turn of conversation (user input + Claude response)."""
    turn_number: int
    user_input: str
    claude_response: str
    tools_used: List[ToolCall] = field(default_factory=list)
    response_parts: List[ResponsePart] = field(default_factory=list)  # Interleaved text/tool order
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cost_usd: Optional[float] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationLog:
    """Complete log of a conversation session."""
    session_id: str
    approach_name: Optional[str] = None
    approach_dir: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None
    turns: List[Turn] = field(default_factory=list)
    system_prompt: Optional[str] = None
    working_directory: Optional[str] = None
    # Claude SDK session ID - for resuming Claude's conversation memory
    claude_sdk_session_id: Optional[str] = None


class ConversationLogger:
    """
    Logger for complete conversation history.

    Captures:
    - Every user message
    - Every Claude response
    - Every tool call (name, parameters, result)
    - Session metadata

    Logs are saved to: logs/conversation_YYYY-MM-DD_HH-MM-SS_<hash>.json
    """

    def __init__(self, logs_dir: Path,
                 approach_name: Optional[str] = None,
                 approach_dir: Optional[Path] = None,
                 working_dir: Optional[Path] = None,
                 system_prompt: Optional[str] = None):
        """
        Initialize conversation logger.

        Args:
            logs_dir: Root logs directory (project_root/logs)
            approach_name: Name of approach if working on one (None otherwise)
            approach_dir: Path to approach directory if applicable
            working_dir: Working directory for the session
            system_prompt: System prompt used for the session
        """
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate session ID
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_hash = hashlib.md5(f"{timestamp}{approach_name}".encode()).hexdigest()[:8]
        self.session_id = f"{timestamp}_{session_hash}"

        # Initialize conversation log
        self.log = ConversationLog(
            session_id=self.session_id,
            approach_name=approach_name,
            approach_dir=str(approach_dir) if approach_dir else None,
            system_prompt=system_prompt,
            working_directory=str(working_dir) if working_dir else None
        )

        # Track current turn tools
        self.current_turn_tools: List[ToolCall] = []
        # Track interleaved response parts (text and tool indicators)
        self.current_response_parts: List[ResponsePart] = []

        # Log file path
        self.log_file = self.logs_dir / f"conversation_{self.session_id}.json"

        print(f"[LOGGER] Session started: {self.session_id}")
        print(f"[LOGGER] Log file: {self.log_file}")

    def log_turn_start(self, user_input: str):
        """
        Log the start of a new turn with user input.

        Args:
            user_input: User's message/prompt
        """
        self.current_turn_tools = []
        self.current_response_parts = []
        self._current_user_input = user_input
        self._turn_start_time = datetime.now()

    def log_text_part(self, text: str):
        """
        Log a text chunk during streaming to track interleaved order.

        Args:
            text: Text content from the stream
        """
        # Append to last text part if it exists, otherwise create new
        if self.current_response_parts and self.current_response_parts[-1].type == "text":
            # Accumulate into existing text part
            self.current_response_parts[-1].content += text
        else:
            # Create new text part
            self.current_response_parts.append(ResponsePart(type="text", content=text))

    def log_tool_use(self, tool_name: str):
        """
        Log a tool use indicator during streaming.

        This is called when a tool starts running, to track the order.
        The full tool_call with results is logged separately via log_tool_call.

        Args:
            tool_name: Name of the tool being used
        """
        self.current_response_parts.append(ResponsePart(type="tool", tool_name=tool_name))

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any],
                      result: Optional[str] = None, error: Optional[str] = None,
                      duration_ms: Optional[float] = None):
        """
        Log a tool call during the current turn.

        Args:
            tool_name: Name of the tool (e.g., "Read", "Write", "mcp__entailment__check_entailment")
            parameters: Tool parameters as dict
            result: Tool result/output (optional)
            error: Error message if tool failed (optional)
            duration_ms: Execution duration in milliseconds (optional)
        """
        tool_call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=error,
            duration_ms=duration_ms
        )
        self.current_turn_tools.append(tool_call)

    def log_turn_end(self, claude_response: str, cost_usd: Optional[float] = None,
                     raw_metadata: Optional[Dict[str, Any]] = None):
        """
        Log the end of a turn with Claude's response.

        Args:
            claude_response: Claude's complete response text
            cost_usd: Cost of this turn in USD (optional)
            raw_metadata: Additional metadata to store (optional)
        """
        turn = Turn(
            turn_number=len(self.log.turns) + 1,
            user_input=self._current_user_input,
            claude_response=claude_response,
            tools_used=self.current_turn_tools.copy(),
            response_parts=self.current_response_parts.copy(),
            cost_usd=cost_usd,
            raw_metadata=raw_metadata or {}
        )

        self.log.turns.append(turn)
        self.current_turn_tools = []
        self.current_response_parts = []

        # Save after each turn
        self.save()

    def end_session(self):
        """Mark session as ended and save final state."""
        self.log.ended_at = datetime.now().isoformat()
        self.save()
        print(f"[LOGGER] Session ended: {self.session_id}")
        print(f"[LOGGER] Total turns: {len(self.log.turns)}")

    def set_sdk_session_id(self, sdk_session_id: str):
        """
        Store the Claude SDK session ID in the log.

        This allows resuming Claude's conversation memory when switching
        back to this conversation.

        Args:
            sdk_session_id: The session ID returned by Claude SDK
        """
        if sdk_session_id and sdk_session_id != self.log.claude_sdk_session_id:
            self.log.claude_sdk_session_id = sdk_session_id
            self.save()
            print(f"[LOGGER] SDK session ID saved: {sdk_session_id[:40]}...")

    def save(self):
        """Save current log state to JSON file."""
        try:
            # Convert to dict and save
            log_dict = self._to_dict(self.log)

            with open(self.log_file, 'w') as f:
                json.dump(log_dict, f, indent=2)
        except Exception as e:
            print(f"[LOGGER] Warning: Failed to save log: {e}")

    def _to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dict recursively."""
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for field_name in obj.__dataclass_fields__:
                value = getattr(obj, field_name)
                if isinstance(value, list):
                    result[field_name] = [self._to_dict(item) for item in value]
                elif hasattr(value, '__dataclass_fields__'):
                    result[field_name] = self._to_dict(value)
                else:
                    result[field_name] = value
            return result
        return obj

    def get_summary(self) -> str:
        """Get a human-readable summary of the session."""
        total_tools = sum(len(turn.tools_used) for turn in self.log.turns)
        total_cost = sum(turn.cost_usd for turn in self.log.turns if turn.cost_usd)

        approach_line = f"Approach: {self.log.approach_name}\n" if self.log.approach_name else ""

        summary = f"""
Session Summary
===============
Session ID: {self.session_id}
{approach_line}Started: {self.log.started_at}
{"Ended: " + self.log.ended_at if self.log.ended_at else "Status: Active"}

Turns: {len(self.log.turns)}
Total tools used: {total_tools}
Total cost: ${total_cost:.4f}

Log file: {self.log_file}
"""
        return summary.strip()


def load_conversation_log(log_file: Path) -> ConversationLog:
    """
    Load a conversation log from JSON file.

    Args:
        log_file: Path to log JSON file

    Returns:
        ConversationLog object
    """
    with open(log_file) as f:
        data = json.load(f)

    # Reconstruct turns
    turns = []
    for turn_data in data.get('turns', []):
        tools = []
        for tool_data in turn_data.get('tools_used', []):
            tools.append(ToolCall(**tool_data))

        turn_data['tools_used'] = tools
        turns.append(Turn(**turn_data))

    # Reconstruct log
    data['turns'] = turns
    return ConversationLog(**data)


def list_conversation_logs(logs_dir: Path,
                          approach_name: Optional[str] = None) -> List[Path]:
    """
    List all conversation log files.

    Args:
        logs_dir: Root logs directory
        approach_name: Filter by approach name (optional)

    Returns:
        List of log file paths, sorted by date (newest first)
    """
    if not logs_dir.exists():
        return []

    log_files = sorted(
        logs_dir.glob("conversation_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # Apply filter if specified
    if approach_name:
        filtered = []
        for log_file in log_files:
            try:
                log = load_conversation_log(log_file)
                if log.approach_name == approach_name:
                    filtered.append(log_file)
            except:
                continue
        return filtered

    return log_files


def print_log_summary(log_file: Path):
    """
    Print a summary of a conversation log.

    Args:
        log_file: Path to log JSON file
    """
    try:
        log = load_conversation_log(log_file)

        print(f"\nSession: {log.session_id}")
        if log.approach_name:
            print(f"Approach: {log.approach_name}")
        print(f"Started: {log.started_at}")
        if log.ended_at:
            print(f"Ended: {log.ended_at}")
        print(f"\nTurns: {len(log.turns)}")

        total_tools = sum(len(turn.tools_used) for turn in log.turns)
        print(f"Total tools used: {total_tools}")

        total_cost = sum(turn.cost_usd for turn in log.turns if turn.cost_usd)
        if total_cost > 0:
            print(f"Total cost: ${total_cost:.4f}")

        print(f"\nLog file: {log_file}")

    except Exception as e:
        print(f"Error reading log: {e}")


if __name__ == "__main__":
    # Test the logger
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        logs_dir = Path(tmpdir) / "logs"

        # Create logger
        logger = ConversationLogger(
            logs_dir=logs_dir,
            working_dir=Path.cwd()
        )

        # Simulate a conversation
        logger.log_turn_start("What is the capital of France?")
        logger.log_tool_call("WebSearch", {"query": "capital of France"}, result="Paris")
        logger.log_turn_end("The capital of France is Paris.", cost_usd=0.001)

        logger.log_turn_start("Tell me more about it")
        logger.log_tool_call("WebSearch", {"query": "Paris France facts"}, result="...")
        logger.log_turn_end("Paris is a beautiful city...", cost_usd=0.002)

        logger.end_session()

        print(logger.get_summary())
        print("\n" + "="*50)
        print("Log file contents:")
        print("="*50)
        with open(logger.log_file) as f:
            print(f.read())
