"""Chat SSE streaming endpoint."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent_system import TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent

from backend.models import ChatRequest
from backend.services import get_orchestrator, notify_hypergraph_update, auto_mode_sessions

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
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
    orchestrator = get_orchestrator()
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

                        # Sync Claude's response to auto mode conversation history
                        # This ensures the auto agent has context when it resumes
                        if folder in auto_mode_sessions:
                            session = auto_mode_sessions[folder]
                            if session.active or session.paused:
                                # Add Claude's response as "user" from auto agent's perspective
                                session.conversation_history.append({
                                    "role": "user",
                                    "content": event.full_response
                                })

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
