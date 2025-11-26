#!/bin/bash
# Start the real-time hypergraph visualization server

echo "=========================================="
echo "Hypergraph Visualization Server"
echo "=========================================="
echo ""
echo "Starting server with WebSocket support..."
echo "This will watch for changes to hypergraph.json"
echo "files and push updates to browsers in real-time."
echo ""

# Use pixi to run the server with correct environment
pixi run python hypergraph_server.py --port 8765

# Alternative: run directly with python
# python hypergraph_server.py --port 8765
