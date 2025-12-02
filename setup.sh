#!/bin/bash
# Entailment Trees - Setup Script
# Installs dependencies, checks for API key, and optionally launches the app

set -e

ANTHROPIC_CONSOLE_URL="https://console.anthropic.com/settings/keys"

echo ""
echo "=========================================="
echo "  Entailment Trees Setup"
echo "=========================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Step 1: Check for uv
echo "Step 1: Checking for uv package manager..."
if ! command -v uv &> /dev/null; then
    echo "  uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the profile to get uv in path
    export PATH="$HOME/.local/bin:$PATH"
    echo "  ✓ uv installed"
else
    echo "  ✓ uv found"
fi

# Step 2: Check for Node.js (requires 18+)
echo ""
echo "Step 2: Checking for Node.js..."
if ! command -v node &> /dev/null; then
    echo "  ✗ Node.js not found"
    echo ""
    echo "  Please install Node.js 18+ from: https://nodejs.org/"
    echo "  Or use a version manager like nvm: https://github.com/nvm-sh/nvm"
    exit 1
else
    NODE_VERSION=$(node -v)
    # Extract major version number (remove 'v' prefix and get first number before '.')
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d'.' -f1)

    if [ "$NODE_MAJOR" -lt 18 ] 2>/dev/null; then
        echo "  ✗ Node.js $NODE_VERSION is too old (requires 18+)"
        echo ""
        NODE_PATH=$(which node)
        if [[ "$NODE_PATH" == *"anaconda"* ]] || [[ "$NODE_PATH" == *"conda"* ]]; then
            echo "  ⚠️  You have an old Node.js from Anaconda/Conda."
            echo "     Conda's Node.js is often outdated and causes issues."
            echo ""
        fi
        echo "  Please install Node.js 18+ from one of these options:"
        echo ""
        echo "  Option 1 - Official installer (recommended):"
        echo "    https://nodejs.org/"
        echo ""
        echo "  Option 2 - Using nvm (Node Version Manager):"
        echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
        echo "    nvm install 20"
        echo "    nvm use 20"
        echo ""
        echo "  Option 3 - Using Homebrew (macOS):"
        echo "    brew install node@20"
        echo ""
        echo "  After installing, restart your terminal and run this script again."
        exit 1
    else
        echo "  ✓ Node.js found ($NODE_VERSION)"
    fi
fi

# Step 3: Install Python dependencies
echo ""
echo "Step 3: Installing Python dependencies..."
uv sync
echo "  ✓ Python dependencies installed"

# Step 4: Install frontend dependencies
echo ""
echo "Step 4: Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "  (node_modules exists, skipping npm install)"
fi
echo "  ✓ Frontend dependencies installed"
cd ..

# Step 5: Check for API key
echo ""
echo "=========================================="
echo "  API Key Check"
echo "=========================================="
echo ""

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY is not set"
    echo ""
    echo "To use the AI agent, you need an Anthropic API key."
    echo ""
    echo "Get your API key here:"
    echo "  $ANTHROPIC_CONSOLE_URL"
    echo ""
    echo "Then set it in your shell:"
    echo "  export ANTHROPIC_API_KEY=\"sk-ant-...\""
    echo ""
    echo "Or add it to your ~/.bashrc or ~/.zshrc to make it persistent."
    echo ""
    echo "=========================================="
    echo "  Setup Complete (without API key)"
    echo "=========================================="
    echo ""
    echo "Once you have your API key set, run:"
    echo "  ./start_web.sh"
    echo ""
else
    echo "✓ ANTHROPIC_API_KEY is set"
    echo ""
    echo "=========================================="
    echo "  Setup Complete!"
    echo "=========================================="
    echo ""
    read -p "Would you like to launch the web app now? [Y/n] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        echo "To start later, run:"
        echo "  ./start_web.sh"
        echo ""
    else
        echo ""
        exec ./start_web.sh
    fi
fi
