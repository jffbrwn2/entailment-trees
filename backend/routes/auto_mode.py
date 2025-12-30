"""Auto mode control endpoints."""

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException

from backend.models import AutoStartRequest, AutoInterjectRequest
from backend.services import (
    get_orchestrator,
    get_auto_agent_client,
    auto_mode_sessions,
    notify_auto_event,
    AutoModeSession,
    run_auto_mode_loop,
)
from agent_system.clients import get_auto_agent_config

router = APIRouter(prefix="/api", tags=["auto_mode"])


@router.get("/auto/config")
async def get_auto_config() -> dict:
    """Get auto mode configuration including provider and available models.

    Returns provider info and model list. If using OpenRouter, fetches models
    dynamically. If using Anthropic fallback, returns static model list.
    """
    config = get_auto_agent_config()

    if config.provider == "openrouter":
        # Fetch models dynamically from OpenRouter
        try:
            client = get_auto_agent_client()
            models = await client.list_models()
        except Exception as e:
            # If OpenRouter fails, return empty list (frontend can handle)
            models = []
    else:
        # Use static Anthropic model list
        models = config.available_models

    return {
        "provider": config.provider,
        "default_model": config.default_model,
        "models": models,
    }


@router.get("/openrouter/models")
async def list_openrouter_models() -> list[dict]:
    """List available models from OpenRouter.

    Deprecated: Use /api/auto/config instead for unified provider support.
    """
    try:
        client = get_auto_agent_client()
        return await client.list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.post("/approaches/{folder}/auto/start")
async def start_auto_mode(folder: str, request: AutoStartRequest) -> dict:
    """Start auto mode for an approach."""
    orchestrator = get_orchestrator()
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


@router.post("/approaches/{folder}/auto/stop")
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


@router.post("/approaches/{folder}/auto/pause")
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


@router.post("/approaches/{folder}/auto/resume")
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


@router.get("/approaches/{folder}/auto/status")
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


@router.post("/approaches/{folder}/auto/interject")
async def auto_mode_interject(folder: str, request: AutoInterjectRequest) -> dict:
    """User interjection during auto mode - handles @mentions.

    target='auto': Add message to history and resume/start auto loop (auto agent responds)
    target='core': Add message to history, keep paused (frontend calls /api/chat)
    target=None: Legacy behavior - pause and let frontend call /api/chat
    """
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    # If no session exists and target is 'auto', create one
    if folder not in auto_mode_sessions:
        if request.target != 'auto':
            raise HTTPException(status_code=404, detail="No auto mode session for this approach")

        # Create a new session (similar to start_auto_mode)
        approach_dir = orchestrator.config.approaches_dir / folder
        if not approach_dir.exists():
            raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

        # Load hypergraph to get hypothesis
        hypergraph_path = approach_dir / "hypergraph.json"
        with open(hypergraph_path) as f:
            hypergraph = json.load(f)

        hypothesis = hypergraph.get("metadata", {}).get("hypothesis", "")
        if not hypothesis:
            claims = hypergraph.get("claims", [])
            root_claims = [c for c in claims if c.get("id") == "root" or c.get("is_root")]
            if root_claims:
                hypothesis = root_claims[0].get("claim", "")

        # Create session with default model
        session = AutoModeSession(
            folder=folder,
            session_id=str(uuid.uuid4()),
            model="google/gemini-2.5-pro-preview",  # Default model
            hypothesis=hypothesis,
            max_turns=orchestrator.config.auto_mode_max_turns,
        )
        auto_mode_sessions[folder] = session

        # Add user message and start the loop
        session.conversation_history.append({"role": "user", "content": request.message})
        session.task = asyncio.create_task(run_auto_mode_loop(folder, session))
        await notify_auto_event(folder, {"type": "auto_status", "status": "started"})

        return {
            "success": True,
            "message": "Auto mode started with message",
            "target": "auto",
            "turn_count": session.turn_count
        }

    session = auto_mode_sessions[folder]

    # Add user message to conversation history
    session.conversation_history.append({"role": "user", "content": request.message})

    if request.target == 'auto':
        # @auto: Resume auto mode loop - auto agent will respond
        if session.paused or not session.active:
            session.paused = False
            session.active = True
            # Restart the loop
            session.task = asyncio.create_task(run_auto_mode_loop(folder, session))
            await notify_auto_event(folder, {"type": "auto_status", "status": "resumed"})
        # If not paused and active, loop is already running and will pick up the message

        return {
            "success": True,
            "message": "Message added, auto mode resumed",
            "target": "auto",
            "turn_count": session.turn_count
        }

    else:
        # @core or legacy: Pause auto mode, frontend handles Claude response
        session.paused = True
        await notify_auto_event(folder, {"type": "auto_status", "status": "paused"})

        return {
            "success": True,
            "message": "Auto mode paused for interjection",
            "target": request.target or "core",
            "turn_count": session.turn_count
        }
