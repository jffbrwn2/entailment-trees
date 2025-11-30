#!/bin/bash
# init.sh - Initialize the Entailment Trees Web Application development environment
# This script sets up the environment for the long-running agent harness

set -e  # Exit on error

echo "🚀 Initializing Entailment Trees Web Application Development Environment"
echo "========================================================================"

# Check if running from project root
if [ ! -f "features.json" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# 1. Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p backend/api/routes
mkdir -p backend/api/models
mkdir -p backend/api/services
mkdir -p backend/api/security
mkdir -p backend/worker
mkdir -p frontend/src/components
mkdir -p frontend/src/hooks
mkdir -p frontend/src/pages
mkdir -p frontend/src/services
mkdir -p frontend/public
mkdir -p docker

echo "   ✓ Directories created"

# 2. Initialize progress tracking
echo ""
echo "📝 Initializing progress tracking..."
if [ ! -f "claude-progress.txt" ]; then
    cat > claude-progress.txt << 'EOF'
# Claude Progress Tracker
# This file tracks work completed across sessions

## Project: Entailment Trees Web Application
## Start Date: $(date +%Y-%m-%d)

## Session 1: Harness Setup
- Created features.json with all Phase 1 & 2 tasks
- Created init.sh environment setup script
- Initialized progress tracking system
- Created baseline git structure

## Next Steps:
- Begin Phase 1: Backend Setup
- Reference features.json for task list
- Update this file after each completed feature

## Notes:
- Always commit after completing a feature
- Run tests before marking features complete
- Keep progress descriptions concise and specific
EOF
    echo "   ✓ claude-progress.txt created"
else
    echo "   ✓ claude-progress.txt already exists"
fi

# 3. Check Python environment
echo ""
echo "🐍 Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "   ✓ Python found: $PYTHON_VERSION"
else
    echo "   ⚠️  Warning: Python 3 not found in PATH"
fi

# Check for uv (project uses uv for dependency management)
if command -v uv &> /dev/null; then
    echo "   ✓ uv found: $(uv --version)"
    echo "   📦 Installing Python dependencies via uv..."
    uv sync
else
    echo "   ℹ️  uv not found - project uses uv for dependencies"
    echo "   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# 4. Check Node.js environment (for frontend)
echo ""
echo "📦 Checking Node.js environment..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "   ✓ Node.js found: $NODE_VERSION"
else
    echo "   ⚠️  Warning: Node.js not found - needed for frontend"
    echo "   Install from: https://nodejs.org/"
fi

# 5. Check Docker
echo ""
echo "🐳 Checking Docker environment..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "   ✓ Docker found: $DOCKER_VERSION"
else
    echo "   ⚠️  Warning: Docker not found - needed for Phase 2 (simulations)"
    echo "   Install from: https://www.docker.com/get-started"
fi

# 6. Create .env.example for environment variables
echo ""
echo "🔐 Creating environment configuration templates..."
cat > .env.example << 'EOF'
# Backend Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/entailment_trees
S3_ENDPOINT=https://your-r2-endpoint.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=entailment-trees

# Authentication (Clerk)
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Environment
ENVIRONMENT=development
EOF
echo "   ✓ .env.example created"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "   ℹ️  Copy .env.example to .env and fill in your credentials"
else
    echo "   ✓ .env file exists"
fi

# 7. Initialize git if needed
echo ""
echo "📚 Checking git repository..."
if [ -d ".git" ]; then
    echo "   ✓ Git repository already initialized"

    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    echo "   ✓ Current branch: $CURRENT_BRANCH"

    # Show recent commits
    echo "   📜 Recent commits:"
    git log --oneline -3 | sed 's/^/      /'
else
    echo "   ⚠️  Git repository not found"
fi

# 8. Summary
echo ""
echo "========================================================================"
echo "✅ Environment initialization complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Copy .env.example to .env and configure credentials"
echo "   2. Review features.json for Phase 1 tasks"
echo "   3. Start with 'backend-setup' feature"
echo "   4. Update claude-progress.txt after each feature"
echo "   5. Commit changes with descriptive messages"
echo ""
echo "📖 Quick Commands:"
echo "   • Start both servers: ./start_web.sh"
echo "   • Start backend only: uv run python -m uvicorn backend.main:app --reload"
echo "   • Start frontend only: cd frontend && npm run dev"
echo "   • View progress: cat claude-progress.txt"
echo "   • View features: cat features.json | jq '.phases'"
echo ""
echo "🤖 This harness enables long-running agent development with:"
echo "   • Feature tracking (features.json)"
echo "   • Progress persistence (claude-progress.txt)"
echo "   • Git-based memory (commit after each feature)"
echo "   • Incremental work (one feature at a time)"
echo "========================================================================"
