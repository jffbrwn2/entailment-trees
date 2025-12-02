# Entailment Trees

A tool for collaborating with an AI agent to rigorously evaluate ideas through structured reasoning, simulations, and literature research.

**How it works:**
1. Start with an idea or hypothesis you want to evaluate
2. The agent breaks it down into testable claims and maps how they logically connect
3. Chat with the agent to research claims - it searches literature, writes simulations, and runs calculations
4. Watch the hypergraph visualization update as evidence accumulates and scores propagate

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

**Need an API key?** Get one at: https://console.anthropic.com/settings/keys

Then set it:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
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
