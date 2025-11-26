# Entailment Trees 

A tool for collaborating with an AI agent to rigorously evaluate ideas through structured reasoning, simulations, and literature research.

## Installation

### Prerequisites

- Python 3.10+
- [Pixi](https://pixi.sh/) package manager

### Install

```bash
# Install pixi if needed
curl -fsSL https://pixi.sh/install.sh | bash

# Clone and install dependencies
git clone https://github.com/jffbrwn2/entailment-trees.git
cd entailment-trees
pixi install
```

### Set API Keys

Required:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Optional (for enhanced scientific literature search):
```bash
export EDISON_API_KEY="your-edison-key"
```

Add these to your `~/.bashrc` or `~/.zshrc` to make them persistent.

## Quick Start

### 1. Start the CLI

```bash
pixi run python -m agent_system.agent_cli
```

### 2. Create a New Approach

```
> /new
What would you like to call this approach? ultrasound-neural-sensing
What idea or claim would you like to evaluate?
> We can detect neural signals using ultrasound reflections
```

### 3. Chat with the Agent

```
> What are the key physical parameters we need to understand?

Agent: To detect neural signals with ultrasound, we need to understand:
1. The amplitude of electrical signals from neurons
2. How these signals affect acoustic impedance in tissue
3. The sensitivity of ultrasound detectors
...

> Can you write a simulation to estimate the signal strength?

Agent: I'll create a simulation that models:
- Ionic current from action potentials
- Resulting electromagnetic fields
- Acoustic impedance changes
...
```

The agent will write code, run simulations, and update the hypergraph with evidence.

### 4. Visualize the Hypergraph

Start the real-time visualization server:

```bash
./start_visualization.sh
```

Open in browser:
```
http://localhost:8765/
```

The visualization updates automatically as the agent works! (Note: Sometimes you have to refresh the page to see the updates.)

## Example 1: Generate First Layer of Entailment Graph

```
> /new
What would you like to call this approach? acoustic-neural-interface
What idea or claim would you like to evaluate?
> Acoustic waves can modulate neural activity for brain-computer interfaces

> Can you break down this hypothesis into the first layer of testable claims?

Agent: I'll decompose this into fundamental premises:

c1: "Acoustic waves can propagate through skull/brain with sufficient amplitude"
    Score: TBD (needs simulation)

c2: "Acoustic waves can create mechanical forces on neural membranes"
    Score: TBD (needs calculation)

c3: "Mechanical forces can affect ion channel gating"
    Score: TBD (needs literature)

c4: "Ion channel changes can trigger/modulate action potentials"
    Score: 9/10 (well-established)

c5: "The effect has useful signal-to-noise ratio"
    Score: TBD (critical blocker)

Created implication:
(c1 AND c2 AND c3 AND c4 AND c5) → Hypothesis

Which claim should we investigate first?
```

## Example 2: Browsing GAP-MAP Research Database

```
> Can you list the research gaps in the Biology field from GAP-MAP?

Agent: I'll query the GAP-MAP database to find biology research gaps...

[Agent uses gapmap_client to browse catalogued problems]

Agent: Found 23 research gaps in Biology, including:

1. "Predicting protein folding from sequence alone"
   Status: Active area of research
   Related capabilities: AlphaFold, RoseTTAFold

2. "Non-invasive continuous glucose monitoring"
   Status: Partially solved
   Related capabilities: Optical sensing, microneedle arrays

3. "Real-time whole-brain neural activity recording"
   Status: Open problem
   Related capabilities: Voltage imaging, optogenetics

Would you like to see proposed solutions for any of these gaps?
```

## Example 3: Using Edison for Literature Search

```
> Can you use Edison to find papers about the amplitude of EEG signals?

Agent: I'll submit a literature search task to Edison Scientific...

[Agent submits async task to Edison]

Agent: Edison is searching scientific literature... (task ID: abc123)

[Polls for completion]

Agent: Found evidence from literature:

"Typical EEG signal amplitudes range from 10-100 microvolts (µV) at the scalp surface,
with alpha waves (8-13 Hz) typically around 50 µV and beta waves (13-30 Hz) around
10-30 µV." [Source: Clinical Neurophysiology, 2019]

Adding this to the hypergraph as literature evidence with score 9/10 (well-established).
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/new` | Start a new approach |
| `/list` | List existing approaches |
| `/load` | Load an existing approach |
| `/status` | Show current hypergraph statistics |
| `/validate` | Check hypergraph structure |
| `/cleanup` | Remove unreachable nodes from hypergraph |
| `/history` | View hypergraph version history |
| `/restore` | Restore a previous hypergraph version |
| `/set-model` | Change the evaluation model used for scoring |
| `/viz` | Show visualization instructions |
| `/help` | Show all commands |
| `/quit` | Exit |

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and architecture
- [CLAUDE.md](CLAUDE.md) - Guidelines for the AI agent
- [entailment_hypergraph/README.md](entailment_hypergraph/README.md) - Hypergraph structure and validation

## Troubleshooting

**API key not found:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
echo $ANTHROPIC_API_KEY  # Verify it's set
```

**Visualization not updating:**
Use the WebSocket server: `./start_visualization.sh`

**Type checking fails:**
```bash
python typecheck_hypergraph.py approaches/your-approach/hypergraph.json
```
