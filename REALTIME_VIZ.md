# Real-Time Hypergraph Visualization

This project includes a WebSocket-powered real-time visualization server that automatically updates the hypergraph view whenever files change.

## Features

- **Real-Time Updates**: Changes to `hypergraph.json` files are instantly pushed to all connected browsers
- **WebSocket Communication**: Low-latency bidirectional communication between server and clients
- **Filesystem Watching**: Monitors `approaches/` and `entailment_hypergraph/` directories for changes
- **Automatic Reconnection**: Clients automatically reconnect if connection is lost
- **Fallback to Polling**: Gracefully degrades to 1-second polling if WebSocket unavailable
- **State Preservation**: Maintains zoom, pan, and selection state during updates

## Architecture

```
┌─────────────────────┐
│  Python Backend     │
│  ─────────────      │
│  FastAPI Server     │
│  + WebSocket (/ws)  │
│                     │
│  Watchdog Watcher   │──┐ Monitors filesystem
│  (filesystem)       │  │ for hypergraph.json
└─────────────────────┘  │ changes
         ▲               │
         │ WebSocket     ▼
         │ push updates
         │               ┌──────────────────┐
         ▼               │ HypergraphManager│
┌─────────────────────┐ │ saves changes    │
│  Frontend (Browser) │ └──────────────────┘
│  ─────────────      │
│  index.html         │
│  WebSocket Client   │
│  D3.js Renderer     │
└─────────────────────┘
```

## Usage

### Starting the Server

Option 1: Using the startup script (recommended):
```bash
./start_visualization.sh
```

Option 2: Direct invocation:
```bash
pixi run python hypergraph_server.py --port 8765
```

Option 3: Custom port/host:
```bash
python hypergraph_server.py --port 9000 --host 0.0.0.0
```

### Accessing the Visualization

Once the server is running:

1. **View examples**: http://localhost:8765/
2. **View specific approach**: http://localhost:8765/?graph=approaches/my-approach/hypergraph.json

### Real-Time Updates

When you or an agent modifies a hypergraph:

```python
from agent_system.hypergraph_manager import HypergraphManager

manager = HypergraphManager(Path("approaches/my-approach"))

# This change will instantly appear in connected browsers
manager.add_claim(Claim(
    id="c5",
    text="New claim added in real-time",
    score=8.0,
    reasoning="Testing WebSocket updates"
))
```

All connected browsers will receive the update within milliseconds and re-render the graph while preserving your view state (zoom, pan, selected nodes).

## WebSocket Protocol

### Client → Server

- `ping` - Keepalive ping (sent every 30 seconds)

### Server → Client

Messages are JSON objects with the following structure:

```json
{
  "type": "hypergraph_update",
  "path": "/path/to/hypergraph.json",
  "timestamp": "2025-01-25T14:30:00.123456",
  "data": {
    "metadata": {...},
    "claims": [...],
    "implications": [...]
  },
  "is_incremental": false
}
```

## Health Check

Check server status:
```bash
curl http://localhost:8765/api/health
```

Response:
```json
{
  "status": "ok",
  "clients": 2,
  "watching": [
    "/path/to/approaches",
    "/path/to/entailment_hypergraph"
  ]
}
```

## Browser Console

The visualization logs WebSocket events to the browser console:

- `[WebSocket] Connecting to...` - Attempting connection
- `[WebSocket] ✓ Connected` - Connection established
- `[WebSocket] Received update: hypergraph_update` - Update received
- `[WebSocket] Update matches current graph, reloading...` - Applying update
- `[WebSocket] Disconnected` - Connection lost (will auto-reconnect)
- `[WebSocket] Falling back to polling mode` - Using HTTP polling fallback

## Troubleshooting

### WebSocket not connecting

1. Ensure server is running: `ps aux | grep hypergraph_server`
2. Check firewall/network settings
3. Verify port isn't in use: `lsof -i :8765`
4. Frontend will automatically fall back to polling

### Updates not appearing

1. Check browser console for errors
2. Verify file path matches: The path in the update must match your current view
3. Check server logs for filesystem watcher status
4. Ensure `hypergraph.json` is being saved (not just modified in memory)

### Multiple tabs showing different states

This is expected - each tab maintains its own view state (zoom, pan, collapsed nodes). The underlying data is synchronized, but UI state is per-tab.

## Performance

- **Latency**: Updates typically appear in <100ms
- **Bandwidth**: Only changed files trigger updates (no unnecessary traffic)
- **CPU**: Filesystem watcher is event-driven (no polling overhead)
- **Memory**: Minimal overhead - only stores last known state per file

## Future Enhancements

Potential improvements for the future:

1. **Incremental Updates**: Send only diffs instead of full hypergraph
2. **Undo/Redo**: Track history and allow reverting changes
3. **Collaborative Editing**: Multiple users editing simultaneously
4. **Conflict Resolution**: Handle concurrent edits gracefully
5. **Change Animations**: Animate new/modified/removed nodes
6. **Edit Mode**: Allow editing directly in the browser
