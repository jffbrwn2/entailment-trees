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
    echo "  uv not found."
    echo ""
    read -p "  Press Enter to install uv (https://astral.sh/uv), or Ctrl+C to cancel..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the profile to get uv in path
    export PATH="$HOME/.local/bin:$PATH"
    echo "  uv installed"
else
    echo "  uv found"
fi

# Step 2: Check for Node.js (requires 18+)
echo ""
echo "Step 2: Checking for Node.js..."

# Helper function to check node version
check_node_version() {
    if ! command -v node &> /dev/null; then
        return 1
    fi
    NODE_VERSION=$(node -v)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d'.' -f1)
    [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null
}

# Helper function to load nvm
load_nvm() {
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
}

if check_node_version; then
    echo "  Node.js found ($(node -v))"
else
    # Check if nvm is available
    load_nvm

    if command -v nvm &> /dev/null; then
        # nvm is available, check for installed versions
        NVM_VERSIONS=$(nvm ls --no-colors 2>/dev/null | grep -E "v(1[89]|[2-9][0-9])\." | head -1 | sed 's/.*\(v[0-9]*\.[0-9]*\.[0-9]*\).*/\1/')

        if [ -n "$NVM_VERSIONS" ]; then
            echo "  Current Node.js is too old, but nvm has newer versions available."
            echo ""
            read -p "  Press Enter to activate Node.js $NVM_VERSIONS via nvm, or Ctrl+C to cancel..."
            nvm use "$NVM_VERSIONS" > /dev/null
            echo "  Node.js $(node -v) activated via nvm"
        else
            echo "  Current Node.js is too old, but nvm is available."
            echo ""
            read -p "  Press Enter to install Node.js 20 via nvm, or Ctrl+C to cancel..."
            nvm install 20
            echo "  Node.js $(node -v) installed via nvm"
        fi
    else
        # No nvm, show manual instructions
        if command -v node &> /dev/null; then
            echo "  Node.js $(node -v) is too old (requires 18+)"
        else
            echo "  Node.js not found"
        fi
        echo ""
        NODE_PATH=$(which node 2>/dev/null)
        if [[ "$NODE_PATH" == *"anaconda"* ]] || [[ "$NODE_PATH" == *"conda"* ]]; then
            echo "  WARNING: You have an old Node.js from Anaconda/Conda."
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
    fi
fi

# Step 3: Install Python dependencies
echo ""
echo "Step 3: Installing Python dependencies..."
uv sync
echo "  Python dependencies installed"

# Step 4: Install frontend dependencies
echo ""
echo "Step 4: Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "  (node_modules exists, skipping npm install)"
fi
echo "  Frontend dependencies installed"
cd ..

# Step 5: Check for API keys
echo ""
echo "=========================================="
echo "  API Key Setup"
echo "=========================================="

# Detect shell config file
if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
else
    SHELL_CONFIG="$HOME/.bashrc"
fi

# Function to prompt for and save an API key
prompt_for_key() {
    local key_name="$1"
    local key_url="$2"
    local key_desc="$3"
    local required="$4"

    echo ""
    if [ "$required" = "required" ]; then
        echo "$key_name is not set (required)"
    else
        echo "$key_name not set (optional - $key_desc)"
    fi
    echo "  Get your key: $key_url"
    echo ""
    read -p "  Paste your $key_name (or press Enter to skip): " key_value

    if [ -n "$key_value" ]; then
        # Export for current session
        export "$key_name"="$key_value"
        # Add to shell config
        echo "" >> "$SHELL_CONFIG"
        echo "export $key_name=\"$key_value\"" >> "$SHELL_CONFIG"
        echo "  $key_name saved to $SHELL_CONFIG"
        return 0
    else
        echo "  Skipped"
        return 1
    fi
}

# Required: Anthropic
if [ -z "$ANTHROPIC_API_KEY" ]; then
    prompt_for_key "ANTHROPIC_API_KEY" "$ANTHROPIC_CONSOLE_URL" "" "required"
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        MISSING_REQUIRED=1
    fi
else
    echo ""
    echo "ANTHROPIC_API_KEY is set"
fi

# Optional: OpenRouter (for auto mode models)
if [ -z "$OPENROUTER_API_KEY" ]; then
    prompt_for_key "OPENROUTER_API_KEY" "https://openrouter.ai/keys" "for auto mode"
else
    echo ""
    echo "OPENROUTER_API_KEY is set"
fi

# Optional: Edison (for literature search)
if [ -z "$EDISON_API_KEY" ]; then
    prompt_for_key "EDISON_API_KEY" "https://edison.so" "for literature search"
else
    echo ""
    echo "EDISON_API_KEY is set"
fi

echo ""

if [ -n "$MISSING_REQUIRED" ]; then
    echo "=========================================="
    echo "  Setup Complete (missing required key)"
    echo "=========================================="
    echo ""
    echo "Once you have ANTHROPIC_API_KEY set, run:"
    echo "  ./start_web.sh"
    echo ""
else
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
