#!/bin/bash
# Start the Entailment Trees Web Application
# Runs both FastAPI backend and React frontend

set -e

echo "🚀 Starting Entailment Trees Web Application"
echo "=============================================="

# Check if we're in the project root
if [ ! -f "features.json" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo ""
echo "📦 Starting FastAPI backend on http://localhost:8000..."
cd "$(dirname "$0")"
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
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
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "=============================================="

# Open browser
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
elif command -v start &> /dev/null; then
    start http://localhost:5173
else
    echo ""
    echo "Open your browser to: http://localhost:5173"
fi

# Wait for processes
wait
