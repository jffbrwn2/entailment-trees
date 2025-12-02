"""
FastAPI backend for Entailment Trees Web Application.

Wraps the existing agent_system to expose HTTP/SSE/WebSocket endpoints.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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


# Global orchestrator instance (one per server for now)
orchestrator: Optional[AgentOrchestrator] = None

# WebSocket connections for hypergraph updates
hypergraph_connections: dict[str, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator on startup."""
    global orchestrator
    orchestrator = AgentOrchestrator(AgentConfig.from_env())
    yield
    # Cleanup on shutdown
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


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "orchestrator_ready": orchestrator is not None}


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
            # Convert infinity to None (JSON doesn't support Infinity)
            if math.isinf(value):
                claim['propagated_negative_log'] = None
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

    # Clear the session_id to start fresh conversation
    if orchestrator.claude_client:
        orchestrator.claude_client.session_id = None
        # End current logging session and start new one
        if orchestrator.claude_client.logger:
            orchestrator.claude_client.logger.end_session()
            # Get approach name for new session
            hypergraph_path = approach_dir / "hypergraph.json"
            approach_name = folder
            if hypergraph_path.exists():
                import json
                with open(hypergraph_path) as f:
                    data = json.load(f)
                    approach_name = data.get("metadata", {}).get("name", folder)
            orchestrator.claude_client.logger.start_session(approach_name)

    return {"success": True, "message": "New session started"}


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

                    # Save session_id for future resumption
                    if orchestrator.current_session and orchestrator.claude_client.session_id:
                        from agent_system.agent_orchestrator import _save_session_id
                        _save_session_id(
                            orchestrator.current_session.approach_dir,
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
    if folder not in hypergraph_connections:
        return

    if not orchestrator:
        return

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


# Mount static files for visualization
# These must be mounted AFTER all API routes
PROJECT_ROOT = Path(__file__).parent.parent
app.mount("/entailment_hypergraph", StaticFiles(directory=PROJECT_ROOT / "entailment_hypergraph", html=True), name="entailment_hypergraph")
app.mount("/approaches", StaticFiles(directory=PROJECT_ROOT / "approaches"), name="approaches")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
