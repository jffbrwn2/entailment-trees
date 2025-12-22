"""
FastAPI backend for Entailment Trees Web Application.

Wraps the existing agent_system to expose HTTP/SSE/WebSocket endpoints.
"""

import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from watchdog.observers import Observer

# Add parent directory to path so we can import agent_system
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_system import AgentOrchestrator
from agent_system.config import AgentConfig

from backend.routes import (
    approaches_router,
    chat_router,
    conversations_router,
    auto_mode_router,
    settings_router,
    gapmap_router,
    websocket_router,
)
from backend.services import set_orchestrator, set_event_loop, get_orchestrator
from backend.services.file_watcher import HypergraphFileHandler

# File watcher instance
file_observer: Observer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator and file watcher on startup."""
    global file_observer

    # Store reference to main event loop for file watcher callbacks
    set_event_loop(asyncio.get_running_loop())

    # Initialize orchestrator
    orchestrator = AgentOrchestrator(AgentConfig.from_env())
    set_orchestrator(orchestrator)

    # Start file watcher for hypergraph changes
    approaches_dir = orchestrator.config.approaches_dir.resolve()
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

    orchestrator = get_orchestrator()
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

# Register routers
app.include_router(approaches_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(auto_mode_router)
app.include_router(settings_router)
app.include_router(gapmap_router)
app.include_router(websocket_router)

# Mount static files (must be after API routes)
PROJECT_ROOT = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/approaches", StaticFiles(directory=PROJECT_ROOT / "approaches"), name="approaches")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
