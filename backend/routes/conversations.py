"""Conversation history endpoints."""

import json

from fastapi import APIRouter, HTTPException

from agent_system.conversation_logger import list_conversation_logs, load_conversation_log

from backend.models import ResumeSessionRequest
from backend.services import get_orchestrator

router = APIRouter(prefix="/api", tags=["conversations"])


@router.get("/approaches/{folder}/conversations")
async def list_conversations(folder: str) -> list[dict]:
    """List all conversation logs for an approach."""
    orchestrator = get_orchestrator()
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


@router.get("/conversations/{filename}")
async def get_conversation(filename: str) -> dict:
    """Load a specific conversation log."""
    orchestrator = get_orchestrator()
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


@router.post("/approaches/{folder}/new-session")
async def new_session(folder: str) -> dict:
    """Start a new chat session for an approach (clears conversation state)."""
    orchestrator = get_orchestrator()
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


@router.post("/approaches/{folder}/resume-session")
async def resume_session(folder: str, request: ResumeSessionRequest) -> dict:
    """Resume a specific conversation's session (when switching to old conversation)."""
    orchestrator = get_orchestrator()
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
