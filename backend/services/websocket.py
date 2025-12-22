"""WebSocket notification helpers."""

import json
from .state import hypergraph_connections, get_orchestrator


async def notify_hypergraph_update(folder: str) -> None:
    """Notify all WebSocket clients that a hypergraph has been updated."""
    print(f"[WS NOTIFY] notify_hypergraph_update called for {folder}", flush=True)
    print(f"[WS NOTIFY] Connected folders: {list(hypergraph_connections.keys())}", flush=True)

    if folder not in hypergraph_connections:
        print(f"[WS NOTIFY] No connections for {folder}, skipping", flush=True)
        return

    orchestrator = get_orchestrator()
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


async def notify_auto_event(folder: str, event: dict) -> None:
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
