"""
FastAPI backend for Entailment Trees Web Application.

Wraps the existing agent_system to expose HTTP/SSE/WebSocket endpoints.
"""

import asyncio
import json
import sys
import threading
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add parent directory to path so we can import agent_system
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_system import (
    AgentOrchestrator,
    HypergraphManager,
    TextEvent,
    ToolUseEvent,
    ToolResultEvent,
    ErrorEvent,
    DoneEvent,
)
from agent_system.config import AgentConfig
from agent_system.conversation_logger import list_conversation_logs, load_conversation_log
from agent_system.openrouter_client import OpenRouterClient
from agent_system.runtime_settings import get_settings, update_settings


# Global orchestrator instance (one per server for now)
orchestrator: Optional[AgentOrchestrator] = None

# WebSocket connections for hypergraph updates
hypergraph_connections: dict[str, list[WebSocket]] = {}

# File watcher for hypergraph changes
file_observer: Optional[Observer] = None
# Event loop reference for async calls from file watcher thread
main_event_loop: Optional[asyncio.AbstractEventLoop] = None

# Auto mode state tracking
from dataclasses import dataclass, field
from typing import Dict, List
import uuid


@dataclass
class AutoModeSession:
    """Tracks state for an auto mode session."""
    folder: str
    session_id: str
    model: str
    active: bool = True
    paused: bool = False
    turn_count: int = 0
    max_turns: int = 20
    hypothesis: str = ""
    conversation_history: List[dict] = field(default_factory=list)
    task: Optional[asyncio.Task] = None


# Active auto mode sessions by folder
auto_mode_sessions: Dict[str, AutoModeSession] = {}

# OpenRouter client instance (initialized lazily)
openrouter_client: Optional[OpenRouterClient] = None


AUTO_AGENT_SYSTEM_PROMPT = """You are an Auto Agent rigorously evaluating a hypothesis through an entailment tree.

Your role: Act as a knowledgeable user who systematically:
1. Identifies claims needing evidence or scoring
2. Requests simulations and literature searches
3. Points out logical gaps
4. Brainstorms alternatives when hitting blockers

Current hypothesis: {hypothesis}

Current entailment tree (full hypergraph.json):
{hypergraph}

Guidelines:
- Work through claims systematically, one at a time
- Prioritize high-impact claims
- Give Claude clear, specific instructions
- When blocked, suggest OR pathways (alternatives)
- Stop when hypothesis is clearly supported or refuted

Generate your next message to Claude:"""


class HypergraphFileHandler(FileSystemEventHandler):
    """Watch for changes to hypergraph.json files and notify WebSocket clients."""

    def __init__(self, approaches_dir: Path):
        self.approaches_dir = approaches_dir
        self._last_modified: dict[str, float] = {}  # Debounce rapid changes

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only care about hypergraph.json files
        path = Path(event.src_path)
        if path.name != "hypergraph.json":
            return

        # Extract folder name from path
        try:
            folder = path.parent.name
        except Exception:
            return

        # Debounce: ignore if modified within last 0.5 seconds
        import time
        now = time.time()
        last = self._last_modified.get(folder, 0)
        if now - last < 0.5:
            return
        self._last_modified[folder] = now

        print(f"[FILE WATCHER] Detected change in {folder}/hypergraph.json", flush=True)

        # Schedule the async notification on the main event loop
        if main_event_loop and not main_event_loop.is_closed():
            print(f"[FILE WATCHER] Scheduling WebSocket notification for {folder}", flush=True)
            asyncio.run_coroutine_threadsafe(
                notify_hypergraph_update(folder),
                main_event_loop
            )
        else:
            print(f"[FILE WATCHER] Event loop not available for {folder}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator and file watcher on startup."""
    global orchestrator, file_observer, main_event_loop

    # Store reference to main event loop for file watcher callbacks
    main_event_loop = asyncio.get_running_loop()

    orchestrator = AgentOrchestrator(AgentConfig.from_env())

    # Start file watcher for hypergraph changes
    approaches_dir = orchestrator.config.approaches_dir.resolve()  # Use absolute path
    print(f"[FILE WATCHER] approaches_dir={approaches_dir}, exists={approaches_dir.exists()}", flush=True)
    if approaches_dir.exists():
        file_observer = Observer()
        handler = HypergraphFileHandler(approaches_dir)
        file_observer.schedule(handler, str(approaches_dir), recursive=True)
        file_observer.start()
        print(f"[FILE WATCHER] Watching {approaches_dir} for hypergraph changes", flush=True)
    else:
        print(f"[FILE WATCHER] approaches_dir does NOT exist, skipping watcher", flush=True)

    yield

    # Cleanup on shutdown
    if file_observer:
        file_observer.stop()
        file_observer.join()
        print("[FILE WATCHER] Stopped")

    if orchestrator and orchestrator.claude_client:
        orchestrator.claude_client.end_conversation()


app = FastAPI(
    title="Entailment Trees API",
    description="API for idea refinement agent with entailment hypergraphs",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class CreateApproachRequest(BaseModel):
    name: str
    hypothesis: str
    description: Optional[str] = ""


class ChatRequest(BaseModel):
    message: str
    approach_name: Optional[str] = None


class ApproachInfo(BaseModel):
    name: str
    folder: str
    description: str
    last_updated: str
    num_claims: int
    num_implications: int


class GenerateNameRequest(BaseModel):
    hypothesis: str


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "orchestrator_ready": orchestrator is not None}


# Generate approach name using Haiku
@app.post("/api/generate-name")
async def generate_name(request: GenerateNameRequest) -> dict:
    """Generate a short name for an approach using Claude Haiku."""
    import anthropic
    import re

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"Generate a short (2-4 word) name for this research idea. Return ONLY the name, nothing else. Use lowercase with hyphens between words.\n\nIdea: {request.hypothesis}"
            }]
        )
        name = response.content[0].text.strip()
        # Sanitize: lowercase, replace spaces/special chars with hyphens
        name = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:50]
        return {"name": name}
    except Exception as e:
        # Fallback to simple slug
        name = re.sub(r'[^a-z0-9]+', '-', request.hypothesis.lower())[:30].strip('-')
        return {"name": name, "error": str(e)}


# Approaches endpoints
@app.get("/api/approaches")
async def list_approaches() -> list[ApproachInfo]:
    """List all existing approaches."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approaches_dir = orchestrator.config.approaches_dir
    if not approaches_dir.exists():
        return []

    approaches = []
    for approach_dir in approaches_dir.iterdir():
        if not approach_dir.is_dir():
            continue

        hypergraph_file = approach_dir / "hypergraph.json"
        if hypergraph_file.exists():
            try:
                with open(hypergraph_file) as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    approaches.append(ApproachInfo(
                        name=metadata.get("name", approach_dir.name),
                        folder=approach_dir.name,
                        description=metadata.get("description", ""),
                        last_updated=metadata.get("last_updated", ""),
                        num_claims=len(data.get("claims", [])),
                        num_implications=len(data.get("implications", [])),
                    ))
            except Exception:
                continue

    return sorted(approaches, key=lambda a: a.last_updated, reverse=True)


@app.post("/api/approaches")
async def create_approach(request: CreateApproachRequest) -> dict:
    """Create a new approach."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = orchestrator.start_approach(
            name=request.name,
            initial_claim=request.hypothesis,
            description=request.description or ""
        )
        return {
            "success": True,
            "name": result["session"]["name"],
            "folder": result["session"]["folder"],
            "path": result["session"]["path"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/approaches/{folder}/load")
async def load_approach(folder: str) -> dict:
    """Load an existing approach."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    try:
        result = orchestrator.load_approach(approach_dir)
        return {
            "success": True,
            "name": result["session"]["name"],
            "folder": result["session"]["folder"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/approaches/{folder}/hypergraph")
async def get_hypergraph(folder: str) -> dict:
    """Get the hypergraph JSON for an approach with computed propagated scores."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
    if not hypergraph_path.exists():
        raise HTTPException(status_code=404, detail=f"Hypergraph not found for '{folder}'")

    with open(hypergraph_path) as f:
        hypergraph = json.load(f)

    # Always compute propagated negative logs before serving
    from agent_system.hypergraph_manager import HypergraphManager
    import math
    mgr = HypergraphManager(orchestrator.config.approaches_dir / folder)
    propagated_logs = mgr.calculate_propagated_negative_logs(hypergraph)
    for claim in hypergraph.get('claims', []):
        claim_id = claim['id']
        if claim_id in propagated_logs:
            value = propagated_logs[claim_id]
            # Store Infinity as string for valid JSON
            if value == float('inf'):
                claim['propagated_negative_log'] = "Infinity"
            elif value == float('-inf'):
                claim['propagated_negative_log'] = "-Infinity"
            else:
                claim['propagated_negative_log'] = value

    return hypergraph


@app.get("/api/approaches/{folder}/status")
async def get_approach_status(folder: str) -> dict:
    """Get status and stats for an approach."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        stats = mgr.get_stats()
        return {
            "folder": folder,
            "stats": stats,
            "is_active": (
                orchestrator.current_session is not None and
                str(orchestrator.current_session.approach_dir) == str(approach_dir)
            )
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/approaches/{folder}/cleanup")
async def cleanup_hypergraph(folder: str) -> dict:
    """Remove unreachable nodes from the hypergraph."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        removed = mgr.remove_unreachable_nodes()
        # Notify WebSocket clients of the update
        await notify_hypergraph_update(folder)
        return {
            "success": True,
            "removed_count": len(removed),
            "removed_nodes": removed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/approaches/{folder}/claims/{claim_id}")
async def delete_claim(folder: str, claim_id: str) -> dict:
    """Delete a claim and its related implications."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        result = mgr.delete_claim(claim_id)
        # Notify WebSocket clients of the update
        await notify_hypergraph_update(folder)
        return {
            "success": True,
            "deleted_claim_id": claim_id,
            "deleted_implications_count": len(result['deleted_implications']),
            "validation": result.get('validation', {})
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Conversation history endpoints
@app.get("/api/approaches/{folder}/conversations")
async def list_conversations(folder: str) -> list[dict]:
    """List all conversation logs for an approach."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # Get the approach name from hypergraph metadata
    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    # Load hypergraph to get approach name
    hypergraph_path = approach_dir / "hypergraph.json"
    approach_name = folder
    if hypergraph_path.exists():
        with open(hypergraph_path) as f:
            data = json.load(f)
            approach_name = data.get("metadata", {}).get("name", folder)

    # List conversations for this approach
    logs_dir = orchestrator.config.logs_dir
    log_files = list_conversation_logs(logs_dir, approach_name=approach_name)

    conversations = []
    for log_file in log_files:
        try:
            log = load_conversation_log(log_file)
            conversations.append({
                "session_id": log.session_id,
                "started_at": log.started_at,
                "ended_at": log.ended_at,
                "num_turns": len(log.turns),
                "filename": log_file.name,
            })
        except Exception:
            continue

    return conversations


@app.get("/api/conversations/{filename}")
async def get_conversation(filename: str) -> dict:
    """Load a specific conversation log."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    log_file = orchestrator.config.logs_dir / filename
    if not log_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation log not found: {filename}")

    try:
        log = load_conversation_log(log_file)
        return {
            "session_id": log.session_id,
            "approach_name": log.approach_name,
            "started_at": log.started_at,
            "ended_at": log.ended_at,
            "turns": [
                {
                    "turn_number": turn.turn_number,
                    "user_input": turn.user_input,
                    "claude_response": turn.claude_response,
                    "timestamp": turn.timestamp,
                    "tools_used": [
                        {"tool_name": tool.tool_name, "result": tool.result}
                        for tool in turn.tools_used
                    ]
                }
                for turn in log.turns
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/approaches/{folder}/new-session")
async def new_session(folder: str) -> dict:
    """Start a new chat session for an approach (clears conversation state)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    # Clear all session state to start fresh conversation
    if orchestrator.claude_client:
        # This clears: sdk_client, session_id, system_prompt, and ends logging
        orchestrator.claude_client.start_new_conversation()

        # Clear session.json so load_approach won't resume the old session
        # This is necessary because load_approach reads from this file
        session_file = approach_dir / "session.json"
        if session_file.exists():
            session_file.unlink()
            print(f"[SESSION] Cleared session file for fresh start")

        print(f"[SESSION] Started fresh conversation for {folder}")

    return {"success": True, "message": "New session started"}


class ResumeSessionRequest(BaseModel):
    """Request to resume a specific conversation."""
    conversation_filename: str


@app.post("/api/approaches/{folder}/resume-session")
async def resume_session(folder: str, request: ResumeSessionRequest) -> dict:
    """Resume a specific conversation's session (when switching to old conversation)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    # Load the conversation log to get its SDK session ID
    log_data = load_conversation_log(request.conversation_filename)
    if not log_data:
        print(f"[SESSION] Could not load conversation: {request.conversation_filename}")
        return {"success": False, "message": "Could not load conversation"}

    sdk_session_id = log_data.get("claude_sdk_session_id")

    if orchestrator.claude_client and sdk_session_id:
        orchestrator.claude_client.session_id = sdk_session_id
        # Force SDK client recreation to use the resumed session
        orchestrator.claude_client.sdk_client = None
        orchestrator.claude_client.current_system_prompt = None
        print(f"[SESSION] Resumed conversation {request.conversation_filename}")
        print(f"[SESSION] SDK session: {sdk_session_id[:40]}...")
        return {"success": True, "message": "Session resumed", "session_id": sdk_session_id}
    else:
        print(f"[SESSION] No SDK session ID in conversation: {request.conversation_filename}")
        # Clear state for fresh start (old conversation didn't have SDK session)
        if orchestrator.claude_client:
            orchestrator.claude_client.start_new_conversation()
        return {"success": False, "message": "No SDK session ID found in conversation"}


# Chat endpoint with SSE streaming
@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """
    Send a message and stream the response via SSE.

    Returns Server-Sent Events with JSON payloads:
    - {"type": "text", "text": "..."}
    - {"type": "tool_use", "tool_name": "...", "tool_input": {...}}
    - {"type": "tool_result", "tool_name": "...", "result": "..."}
    - {"type": "error", "error": "..."}
    - {"type": "done", "full_response": "..."}
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # If approach specified, load it first
    if request.approach_name:
        approach_dir = orchestrator.config.approaches_dir / request.approach_name
        if approach_dir.exists() and (
            orchestrator.current_session is None or
            str(orchestrator.current_session.approach_dir) != str(approach_dir)
        ):
            orchestrator.load_approach(approach_dir)

    # Capture hypergraph state before processing to detect changes
    hypergraph_before = None
    if orchestrator.current_session:
        hypergraph_path = orchestrator.current_session.approach_dir / "hypergraph.json"
        if hypergraph_path.exists():
            try:
                hypergraph_before = hypergraph_path.read_text()
            except Exception:
                pass

    async def generate():
        nonlocal hypergraph_before
        try:
            # Get system prompt based on current mode
            system_prompt = None
            if orchestrator.current_session:
                system_prompt = orchestrator.get_system_prompt()

            # Stream events from Claude
            async for event in orchestrator.claude_client.query_stream(
                request.message,
                system_prompt=system_prompt
            ):
                if isinstance(event, TextEvent):
                    yield f"data: {json.dumps({'type': 'text', 'text': event.text})}\n\n"
                elif isinstance(event, ToolUseEvent):
                    yield f"data: {json.dumps({'type': 'tool_use', 'tool_name': event.tool_name, 'tool_input': event.tool_input})}\n\n"
                elif isinstance(event, ToolResultEvent):
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': event.tool_name, 'result': event.result, 'is_error': event.is_error})}\n\n"
                elif isinstance(event, ErrorEvent):
                    yield f"data: {json.dumps({'type': 'error', 'error': event.error})}\n\n"
                elif isinstance(event, DoneEvent):
                    yield f"data: {json.dumps({'type': 'done', 'full_response': event.full_response})}\n\n"

                    # Only notify WebSocket clients if hypergraph actually changed
                    if orchestrator.current_session:
                        folder = orchestrator.current_session.approach_dir.name
                        hypergraph_path = orchestrator.current_session.approach_dir / "hypergraph.json"
                        hypergraph_after = None
                        if hypergraph_path.exists():
                            try:
                                hypergraph_after = hypergraph_path.read_text()
                            except Exception:
                                pass

                        # Only send update if content changed
                        if hypergraph_after != hypergraph_before:
                            await notify_hypergraph_update(folder)

                    # Save session_id to conversation log for per-conversation resumption
                    if orchestrator.claude_client.session_id and orchestrator.claude_client.logger:
                        orchestrator.claude_client.logger.set_sdk_session_id(
                            orchestrator.claude_client.session_id
                        )

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# WebSocket for live hypergraph updates
@app.websocket("/ws/hypergraph/{folder}")
async def hypergraph_websocket(websocket: WebSocket, folder: str):
    """WebSocket for live hypergraph updates."""
    await websocket.accept()

    # Add to connections for this folder
    if folder not in hypergraph_connections:
        hypergraph_connections[folder] = []
    hypergraph_connections[folder].append(websocket)

    try:
        # Send initial hypergraph state
        if orchestrator:
            hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
            if hypergraph_path.exists():
                with open(hypergraph_path) as f:
                    data = json.load(f)
                await websocket.send_json({"type": "initial", "hypergraph": data})

        # Keep connection alive and handle any incoming messages
        while True:
            try:
                # Wait for messages (mainly for keepalive pings)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send ping to check connection
                await websocket.send_text("ping")

    except WebSocketDisconnect:
        pass
    finally:
        # Remove from connections
        if folder in hypergraph_connections:
            hypergraph_connections[folder].remove(websocket)


async def notify_hypergraph_update(folder: str):
    """Notify all WebSocket clients that a hypergraph has been updated."""
    print(f"[WS NOTIFY] notify_hypergraph_update called for {folder}", flush=True)
    print(f"[WS NOTIFY] Connected folders: {list(hypergraph_connections.keys())}", flush=True)

    if folder not in hypergraph_connections:
        print(f"[WS NOTIFY] No connections for {folder}, skipping", flush=True)
        return

    if not orchestrator:
        print(f"[WS NOTIFY] No orchestrator, skipping", flush=True)
        return

    print(f"[WS NOTIFY] {len(hypergraph_connections[folder])} clients connected for {folder}", flush=True)

    hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
    if not hypergraph_path.exists():
        return

    with open(hypergraph_path) as f:
        data = json.load(f)

    # Send to all connected clients
    disconnected = []
    for websocket in hypergraph_connections[folder]:
        try:
            await websocket.send_json({"type": "update", "hypergraph": data})
        except Exception:
            disconnected.append(websocket)

    # Clean up disconnected clients
    for ws in disconnected:
        hypergraph_connections[folder].remove(ws)


# =============================================================================
# AUTO MODE ENDPOINTS
# =============================================================================

class AutoStartRequest(BaseModel):
    """Request to start auto mode."""
    model: str = "anthropic/claude-3-haiku"


class AutoInterjectRequest(BaseModel):
    """Request for user to interject during auto mode."""
    message: str


def get_openrouter_client() -> OpenRouterClient:
    """Get or create the OpenRouter client."""
    global openrouter_client
    if openrouter_client is None:
        openrouter_client = OpenRouterClient()
    return openrouter_client


async def get_auto_agent_response(
    client: OpenRouterClient,
    model: str,
    hypothesis: str,
    hypergraph: dict,
    conversation_history: list[dict]
) -> str:
    """Get next message from the Auto agent via OpenRouter."""
    system_prompt = AUTO_AGENT_SYSTEM_PROMPT.format(
        hypothesis=hypothesis,
        hypergraph=json.dumps(hypergraph, indent=2)
    )

    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    return await client.chat(messages, model)


async def run_auto_mode_loop(folder: str, session: AutoModeSession):
    """Background task that runs the auto mode loop."""
    print(f"[AUTO MODE] Starting loop for {folder}", flush=True)

    while session.active and not session.paused and session.turn_count < session.max_turns:
        try:
            # Load current hypergraph state
            hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
            if not hypergraph_path.exists():
                print(f"[AUTO MODE] Hypergraph not found for {folder}", flush=True)
                break

            with open(hypergraph_path) as f:
                hypergraph = json.load(f)

            # Get Auto agent's next message
            print(f"[AUTO MODE] Turn {session.turn_count + 1}: Getting Auto agent response", flush=True)
            client = get_openrouter_client()
            auto_message = await get_auto_agent_response(
                client,
                session.model,
                session.hypothesis,
                hypergraph,
                session.conversation_history
            )

            print(f"[AUTO MODE] Auto agent says: {auto_message[:100]}...", flush=True)

            # Add Auto agent message to history
            session.conversation_history.append({"role": "assistant", "content": auto_message})

            # Notify WebSocket clients of the auto message
            await notify_auto_event(folder, {
                "type": "auto_message",
                "text": auto_message,
                "source": "auto"
            })

            # Check for stop signals before sending to Claude
            if not session.active or session.paused:
                break

            # Send to Claude via the existing chat endpoint logic
            # We need to capture Claude's response to add to history
            claude_response = ""
            approach_dir = orchestrator.config.approaches_dir / folder

            # Load approach if not already loaded
            if (orchestrator.current_session is None or
                str(orchestrator.current_session.approach_dir) != str(approach_dir)):
                orchestrator.load_approach(approach_dir)

            system_prompt = orchestrator.get_system_prompt()

            async for event in orchestrator.claude_client.query_stream(
                auto_message,
                system_prompt=system_prompt
            ):
                if isinstance(event, TextEvent):
                    claude_response += event.text
                    await notify_auto_event(folder, {"type": "text", "text": event.text})
                elif isinstance(event, ToolUseEvent):
                    await notify_auto_event(folder, {
                        "type": "tool_use",
                        "tool_name": event.tool_name,
                        "tool_input": event.tool_input
                    })
                elif isinstance(event, ToolResultEvent):
                    await notify_auto_event(folder, {
                        "type": "tool_result",
                        "tool_name": event.tool_name,
                        "result": event.result,
                        "is_error": event.is_error
                    })
                elif isinstance(event, ErrorEvent):
                    await notify_auto_event(folder, {"type": "error", "error": event.error})
                elif isinstance(event, DoneEvent):
                    await notify_auto_event(folder, {
                        "type": "done",
                        "full_response": event.full_response
                    })

            # Add Claude's response to history (for Auto agent's context)
            session.conversation_history.append({"role": "user", "content": claude_response})

            session.turn_count += 1
            await notify_auto_event(folder, {
                "type": "auto_turn",
                "turn_number": session.turn_count,
                "max_turns": session.max_turns
            })

            # Brief delay before next turn
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[AUTO MODE] Error in loop: {e}", flush=True)
            await notify_auto_event(folder, {"type": "error", "error": str(e)})
            break

    # Clean up
    session.active = False
    await notify_auto_event(folder, {"type": "auto_status", "status": "stopped"})
    print(f"[AUTO MODE] Loop ended for {folder} after {session.turn_count} turns", flush=True)


async def notify_auto_event(folder: str, event: dict):
    """Send an auto mode event to WebSocket clients."""
    if folder not in hypergraph_connections:
        return

    disconnected = []
    for websocket in hypergraph_connections[folder]:
        try:
            await websocket.send_json(event)
        except Exception:
            disconnected.append(websocket)

    for ws in disconnected:
        hypergraph_connections[folder].remove(ws)


@app.get("/api/openrouter/models")
async def list_openrouter_models() -> list[dict]:
    """List available models from OpenRouter."""
    try:
        client = get_openrouter_client()
        models = await client.list_models()
        # Return simplified model info
        return [
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "pricing": m.get("pricing", {}),
                "context_length": m.get("context_length"),
            }
            for m in models
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@app.get("/api/config/status")
async def get_config_status() -> dict:
    """Check if required API keys are configured."""
    import os
    return {
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openrouter_key_set": bool(os.getenv("OPENROUTER_API_KEY")),
    }


# =============================================================================
# RUNTIME SETTINGS ENDPOINTS
# =============================================================================

class UpdateSettingsRequest(BaseModel):
    """Request to update runtime settings."""
    chatModel: Optional[str] = None
    evaluatorModel: Optional[str] = None
    autoModel: Optional[str] = None
    edisonToolsEnabled: Optional[bool] = None
    gapMapToolsEnabled: Optional[bool] = None


@app.get("/api/settings")
async def get_runtime_settings() -> dict:
    """Get current runtime settings."""
    settings = get_settings()
    return settings.to_dict()


@app.put("/api/settings")
async def update_runtime_settings(request: UpdateSettingsRequest) -> dict:
    """Update runtime settings."""
    # Convert request to dict, filtering out None values
    data = {k: v for k, v in request.model_dump().items() if v is not None}
    settings = update_settings(data)
    return settings.to_dict()


@app.post("/api/approaches/{folder}/auto/start")
async def start_auto_mode(folder: str, request: AutoStartRequest) -> dict:
    """Start auto mode for an approach."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    # Check if already running
    if folder in auto_mode_sessions and auto_mode_sessions[folder].active:
        raise HTTPException(status_code=400, detail="Auto mode already running for this approach")

    # Load hypergraph to get hypothesis
    hypergraph_path = approach_dir / "hypergraph.json"
    with open(hypergraph_path) as f:
        hypergraph = json.load(f)

    hypothesis = hypergraph.get("metadata", {}).get("hypothesis", "")
    if not hypothesis:
        # Try to get from root claim
        claims = hypergraph.get("claims", [])
        root_claims = [c for c in claims if c.get("id") == "root" or c.get("is_root")]
        if root_claims:
            hypothesis = root_claims[0].get("claim", "")

    # Create session
    session = AutoModeSession(
        folder=folder,
        session_id=str(uuid.uuid4()),
        model=request.model,
        hypothesis=hypothesis,
        max_turns=orchestrator.config.auto_mode_max_turns,
    )
    auto_mode_sessions[folder] = session

    # Start background task
    session.task = asyncio.create_task(run_auto_mode_loop(folder, session))

    await notify_auto_event(folder, {"type": "auto_status", "status": "started"})

    return {
        "success": True,
        "session_id": session.session_id,
        "model": session.model,
        "max_turns": session.max_turns,
    }


@app.post("/api/approaches/{folder}/auto/stop")
async def stop_auto_mode(folder: str) -> dict:
    """Stop auto mode for an approach."""
    if folder not in auto_mode_sessions:
        raise HTTPException(status_code=404, detail="No auto mode session for this approach")

    session = auto_mode_sessions[folder]
    session.active = False
    session.paused = False

    # Cancel the task if running
    if session.task and not session.task.done():
        session.task.cancel()

    await notify_auto_event(folder, {"type": "auto_status", "status": "stopped"})

    return {"success": True, "turns_completed": session.turn_count}


@app.post("/api/approaches/{folder}/auto/pause")
async def pause_auto_mode(folder: str) -> dict:
    """Pause auto mode for an approach."""
    if folder not in auto_mode_sessions:
        raise HTTPException(status_code=404, detail="No auto mode session for this approach")

    session = auto_mode_sessions[folder]
    if not session.active:
        raise HTTPException(status_code=400, detail="Auto mode not active")

    session.paused = True
    await notify_auto_event(folder, {"type": "auto_status", "status": "paused"})

    return {"success": True, "turn_count": session.turn_count}


@app.post("/api/approaches/{folder}/auto/resume")
async def resume_auto_mode(folder: str) -> dict:
    """Resume paused auto mode for an approach."""
    if folder not in auto_mode_sessions:
        raise HTTPException(status_code=404, detail="No auto mode session for this approach")

    session = auto_mode_sessions[folder]
    if not session.paused:
        raise HTTPException(status_code=400, detail="Auto mode not paused")

    session.paused = False
    session.active = True

    # Restart the loop
    session.task = asyncio.create_task(run_auto_mode_loop(folder, session))

    await notify_auto_event(folder, {"type": "auto_status", "status": "resumed"})

    return {"success": True, "turn_count": session.turn_count}


@app.get("/api/approaches/{folder}/auto/status")
async def get_auto_mode_status(folder: str) -> dict:
    """Get auto mode status for an approach."""
    if folder not in auto_mode_sessions:
        return {
            "active": False,
            "paused": False,
            "turn_count": 0,
            "session_id": None,
        }

    session = auto_mode_sessions[folder]
    return {
        "active": session.active,
        "paused": session.paused,
        "turn_count": session.turn_count,
        "max_turns": session.max_turns,
        "session_id": session.session_id,
        "model": session.model,
    }


@app.post("/api/approaches/{folder}/auto/interject")
async def auto_mode_interject(folder: str, request: AutoInterjectRequest) -> dict:
    """User interjection during auto mode - pauses auto and sends user message."""
    if folder not in auto_mode_sessions:
        raise HTTPException(status_code=404, detail="No auto mode session for this approach")

    session = auto_mode_sessions[folder]

    # Pause auto mode
    session.paused = True
    await notify_auto_event(folder, {"type": "auto_status", "status": "paused"})

    # Add user message to history
    session.conversation_history.append({"role": "user", "content": request.message})

    # The message will be sent via the normal chat endpoint
    # Frontend should call /api/chat after this

    return {
        "success": True,
        "message": "Auto mode paused for interjection",
        "turn_count": session.turn_count
    }


# =============================================================================
# STATIC FILES
# =============================================================================

# Mount static files for visualization
# These must be mounted AFTER all API routes
PROJECT_ROOT = Path(__file__).parent.parent
app.mount("/entailment_hypergraph", StaticFiles(directory=PROJECT_ROOT / "entailment_hypergraph", html=True), name="entailment_hypergraph")
app.mount("/approaches", StaticFiles(directory=PROJECT_ROOT / "approaches"), name="approaches")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
