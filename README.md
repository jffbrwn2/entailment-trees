# Entailment Trees

Let AI agents autonomously explore and evaluate your ideas, or collaborate with them directly. The system breaks hypotheses into testable claims, researches literature, writes simulations, and builds a visual map of evidence and logical connections.

**How it works:**
1. Enter an idea or hypothesis
2. Enable Auto Mode to let agents explore autonomously, or chat to guide the investigation yourself
3. Watch the hypergraph update as evidence accumulates and scores propagate

## Requirements

- **Node.js 18+** - [Download here](https://nodejs.org/) or use `nvm install 20`
- **Python 3.10+** - Installed automatically by the setup script via uv
- **Anthropic API key** - [Get one here](https://console.anthropic.com/settings/keys)
- **OpenRouter API key** (for Auto Mode) - [Get one here](https://openrouter.ai/keys)

> ⚠️ **Anaconda/Conda users:** Conda often has outdated Node.js versions (e.g., v6.x). Install Node.js separately from https://nodejs.org/ or use nvm.

## Quick Start

```bash
git clone https://github.com/jffbrwn2/entailment-trees.git
cd entailment-trees
./setup.sh
```

**Windows users:** Use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) or [Git Bash](https://git-scm.com/downloads).

The setup script will:
1. Install [uv](https://docs.astral.sh/uv/) if needed
2. Check for Node.js 18+
3. Install all dependencies
4. Check for your Anthropic API key
5. Offer to launch the web app

**Set your API keys:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."      # https://console.anthropic.com/settings/keys
export OPENROUTER_API_KEY="sk-or-..."      # https://openrouter.ai/keys (for Auto Mode)
```

## Usage

Once set up, start the web app anytime with:

```bash
./start_web.sh
```

Then open http://localhost:5173 in your browser.

### What You Can Do

1. **Create an approach** - Start evaluating a new idea or hypothesis
2. **Chat with the agent** - Ask questions, request simulations, explore literature
3. **Visualize the hypergraph** - See claims, evidence, and logical relationships
4. **Track progress** - Watch scores update as evidence accumulates

### Example Conversation

```
You: Can we detect neural signals using ultrasound reflections?

Agent: I'll break this down into testable claims:

c1: "Ultrasound can propagate through skull with sufficient amplitude"
    Score: TBD (needs simulation)

c2: "Neural activity causes detectable acoustic impedance changes"
    Score: TBD (needs calculation)

c3: "Signal-to-noise ratio is sufficient for detection"
    Score: TBD (critical unknown)

Which claim should we investigate first?
```

The agent writes simulations, searches literature, and updates the hypergraph with evidence.

## Optional: Edison Scientific

For enhanced literature search, set:
```bash
export EDISON_API_KEY="your-edison-key"
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [CLAUDE.md](CLAUDE.md) - Agent guidelines
- [entailment_hypergraph/README.md](entailment_hypergraph/README.md) - Hypergraph structure
