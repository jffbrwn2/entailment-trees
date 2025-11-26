#!/usr/bin/env python
"""
Real-time Hypergraph Visualization Server

WebSocket server that watches for changes to hypergraph.json files
and pushes updates to connected clients in real-time.

Usage:
    python hypergraph_server.py [--port 8765]
"""

import asyncio
import json
import argparse
from pathlib import Path
from typing import Set, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class HypergraphWatcher(FileSystemEventHandler):
    """Watches filesystem for hypergraph.json changes and notifies WebSocket clients."""

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.hypergraph_cache: Dict[str, Dict[str, Any]] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations."""
        self.loop = loop

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only care about hypergraph.json files
        if file_path.name != "hypergraph.json":
            return

        print(f"[WATCHER] Detected change in {file_path}")

        # Load the updated hypergraph
        try:
            with open(file_path, 'r') as f:
                new_data = json.load(f)

            # Calculate update message
            update_msg = self._create_update_message(file_path, new_data)

            # Notify all connected clients
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_clients(update_msg),
                    self.loop
                )
        except Exception as e:
            print(f"[WATCHER] Error processing change: {e}")

    def _create_update_message(self, file_path: Path, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create update message with diff information."""
        path_str = str(file_path)
        old_data = self.hypergraph_cache.get(path_str)

        # Store new data in cache
        self.hypergraph_cache[path_str] = new_data

        # For now, send full update (we'll add diffing later)
        return {
            "type": "hypergraph_update",
            "path": path_str,
            "timestamp": datetime.now().isoformat(),
            "data": new_data,
            "is_incremental": False
        }

    async def _notify_clients(self, message: Dict[str, Any]):
        """Send update to all connected clients."""
        if not self.clients:
            return

        disconnected = set()
        for client in self.clients:
            try:
                await client.send_json(message)
                print(f"[WEBSOCKET] Sent update to client")
            except Exception as e:
                print(f"[WEBSOCKET] Client disconnected: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def add_client(self, websocket: WebSocket):
        """Register a new WebSocket client."""
        self.clients.add(websocket)
        print(f"[WEBSOCKET] Client connected. Total clients: {len(self.clients)}")

    async def remove_client(self, websocket: WebSocket):
        """Unregister a WebSocket client."""
        self.clients.discard(websocket)
        print(f"[WEBSOCKET] Client disconnected. Total clients: {len(self.clients)}")


# Global watcher instance
watcher = HypergraphWatcher()

# Create FastAPI app
app = FastAPI(title="Hypergraph Visualization Server")


@app.on_event("startup")
async def startup_event():
    """Start filesystem watcher on startup."""
    # Set event loop for watcher
    watcher.set_event_loop(asyncio.get_event_loop())

    # Start watching filesystem
    observer = Observer()

    # Watch approaches directory
    approaches_dir = Path("approaches")
    if approaches_dir.exists():
        observer.schedule(watcher, str(approaches_dir), recursive=True)
        print(f"[SERVER] Watching {approaches_dir.absolute()} for changes")

    # Watch examples directory
    examples_dir = Path("entailment_hypergraph")
    if examples_dir.exists():
        observer.schedule(watcher, str(examples_dir), recursive=True)
        print(f"[SERVER] Watching {examples_dir.absolute()} for changes")

    observer.start()

    # Store observer in app state so we can stop it later
    app.state.observer = observer

    print("[SERVER] ✓ Filesystem watcher started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop filesystem watcher on shutdown."""
    if hasattr(app.state, 'observer'):
        app.state.observer.stop()
        app.state.observer.join()
        print("[SERVER] Filesystem watcher stopped")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    await watcher.add_client(websocket)

    try:
        # Keep connection alive and handle pings
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await watcher.remove_client(websocket)
    except Exception as e:
        print(f"[WEBSOCKET] Error: {e}")
        await watcher.remove_client(websocket)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "clients": len(watcher.clients),
        "watching": [
            str(Path("approaches").absolute()),
            str(Path("entailment_hypergraph").absolute())
        ]
    }


# Serve the visualization interface
@app.get("/")
async def serve_index():
    """Serve the main visualization page."""
    return FileResponse("entailment_hypergraph/index.html")


# Mount static files
app.mount("/entailment_hypergraph", StaticFiles(directory="entailment_hypergraph"), name="static")
app.mount("/approaches", StaticFiles(directory="approaches"), name="approaches")


def main():
    """Run the server."""
    import uvicorn

    parser = argparse.ArgumentParser(description="Hypergraph Visualization Server")
    parser.add_argument("--port", type=int, default=8765, help="Port to run server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print("=" * 70)
    print("Hypergraph Visualization Server")
    print("=" * 70)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws")
    print()
    print("The server will watch for changes to hypergraph.json files and")
    print("push updates to connected browsers in real-time.")
    print("=" * 70)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
