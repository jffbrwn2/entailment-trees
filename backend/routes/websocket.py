"""WebSocket endpoints."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services import get_orchestrator, hypergraph_connections

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/hypergraph/{folder}")
async def hypergraph_websocket(websocket: WebSocket, folder: str):
    """WebSocket for live hypergraph updates."""
    await websocket.accept()

    # Add to connections for this folder
    if folder not in hypergraph_connections:
        hypergraph_connections[folder] = []
    hypergraph_connections[folder].append(websocket)

    try:
        # Send initial hypergraph state
        orchestrator = get_orchestrator()
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
