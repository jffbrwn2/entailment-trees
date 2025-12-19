#!/bin/bash
# Start the Entailment Trees Web Application
# Runs both FastAPI backend and React frontend

set -e

# Find an available port starting from the given port
find_port() {
    local port=$1
    while lsof -ti:$port &>/dev/null; do
        port=$((port + 1))
    done
    echo $port
}

# Configuration (auto-find available ports if defaults are taken)
BACKEND_PORT=${BACKEND_PORT:-$(find_port 8000)}
FRONTEND_PORT=${FRONTEND_PORT:-$(find_port 5173)}

echo "🚀 Starting Entailment Trees Web Application"
echo "=============================================="

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."

    # Kill process groups (catches child processes too)
    kill -- -$BACKEND_PID 2>/dev/null || kill $BACKEND_PID 2>/dev/null || true
    kill -- -$FRONTEND_PID 2>/dev/null || kill $FRONTEND_PID 2>/dev/null || true

    # Also kill anything still on our ports (belt and suspenders)
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true

    echo "✓ Stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo ""
echo "📦 Starting FastAPI backend on http://localhost:$BACKEND_PORT..."
cd "$(dirname "$0")"
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start"
    exit 1
fi
echo "✓ Backend running (PID: $BACKEND_PID)"

# Start frontend
echo ""
echo "📦 Starting React frontend on http://localhost:5173..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

echo ""
echo "=============================================="
echo "✅ Web application running!"
echo ""
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "=============================================="

# Open browser
if command -v open &> /dev/null; then
    open http://localhost:$FRONTEND_PORT
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:$FRONTEND_PORT
elif command -v start &> /dev/null; then
    start http://localhost:$FRONTEND_PORT
else
    echo ""
    echo "Open your browser to: http://localhost:$FRONTEND_PORT"
fi

# Wait for processes
wait
