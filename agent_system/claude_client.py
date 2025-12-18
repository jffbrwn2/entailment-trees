"""
Claude Code Client - Wrapper for Claude Agent SDK.

Provides Python interface to the Claude Agent SDK for programmatic interaction.
"""

import asyncio
import os
import json
from typing import Optional, List, Dict, Any, AsyncIterator, Union
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    tool,
    create_sdk_mcp_server,
    HookMatcher,
    HookContext
)

from .entailment_checker import check_entailment_skill as check_entailment_impl
from .claim_evaluator import evaluate_claim_skill as evaluate_claim_impl, add_evidence_skill as add_evidence_impl
from .gapmap_client import GapMapClient
from .conversation_logger import ConversationLogger
from .path_utils import set_approach_dir, resolve_path
from .runtime_settings import get_settings

try:
    from edison_client import EdisonClient, JobNames
    EDISON_AVAILABLE = True
except ImportError:
    EDISON_AVAILABLE = False
    print("⚠️  edison-client not available. Edison tools will be disabled.")


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


@dataclass
class StreamEvent:
    """Base class for streaming events from Claude."""
    type: str  # "text", "tool_use", "tool_result", "error", "done"


@dataclass
class TextEvent(StreamEvent):
    """Text chunk from Claude's response."""
    text: str

    def __init__(self, text: str):
        self.type = "text"
        self.text = text


@dataclass
class ToolUseEvent(StreamEvent):
    """Notification that a tool is being used."""
    tool_name: str
    tool_input: Dict[str, Any]

    def __init__(self, tool_name: str, tool_input: Dict[str, Any]):
        self.type = "tool_use"
        self.tool_name = tool_name
        self.tool_input = tool_input


@dataclass
class ToolResultEvent(StreamEvent):
    """Result from a tool execution."""
    tool_name: str
    result: str
    is_error: bool = False

    def __init__(self, tool_name: str, result: str, is_error: bool = False):
        self.type = "tool_result"
        self.tool_name = tool_name
        self.result = result
        self.is_error = is_error


@dataclass
class ErrorEvent(StreamEvent):
    """Error during execution."""
    error: str

    def __init__(self, error: str):
        self.type = "error"
        self.error = error


@dataclass
class DoneEvent(StreamEvent):
    """Stream complete."""
    full_response: str

    def __init__(self, full_response: str):
        self.type = "done"
        self.full_response = full_response


@dataclass
class ClientMode:
    """Configuration for a client mode (exploration or approach)."""
    working_dir: Path
    approach_name: Optional[str] = None
    approach_dir: Optional[Path] = None


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


# Define add_evidence as SDK tool
@tool(
    name="add_evidence",
    description="Add evidence to a claim in the hypergraph. "
                "Evidence must follow the schema: "
                "- simulation: requires 'type', 'source' (file path), 'lines' (e.g. '10-50'), 'code' (extracted code) "
                "- literature: requires 'type', 'source' (citation/file), 'reference_text' (exact quote) "
                "- calculation: requires 'type', 'equations' (LaTeX), 'program' (Python code). "
                "Validates format and updates last_evidence_modified timestamp. "
                "Use this BEFORE evaluate_claim to add new evidence.",
    input_schema={
        "hypergraph_path": str,
        "claim_id": str,
        "evidence": str  # JSON string of evidence item or array
    }
)
async def add_evidence_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool for adding validated evidence to claims.

    Args:
        args: Dictionary with keys:
            - hypergraph_path: Path to hypergraph.json
            - claim_id: ID of claim (e.g., "c1")
            - evidence: JSON string of evidence item(s)

    Returns:
        Tool response with confirmation or error
    """
    result = add_evidence_impl(
        args.get("hypergraph_path", ""),
        args.get("claim_id", ""),
        args.get("evidence", "")
    )

    return {
        "content": [{"type": "text", "text": result}]
    }


# Define claim evaluator as SDK tool
@tool(
    name="evaluate_claim",
    description="Evaluate a claim using Claude to analyze its existing evidence and determine score. "
                "Claude examines the evidence already attached to the claim and autonomously assigns "
                "a score 0-10 based on how well the evidence supports the claim. "
                "If no evidence exists, score = 0. "
                "Use add_evidence BEFORE this tool to attach evidence to the claim. "
                "Returns: calculated score + reasoning.",
    input_schema={
        "hypergraph_path": str,
        "claim_id": str
    }
)
async def evaluate_claim_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool for autonomously evaluating claims with Claude based on existing evidence.

    Args:
        args: Dictionary with keys:
            - hypergraph_path: Path to hypergraph.json
            - claim_id: ID of claim to evaluate (e.g., "c1")

    Returns:
        Tool response with calculated score, reasoning, or error
    """
    result = evaluate_claim_impl(
        args.get("hypergraph_path", ""),
        args.get("claim_id", "")
    )

    return {
        "content": [{"type": "text", "text": result}]
    }


# Edison Scientific tools (only if edison-client is available)
if EDISON_AVAILABLE:
    # Initialize Edison client with API key from environment
    _edison_client = None
    # Working directory (approach directory) - set by ClaudeCodeClient
    _approach_dir: Optional[Path] = None

    def _get_edison_client():
        global _edison_client
        if _edison_client is None:
            api_key = os.getenv("EDISON_API_KEY")
            if not api_key:
                raise ValueError("EDISON_API_KEY environment variable not set")
            _edison_client = EdisonClient(api_key=api_key)
        return _edison_client

    def _get_approach_dir() -> Path:
        """Get the current approach directory."""
        if _approach_dir is None:
            raise RuntimeError("Approach directory not set. Edison tools require ClaudeCodeClient to be initialized first.")
        return _approach_dir

    def _log_edison_task(approach_dir: str, task_id: str, task_type: str, query: str):
        """Log Edison task to JSON file in approach's references folder."""
        # References folder is defined in HypergraphManager alongside simulations
        log_path = Path(approach_dir) / "references" / "edison_tasks.json"

        # Ensure references directory exists
        log_path.parent.mkdir(exist_ok=True)

        # Load existing log
        if log_path.exists():
            with open(log_path) as f:
                tasks = json.load(f)
        else:
            tasks = []

        # Add new task
        tasks.append({
            "task_id": task_id,
            "type": task_type,
            "query": query,
            "submitted_at": datetime.now().isoformat(),
            "status": "pending"
        })

        # Save log
        with open(log_path, 'w') as f:
            json.dump(tasks, f, indent=2)

    def _update_edison_task_status(approach_dir: str, task_id: str, status: str, answer: Optional[str] = None):
        """Update status of logged Edison task in approach's references folder."""
        log_path = Path(approach_dir) / "references" / "edison_tasks.json"

        if not log_path.exists():
            return

        with open(log_path) as f:
            tasks = json.load(f)

        # Find and update task
        for task in tasks:
            if task["task_id"] == task_id:
                task["status"] = status
                task["completed_at"] = datetime.now().isoformat()
                if answer:
                    task["answer"] = answer
                break

        # Save updated log
        with open(log_path, 'w') as f:
            json.dump(tasks, f, indent=2)

    @tool(
        name="literature_search",
        description="Search scientific literature and get cited answers to research questions. "
                    "Uses Edison's PaperQA2 to query scientific databases asynchronously. "
                    "Submits task and returns task ID. Use check_edison_task to get results. "
                    "Tasks are logged in references/edison_tasks.json. "
                    "Perfect for gathering evidence for entailment tree claims.",
        input_schema={
            "query": str,
        }
    )
    async def edison_literature_search(args: Dict[str, Any]) -> Dict[str, Any]:
        """Search scientific literature with Edison (async)."""
        query = args.get("query", "")

        try:
            # Get approach directory from module state
            approach_path = _get_approach_dir()

            client = _get_edison_client()
            task_data = {"name": JobNames.LITERATURE, "query": query}

            # Create task asynchronously
            task_id = await client.acreate_task(task_data)

            # Log task to approach's references folder
            _log_edison_task(str(approach_path), task_id, "literature", query)

            result_text = (
                f"✓ Literature search task submitted\n\n"
                f"**Task ID:** {task_id}\n"
                f"**Query:** {query}\n\n"
                f"Task logged in references/edison_tasks.json\n"
                f"Use check_edison_task(task_id=\"{task_id}\") to check status and get results."
            )

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Edison literature search failed: {str(e)}"}]}

    @tool(
        name="precedent_search",
        description="Check if a scientific concept or approach has been previously explored. "
                    "Uses Edison to search for prior work in scientific literature asynchronously. "
                    "Submits task and returns task ID. Use check_edison_task to get results. "
                    "Tasks are logged in references/edison_tasks.json. "
                    "Useful for assessing novelty and finding related approaches.",
        input_schema={
            "query": str,
        }
    )
    async def edison_precedent_search(args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for precedents in scientific literature with Edison (async)."""
        query = args.get("query", "")

        try:
            # Get approach directory from module state
            approach_path = _get_approach_dir()

            client = _get_edison_client()
            task_data = {"name": JobNames.PRECEDENT, "query": query}

            # Create task asynchronously
            task_id = await client.acreate_task(task_data)

            # Log task to approach's references folder
            _log_edison_task(str(approach_path), task_id, "precedent", query)

            result_text = (
                f"✓ Precedent search task submitted\n\n"
                f"**Task ID:** {task_id}\n"
                f"**Query:** {query}\n\n"
                f"Task logged in references/edison_tasks.json\n"
                f"Use check_edison_task(task_id=\"{task_id}\") to check status and get results."
            )

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Edison precedent search failed: {str(e)}"}]}

    @tool(
        name="check_edison_task",
        description="Check status and get results of a previously submitted Edison task. "
                    "Provide the task ID. "
                    "Returns current status (pending/running/success/failed) and answer if complete. "
                    "Updates task status in references/edison_tasks.json.",
        input_schema={
            "task_id": str,
        }
    )
    async def check_edison_task(args: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of Edison task."""
        task_id = args.get("task_id", "")

        try:
            # Get approach directory from module state
            approach_path = _get_approach_dir()

            client = _get_edison_client()

            # Get task status
            task_status = await client.aget_task(task_id)

            # Build result text
            status = task_status.status
            result_text = f"**Task ID:** {task_id}\n**Status:** {status}\n\n"

            if status == "success":
                answer = task_status.answer if hasattr(task_status, 'answer') else "No answer available"
                result_text += f"**Answer:**\n{answer}"

                # Update log with completion
                _update_edison_task_status(str(approach_path), task_id, status, answer)
            elif status == "failed":
                result_text += "❌ Task failed"
                _update_edison_task_status(str(approach_path), task_id, status)
            elif status in ["pending", "running"]:
                result_text += f"⏳ Task is {status}... check again later"

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Failed to check Edison task: {str(e)}"}]}

    # Create Edison MCP server
    edison_server = create_sdk_mcp_server(
        name="edison",
        version="1.0.0",
        tools=[edison_literature_search, edison_precedent_search, check_edison_task]
    )
else:
    edison_server = None


# GAP-map tools
_gapmap_client = None

def _get_gapmap_client():
    """Get or create GAP-map client."""
    global _gapmap_client
    if _gapmap_client is None:
        _gapmap_client = GapMapClient()
    return _gapmap_client


@tool(
    name="list_fields",
    description="List all research fields/domains in GAP-map. "
                "Returns the 20 major fields with descriptions (e.g., Computation, Biology, Global Health). "
                "Use this to explore available domains or filter searches by field.",
    input_schema={}
)
async def gapmap_list_fields(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all research fields."""
    try:
        client = _get_gapmap_client()
        fields = client.get_all_fields()

        result_text = f"**GAP-map Research Fields** ({len(fields)} total):\n\n"

        for field in fields:
            result_text += f"**{field['name']}**\n"
            result_text += f"{field['description']}\n"
            result_text += f"ID: `{field['id']}`\n\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed to list fields: {str(e)}"}]}


@tool(
    name="list_gaps",
    description="List all research gaps in GAP-map. "
                "Returns all 104 catalogued gaps with summaries. "
                "Optionally filter by field. Use this to browse available problems.",
    input_schema={
        "field": {"type": "string", "default": None},  # Optional: field name to filter
    }
)
async def gapmap_list_gaps(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all research gaps."""
    field = args.get("field", None)

    try:
        client = _get_gapmap_client()
        gaps = client.get_all_gaps()

        # Filter by field if specified
        if field:
            field_lower = field.lower()
            gaps = [g for g in gaps if field_lower in g.get("field", {}).get("name", "").lower()]

        if not gaps:
            return {"content": [{"type": "text", "text": f"No gaps found" + (f" in field '{field}'" if field else "")}]}

        result_text = f"**GAP-map Research Gaps** ({len(gaps)} total"
        if field:
            result_text += f" in {field}"
        result_text += "):\n\n"

        for gap in gaps:
            field_name = gap.get("field", {}).get("name", "Unknown")
            cap_count = len(gap.get("foundationalCapabilities", []))

            result_text += f"**{gap['name']}** ({field_name})\n"
            result_text += f"{gap['description']}\n"
            result_text += f"Gap ID: `{gap['id']}` | Capabilities: {cap_count}\n\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed: {str(e)}"}]}


@tool(
    name="search_gaps",
    description="Search GAP-map for open research problems. "
                "104 catalogued gaps across fields like Computation, Biology, Materials, etc. "
                "Returns gap ID, name, description, field, tags, and count of proposed capabilities. "
                "Use gap_id with get_capabilities to see proposed solutions.",
    input_schema={
        "query": str,
        "field": {"type": "string", "default": None},  # Optional: field name to filter
    }
)
async def gapmap_search_gaps(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for research gaps."""
    query = args.get("query", "")
    field = args.get("field", None)

    try:
        client = _get_gapmap_client()
        gaps = client.search_gaps(query, field=field)

        if not gaps:
            return {"content": [{"type": "text", "text": f"No gaps found matching '{query}'"}]}

        result_text = f"Found {len(gaps)} gap(s):\n\n"

        for gap in gaps:
            field_name = gap.get("field", {}).get("name", "Unknown")
            tags = gap.get("tags", [])
            tags_str = f" [{', '.join(tags)}]" if tags else ""
            cap_count = len(gap.get("foundationalCapabilities", []))

            result_text += f"**{gap['name']}** ({field_name}){tags_str}\n"
            result_text += f"{gap['description']}\n"
            result_text += f"Gap ID: `{gap['id']}`\n"
            result_text += f"Proposed capabilities: {cap_count}\n\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Search failed: {str(e)}"}]}


@tool(
    name="list_capabilities",
    description="List all foundational capabilities in GAP-map. "
                "Returns all 368 catalogued approaches/technologies with summaries. "
                "Use this to browse what solutions have been proposed across all problems.",
    input_schema={}
)
async def gapmap_list_capabilities(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all capabilities."""
    try:
        client = _get_gapmap_client()
        capabilities = client.get_all_capabilities()

        result_text = f"**GAP-map Foundational Capabilities** ({len(capabilities)} total):\n\n"

        for cap in capabilities:
            tags = cap.get("tags", [])
            tags_str = f" [{', '.join(tags)}]" if tags else ""
            gap_count = len(cap.get("gaps", []))
            resource_count = len(cap.get("resources", []))

            result_text += f"**{cap['name']}**{tags_str}\n"
            result_text += f"{cap['description']}\n" if cap['description'] else ""
            result_text += f"ID: `{cap['id']}` | Gaps addressed: {gap_count} | Resources: {resource_count}\n\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed: {str(e)}"}]}


@tool(
    name="get_capabilities",
    description="Get foundational capabilities for a gap. "
                "Returns proposed approaches/technologies that could address the problem. "
                "Each capability includes description, tags, and count of linked resources. "
                "Use capability_id with get_resources to access papers, companies, initiatives, etc.",
    input_schema={
        "gap_id": str,
    }
)
async def gapmap_get_capabilities(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get capabilities for a gap."""
    gap_id = args.get("gap_id", "")

    try:
        client = _get_gapmap_client()
        gap = client.get_gap_by_id(gap_id)
        if not gap:
            return {"content": [{"type": "text", "text": f"❌ Gap not found: {gap_id}"}]}

        capabilities = client.get_capabilities_for_gap(gap_id)

        if not capabilities:
            return {"content": [{"type": "text", "text": f"Gap **{gap['name']}** has no linked capabilities yet."}]}

        result_text = f"**Gap:** {gap['name']}\n\n"
        result_text += f"**{len(capabilities)} Foundational Capabilities:**\n\n"

        for cap in capabilities:
            tags = cap.get("tags", [])
            tags_str = f" [{', '.join(tags)}]" if tags else ""
            resource_count = len(cap.get("resources", []))

            result_text += f"**{cap['name']}**{tags_str}\n"
            result_text += f"{cap['description']}\n"
            result_text += f"Capability ID: `{cap['id']}`\n"
            result_text += f"Resources: {resource_count}\n\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed: {str(e)}"}]}


@tool(
    name="list_resources",
    description="List all resources in GAP-map. "
                "Returns all 1062 resources (papers, companies, FROs, initiatives, etc.). "
                "Optionally filter by resource type. Use this to browse available resources.",
    input_schema={
        "resource_type": {"type": "string", "default": None},  # Optional: e.g., "Research and Reviews", "Company", "FRO"
    }
)
async def gapmap_list_resources(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all resources."""
    resource_type = args.get("resource_type", None)

    try:
        client = _get_gapmap_client()
        resources = client.get_all_resources()

        # Filter by type if specified
        if resource_type:
            resources = [r for r in resources if resource_type in r.get("types", [])]

        if not resources:
            return {"content": [{"type": "text", "text": f"No resources found" + (f" of type '{resource_type}'" if resource_type else "")}]}

        result_text = f"**GAP-map Resources** ({len(resources)} total"
        if resource_type:
            result_text += f" of type '{resource_type}'"
        result_text += "):\n\n"

        for res in resources[:15]:  # Show first 15
            types = res.get("types", [])
            types_str = f" ({', '.join(types)})" if types else ""
            url = res.get("url", "")

            result_text += f"**{res['title']}**{types_str}\n"
            if url:
                result_text += f"{url}\n"
            result_text += "\n"

        if len(resources) > 15:
            result_text += f"(Showing 15 of {len(resources)} resources)"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed: {str(e)}"}]}


@tool(
    name="get_resources",
    description="Get resources for a capability. "
                "Returns papers, companies, initiatives, datasets, etc. (1062 total resources). "
                "Resource types: Research and Reviews, FRO, Company, Initiative, Technology Seed, etc. "
                "Each resource has title, URL, summary, and type.",
    input_schema={
        "capability_id": str,
    }
)
async def gapmap_get_resources(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get resources for a capability."""
    capability_id = args.get("capability_id", "")

    try:
        client = _get_gapmap_client()

        # Get capability details
        capabilities = client.get_all_capabilities()
        capability = next((c for c in capabilities if c.get("id") == capability_id), None)

        if not capability:
            return {"content": [{"type": "text", "text": f"❌ Capability not found: {capability_id}"}]}

        resources = client.get_resources_for_capability(capability_id)

        if not resources:
            return {"content": [{"type": "text", "text": f"Capability **{capability['name']}** has no linked resources yet."}]}

        result_text = f"**Capability:** {capability['name']}\n\n"
        result_text += f"**{len(resources)} Resources:**\n\n"

        for res in resources:
            types = res.get("types", [])
            types_str = f" ({', '.join(types)})" if types else ""
            url = res.get("url", "")
            summary = res.get("summary", "").strip()

            result_text += f"**{res['title']}**{types_str}\n"
            if summary:
                result_text += f"{summary}\n"
            if url:
                result_text += f"URL: {url}\n"
            result_text += "\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"❌ Failed: {str(e)}"}]}


# Create GAP-map MCP server
gapmap_server = create_sdk_mcp_server(
    name="gapmap",
    version="1.0.0",
    tools=[
        gapmap_list_fields,
        gapmap_list_gaps,
        gapmap_search_gaps,
        gapmap_list_capabilities,
        gapmap_get_capabilities,
        gapmap_list_resources,
        gapmap_get_resources
    ]
)


# Create MCP server with entailment tools
entailment_server = create_sdk_mcp_server(
    name="entailment",
    version="1.0.0",
    tools=[check_entailment_tool, add_evidence_tool, evaluate_claim_tool]
)


# Global logger instance (set by ClaudeCodeClient)
_current_logger: Optional[ConversationLogger] = None


# Hook that logs all tool calls
async def tool_logging_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str] = None,
    context: Optional[HookContext] = None
) -> Dict[str, Any]:
    """
    Hook that logs every tool call with parameters and results.

    Called after each tool execution (PostToolUse hook).
    """
    global _current_logger

    if _current_logger is None:
        return {}

    # Extract tool information from input_data
    # PostToolUse structure has: tool_name, tool_input, tool_response
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response")

    # Parse result/error from tool_response
    result = None
    error = None
    if tool_response:
        if isinstance(tool_response, dict):
            if "error" in tool_response:
                error = str(tool_response["error"])
            elif "content" in tool_response:
                # MCP tools return content in a specific format
                result = str(tool_response["content"])
            else:
                result = str(tool_response)
        else:
            result = str(tool_response)

    # Log the tool call
    _current_logger.log_tool_call(
        tool_name=tool_name,
        parameters=tool_input,
        result=result,
        error=error
    )

    return {}


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
        mode: ClientMode,
        allowed_tools: Optional[List[str]] = None,
        verbose: bool = False,
        logger: Optional[ConversationLogger] = None
    ):
        """
        Initialize Claude Code client.

        Args:
            mode: Client mode configuration (working dir, approach info)
            allowed_tools: List of tools to allow (e.g., ["Write", "Read", "Bash"])
            verbose: Enable verbose logging
            logger: ConversationLogger instance for logging all interactions
        """
        self.mode = mode
        self.allowed_tools = allowed_tools or []
        self.verbose = verbose
        self.sdk_client: Optional[ClaudeSDKClient] = None
        self.current_system_prompt: Optional[str] = None
        self._loop = None
        self.logger = logger
        self.session_id: Optional[str] = None  # Session ID for resuming conversations

        # Set global logger for hooks
        if logger:
            global _current_logger
            _current_logger = logger

    def set_session_id(self, session_id: Optional[str]) -> None:
        """Set the session ID for conversation resumption."""
        self.session_id = session_id

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.session_id

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
        # Log turn start
        if self.logger:
            self.logger.log_turn_start(prompt)

        # Initialize SDK client if not already done
        # OR if we're explicitly changing the system prompt (not None)
        should_recreate = (
            self.sdk_client is None or
            (system_prompt is not None and system_prompt != self.current_system_prompt)
        )

        if should_recreate:
            # Set approach directory for path resolution in tools
            set_approach_dir(self.mode.working_dir)

            # Also set for Edison tools if available
            if EDISON_AVAILABLE:
                global _approach_dir
                _approach_dir = self.mode.working_dir

            # Get runtime settings for tool toggles
            runtime_settings = get_settings()

            # Build allowed tools list (include built-in tools + MCP tools)
            allowed = self.allowed_tools.copy() if self.allowed_tools else []
            allowed.append("mcp__entailment__check_entailment")
            allowed.append("mcp__entailment__add_evidence")
            allowed.append("mcp__entailment__evaluate_claim")

            # Build MCP servers dict (always include entailment)
            mcp_servers_dict = {
                "entailment": entailment_server,
            }

            # Add Edison tools if available AND enabled in settings
            if EDISON_AVAILABLE and edison_server and runtime_settings.edison_tools_enabled:
                allowed.append("mcp__edison__literature_search")
                allowed.append("mcp__edison__precedent_search")
                allowed.append("mcp__edison__check_edison_task")
                mcp_servers_dict["edison"] = edison_server

            # Add GAP-map tools if enabled in settings
            if runtime_settings.gapmap_tools_enabled:
                allowed.append("mcp__gapmap__list_fields")
                allowed.append("mcp__gapmap__list_gaps")
                allowed.append("mcp__gapmap__search_gaps")
                allowed.append("mcp__gapmap__list_capabilities")
                allowed.append("mcp__gapmap__get_capabilities")
                allowed.append("mcp__gapmap__list_resources")
                allowed.append("mcp__gapmap__get_resources")
                mcp_servers_dict["gapmap"] = gapmap_server

            options = ClaudeAgentOptions(
                system_prompt=system_prompt or "claude_code",
                allowed_tools=allowed if allowed else None,
                cwd=str(self.mode.working_dir),
                mcp_servers=mcp_servers_dict,
                resume=self.session_id,  # Resume previous session if set
                hooks={
                    "PostToolUse": [
                        HookMatcher(hooks=[tool_logging_hook])
                    ],
                    "Stop": [
                        HookMatcher(hooks=[post_hypergraph_edit_hook])
                    ]
                }
            )

            # Don't try to close existing client - anyio cancel scopes must be exited
            # in the same task they were entered. Just abandon and create fresh.

            self.sdk_client = ClaudeSDKClient(options=options)
            await self.sdk_client.__aenter__()
            self.current_system_prompt = system_prompt

        # Send query
        try:
            # Use session_id if set (for resuming conversations)
            query_session_id = self.session_id or "default"
            await self.sdk_client.query(prompt, session_id=query_session_id)

            # Collect response content with streaming
            response_text = []
            last_was_tool = False

            async for message in self.sdk_client.receive_response():
                # Capture session ID from result message (sent at end of response)
                if isinstance(message, ResultMessage):
                    if hasattr(message, 'session_id') and message.session_id:
                        self.session_id = message.session_id
                elif isinstance(message, AssistantMessage):
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

            # Log turn end
            response_content = "".join(response_text)
            if self.logger:
                self.logger.log_turn_end(
                    claude_response=response_content,
                    cost_usd=None,  # SDK doesn't expose cost
                    raw_metadata={"messages": response_text}
                )

            return ClaudeResponse(
                content=response_content,
                session_id="active",  # SDK manages sessions internally
                cost_usd=None,  # SDK doesn't expose cost in response
                raw_output={"messages": response_text}
            )
        except Exception as e:
            # Log error if logger available
            if self.logger:
                self.logger.log_turn_end(
                    claude_response=f"ERROR: {str(e)}",
                    raw_metadata={"error": str(e)}
                )
            raise RuntimeError(f"Claude SDK failed: {str(e)}")

    async def _query_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[Union[TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent]]:
        """
        Send a query to Claude Code and yield streaming events.

        This is the web-friendly version that yields events instead of printing.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions

        Yields:
            StreamEvent subclasses: TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent
        """
        # Log turn start
        if self.logger:
            self.logger.log_turn_start(prompt)

        # Always create a fresh SDK client for streaming requests.
        # The SDK client cannot be reused across different HTTP requests (different async tasks)
        # because anyio cancel scopes must be entered/exited in the same task.
        if True:  # Always recreate for streaming
            # Set approach directory for path resolution in tools
            set_approach_dir(self.mode.working_dir)

            # Also set for Edison tools if available
            if EDISON_AVAILABLE:
                global _approach_dir
                _approach_dir = self.mode.working_dir

            # Get runtime settings for tool toggles
            runtime_settings = get_settings()

            # Build allowed tools list (include built-in tools + MCP tools)
            allowed = self.allowed_tools.copy() if self.allowed_tools else []
            allowed.append("mcp__entailment__check_entailment")
            allowed.append("mcp__entailment__add_evidence")
            allowed.append("mcp__entailment__evaluate_claim")

            # Build MCP servers dict (always include entailment)
            mcp_servers_dict = {
                "entailment": entailment_server,
            }

            # Add Edison tools if available AND enabled in settings
            if EDISON_AVAILABLE and edison_server and runtime_settings.edison_tools_enabled:
                allowed.append("mcp__edison__literature_search")
                allowed.append("mcp__edison__precedent_search")
                allowed.append("mcp__edison__check_edison_task")
                mcp_servers_dict["edison"] = edison_server

            # Add GAP-map tools if enabled in settings
            if runtime_settings.gapmap_tools_enabled:
                allowed.append("mcp__gapmap__list_fields")
                allowed.append("mcp__gapmap__list_gaps")
                allowed.append("mcp__gapmap__search_gaps")
                allowed.append("mcp__gapmap__list_capabilities")
                allowed.append("mcp__gapmap__get_capabilities")
                allowed.append("mcp__gapmap__list_resources")
                allowed.append("mcp__gapmap__get_resources")
                mcp_servers_dict["gapmap"] = gapmap_server

            options = ClaudeAgentOptions(
                system_prompt=system_prompt or "claude_code",
                allowed_tools=allowed if allowed else None,
                cwd=str(self.mode.working_dir),
                mcp_servers=mcp_servers_dict,
                resume=self.session_id,  # Resume previous session if set
                hooks={
                    "PostToolUse": [
                        HookMatcher(hooks=[tool_logging_hook])
                    ],
                    "Stop": [
                        HookMatcher(hooks=[post_hypergraph_edit_hook])
                    ]
                }
            )

            # Don't try to close existing client - anyio cancel scopes must be exited
            # in the same task they were entered. Just abandon and create fresh.

            self.sdk_client = ClaudeSDKClient(options=options)
            await self.sdk_client.__aenter__()
            self.current_system_prompt = system_prompt

        # Send query and stream responses
        try:
            # Use session_id if set (for resuming conversations)
            query_session_id = self.session_id or "default"
            await self.sdk_client.query(prompt, session_id=query_session_id)

            response_text = []
            # Track tool names by ID for proper matching when multiple tools run in parallel
            tool_id_to_name: Dict[str, str] = {}

            async for message in self.sdk_client.receive_response():
                # Capture session ID from result message (sent at end of response)
                if isinstance(message, ResultMessage):
                    if hasattr(message, 'session_id') and message.session_id:
                        self.session_id = message.session_id
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text.append(block.text)
                            # Log text part for interleaved tracking
                            if self.logger:
                                self.logger.log_text_part(block.text)
                            yield TextEvent(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_id = getattr(block, 'id', None)
                            if tool_id:
                                tool_id_to_name[tool_id] = block.name
                            # Log tool use for interleaved tracking
                            if self.logger:
                                self.logger.log_tool_use(block.name)
                            yield ToolUseEvent(
                                tool_name=block.name,
                                tool_input=block.input if hasattr(block, 'input') else {}
                            )
                        elif isinstance(block, ToolResultBlock):
                            # Tool result - extract content
                            result_text = ""
                            if hasattr(block, 'content'):
                                if isinstance(block.content, str):
                                    result_text = block.content
                                elif isinstance(block.content, list):
                                    result_text = str(block.content)
                            # Look up tool name by tool_use_id
                            tool_use_id = getattr(block, 'tool_use_id', None)
                            tool_name = tool_id_to_name.get(tool_use_id, "unknown") if tool_use_id else "unknown"
                            yield ToolResultEvent(
                                tool_name=tool_name,
                                result=result_text,
                                is_error=getattr(block, 'is_error', False)
                            )

            # Log turn end
            response_content = "".join(response_text)
            if self.logger:
                self.logger.log_turn_end(
                    claude_response=response_content,
                    cost_usd=None,
                    raw_metadata={"messages": response_text}
                )

            yield DoneEvent(full_response=response_content)

        except Exception as e:
            # Log error if logger available
            if self.logger:
                self.logger.log_turn_end(
                    claude_response=f"ERROR: {str(e)}",
                    raw_metadata={"error": str(e)}
                )
            yield ErrorEvent(error=str(e))

    async def query_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[Union[TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent]]:
        """
        Send a query and yield streaming events (async generator).

        This is the main entry point for web streaming.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions

        Yields:
            StreamEvent subclasses
        """
        async for event in self._query_stream_async(prompt, system_prompt):
            yield event

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


    def switch_mode(self, new_mode: ClientMode):
        """
        Switch client to a new mode (e.g., exploration → approach).

        Forces SDK client to recreate with new working directory.

        Args:
            new_mode: New mode configuration
        """
        old_working_dir = self.mode.working_dir if self.mode else None
        self.mode = new_mode

        # Update approach directory for path resolution in tools
        set_approach_dir(new_mode.working_dir)

        # Also update for Edison tools if available
        if EDISON_AVAILABLE:
            global _approach_dir
            _approach_dir = new_mode.working_dir

        # Force SDK client recreation if working directory changed
        # The cwd is set when the SDK client is created, so we must recreate
        if old_working_dir != new_mode.working_dir and self.sdk_client is not None:
            # Don't try to close the old client - anyio cancel scopes must be exited
            # in the same task they were entered. In an async web context, trying to
            # close here creates cross-task issues. Just abandon the old client and
            # let the new one be created fresh on next query.
            self.sdk_client = None
            self.current_system_prompt = None  # Force new system prompt too

    def end_conversation(self):
        """End the current conversation session."""
        # Don't try to close the SDK client - anyio cancel scopes must be exited
        # in the same task they were entered. Just abandon the client.
        self.sdk_client = None
        self.current_system_prompt = None

        # End logging session
        if self.logger:
            self.logger.end_session()

    def start_new_conversation(self):
        """
        Start a completely fresh conversation, clearing all session state.

        This clears:
        - The SDK client (forces recreation)
        - The session_id (prevents resuming old session)
        - The system prompt (forces re-initialization)
        - The logging session

        After calling this, the next query will start with a blank slate.
        """
        # Clear SDK client state
        self.sdk_client = None
        self.session_id = None
        self.current_system_prompt = None

        # End any current logging session
        if self.logger:
            self.logger.end_session()

    def __del__(self):
        """Cleanup when object is destroyed."""
        # Don't try to close SDK client in __del__ - it's unsafe in async contexts
        pass


class ClaudeCodeError(Exception):
    """Exception raised when Claude Code execution fails."""
    pass
