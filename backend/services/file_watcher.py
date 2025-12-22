"""File watcher for hypergraph changes."""

import asyncio
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from .state import get_event_loop
from .websocket import notify_hypergraph_update


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
        now = time.time()
        last = self._last_modified.get(folder, 0)
        if now - last < 0.5:
            return
        self._last_modified[folder] = now

        print(f"[FILE WATCHER] Detected change in {folder}/hypergraph.json", flush=True)

        # Schedule the async notification on the main event loop
        main_event_loop = get_event_loop()
        if main_event_loop and not main_event_loop.is_closed():
            print(f"[FILE WATCHER] Scheduling WebSocket notification for {folder}", flush=True)
            asyncio.run_coroutine_threadsafe(
                notify_hypergraph_update(folder),
                main_event_loop
            )
        else:
            print(f"[FILE WATCHER] Event loop not available for {folder}", flush=True)
