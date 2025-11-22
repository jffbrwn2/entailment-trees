# Hypergraph Collaboration System - Architecture

## Vision

A tool for thought where users collaborate with an AI agent to rigorously evaluate ideas through:
- **Structured reasoning** - Entailment hypergraphs make logic explicit
- **Simulation** - Agent writes code to test physical/computational feasibility
- **Literature grounding** - Agent searches papers and citations
- **Interactive refinement** - User guides, agent executes

## Key Insight

**We're building a thin wrapper around Headless Claude Code that provides hypergraph structure.**

Claude Code already has all the tools needed (Write, Bash, Read, WebSearch). We just:
1. Initialize approach folders with hypergraph templates
2. Provide system prompts explaining hypergraph schema
3. Validate hypergraph after updates
4. Help format evidence correctly

The agent does the heavy lifting using its built-in capabilities!

## Design Principles

1. **Progressive enhancement**: Terminal → Web without major rewrites
2. **Separation of concerns**: Core logic independent of UI
3. **Folder-per-approach**: Self-contained workspaces (sims + hypergraph + docs)
4. **Type safety**: Validated hypergraph structure at all times
5. **Traceable evidence**: Every score links to source code or citation

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  ┌─────────────────┐         ┌──────────────────────┐  │
│  │  CLI (Phase 1)  │   →     │   Web UI (Phase 3)   │  │
│  │  - Terminal     │         │   - Chat interface   │  │
│  │  - REPL style   │         │   - Embedded viz     │  │
│  └─────────────────┘         └──────────────────────┘  │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │
                ▼                         ▼
┌─────────────────────────────────────────────────────────┐
│         Agent Orchestrator (Thin Wrapper)                │
│  - Initialize approach folders                           │
│  - Track conversation context                            │
│  - Parse sim outputs → hypergraph evidence              │
│  - Validate hypergraph after updates                     │
│  - Approval workflows for major operations               │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   Headless Claude Code │
         │   (Does heavy lifting) │
         │                        │
         │   Built-in tools:      │
         │   - Write (sims)       │
         │   - Bash (run code)    │
         │   - Read (files)       │
         │   - Edit (update)      │
         │   - WebSearch (lit)    │
         └────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │   Hypergraph Manager        │
    │   - CRUD operations         │
    │   - Type validation         │
    │   - Evidence formatting     │
    └─────────────┬───────────────┘
                  │
                  ▼
         ┌──────────────────────────┐
         │     File System          │
         │  approaches/             │
         │    └── approach_name/    │
         │        ├── hypergraph.json│
         │        ├── README.md     │
         │        └── simulations/  │
         │                          │
         │  entailment_hypergraph/  │
         │    └── index.html (viz)  │
         └──────────────────────────┘
```

## Phase 1: Terminal Interface (Current Sprint)

**Goal**: User can start a claim, agent helps flesh it out interactively.

### Components

#### 1. CLI Interface (`agent_cli.py`)
```python
# Simple REPL-style interface
while True:
    user_input = input("You: ")

    # Send to agent orchestrator
    response = await orchestrator.process(user_input, session)

    # Display response + show hypergraph updates
    print(f"Agent: {response.message}")
    if response.needs_approval:
        approve = input("Approve? (y/n): ")
```

**Features:**
- Create new approach from claim
- Interactive conversation with agent
- Approve/reject simulation creation
- View current hypergraph state
- Run simulations
- Update claims/evidence

#### 2. Agent Orchestrator (`agent_orchestrator.py`)
```python
class AgentOrchestrator:
    """Thin wrapper providing hypergraph structure around Claude Code."""

    def __init__(self, headless_claude_config):
        self.claude = HeadlessClaudeCode(config)
        self.hypergraph_mgr = HypergraphManager()
        self.current_approach = None

    async def start_approach(self, claim: str, name: str):
        """Initialize new approach folder with initial hypergraph."""
        approach_dir = Path("approaches") / name
        approach_dir.mkdir(parents=True, exist_ok=True)
        (approach_dir / "simulations").mkdir(exist_ok=True)

        # Create initial hypergraph with first claim
        self.hypergraph_mgr.create_approach(approach_dir, claim)
        self.current_approach = approach_dir

        # Set context for Claude
        context = f"Working on approach: {name}\nInitial claim: {claim}"
        return context

    async def process(self, user_input, session):
        """Process user input. Claude Code does heavy lifting."""
        session.history.append({"role": "user", "content": user_input})

        # Claude Code has built-in tools (Write, Bash, Read, WebSearch)
        # We just provide hypergraph-specific helpers via system prompt
        response = await self.claude.query(
            messages=session.history,
            system_prompt=self._get_hypergraph_instructions()
        )

        # After Claude responds, validate hypergraph if it was updated
        if self._hypergraph_was_modified(response):
            errors, warnings = self.hypergraph_mgr.validate()
            if errors:
                return f"Hypergraph validation failed: {errors}"

        return response

    def _get_hypergraph_instructions(self):
        """Instructions for Claude on hypergraph structure."""
        return f"""
        You're helping evaluate: {self.current_approach}

        Hypergraph location: {self.current_approach}/hypergraph.json
        Simulations folder: {self.current_approach}/simulations/

        When updating the hypergraph:
        1. Read current hypergraph.json
        2. Add claims/implications following the schema
        3. Write updated hypergraph.json
        4. Ensure evidence has correct format (see examples)

        Evidence types:
        - simulation: {{"type": "simulation", "source": "path", "lines": "10-50", "code": "..."}}
        - literature: {{"type": "literature", "source": "citation", "reference_text": "quote"}}
        - calculation: {{"type": "calculation", "equations": "...", "program": "..."}}
        """
```

**Approval Points:**
- Writing new simulation code
- Adding claims to hypergraph
- Updating scores based on simulation results
- Finalizing the approach

#### 3. Hypergraph Manager (`hypergraph_manager.py`)
```python
class HypergraphManager:
    """CRUD operations on hypergraph JSON with validation."""

    def create_approach(self, name: str, initial_claim: str) -> Path:
        """Create folder structure + initial hypergraph."""

    def add_claim(self, claim: Claim) -> str:
        """Add claim, validate, save. Returns claim ID."""

    def add_implication(self, premises: List[str], conclusion: str, type: str):
        """Add logical implication."""

    def update_claim_evidence(self, claim_id: str, evidence: Evidence):
        """Add evidence to existing claim."""

    def validate(self) -> Tuple[List[str], List[str]]:
        """Run typecheck_hypergraph.py."""

    def get_graph(self) -> Dict:
        """Return current hypergraph state."""
```

#### 4. Evidence Parser (`evidence_parser.py`)
```python
def parse_simulation_output(sim_path: Path, stdout: str) -> dict:
    """Parse simulation output into evidence format for hypergraph.

    Args:
        sim_path: Path to simulation file
        stdout: Captured output from running simulation

    Returns:
        Evidence dict ready for hypergraph insertion
    """
    # Extract relevant code lines
    with open(sim_path) as f:
        code_lines = f.readlines()

    # Find key calculation/result lines
    relevant_lines = identify_key_lines(code_lines, stdout)

    return {
        "type": "simulation",
        "source": str(sim_path.relative_to(Path.cwd())),
        "lines": format_line_spec(relevant_lines),
        "code": ''.join([code_lines[i] for i in relevant_lines])
    }

def format_literature_evidence(citation: str, quote: str) -> dict:
    """Format literature search results into evidence."""
    return {
        "type": "literature",
        "source": citation,
        "reference_text": quote
    }
```

### Folder Structure
```
ai-simulations/
├── ARCHITECTURE.md                    # This file
├── agent_system/                      # New: Agent components
│   ├── __init__.py
│   ├── agent_cli.py                   # Terminal interface (REPL)
│   ├── agent_orchestrator.py          # Thin wrapper around Claude Code
│   ├── hypergraph_manager.py          # Hypergraph CRUD + validation
│   ├── evidence_parser.py             # Parse outputs → evidence format
│   └── config.py                      # Configs (API keys, paths)
├── entailment_hypergraph/             # Existing: Visualizer
│   └── index.html                     # Interactive graph viz
├── typecheck_hypergraph.py            # Existing: Validation
└── approaches/                        # User approaches (created by agent)
    └── <approach_name>/               # One per idea
        ├── hypergraph.json            # The entailment hypergraph
        ├── README.md                  # Generated summary
        └── simulations/               # Python simulations
            └── *.py
```

## Phase 2: Enhanced Agent Capabilities

### Claude Code Built-in Tools (Already Available)

Claude Code provides these tools that enable the agent:

1. **Write** - Create simulation files, update hypergraph.json
2. **Read** - Read existing hypergraph, simulation code
3. **Edit** - Modify existing files (claims, scores, evidence)
4. **Bash** - Run simulations, start visualization server
5. **WebSearch** - Find papers, look up physical constants
6. **Glob/Grep** - Search for existing simulations, find references

### What We Add (Helper Functions)

The orchestrator provides guidance via system prompt on:

1. **Hypergraph schema** - How to structure claims/implications/evidence
2. **Evidence formatting** - Proper format for simulation/literature/calculation types
3. **Validation triggers** - When to run type checker
4. **Approval workflows** - Which operations need user approval
5. **Visualization** - How to open the interactive graph viewer

### Agent Workflow Example

```
User: "I want to evaluate if we can detect neural signals using ultrasound"

Agent: I'll help you evaluate this idea. Let me start by breaking it down
       into testable claims.

       [Tool: create_claim]
       Created claim c1: "Neural signals produce detectable ultrasound reflections"

       To evaluate this, I need to understand:
       1. What's the amplitude of neural electrical signals?
       2. How do ultrasound waves interact with tissue?
       3. What's the detection threshold of ultrasound sensors?

       Should I create a simulation to estimate signal strength?

User: Yes, do that

Agent: [Tool: write_simulation]
       I'll create simulations/neural_signal_amplitude.py

       [Shows code preview]

       This simulation will:
       - Model ionic current from action potentials
       - Calculate resulting electromagnetic fields
       - Estimate acoustic impedance changes

       Approve this simulation?

User: Looks good

Agent: [Tool: run_simulation]
       Running simulation...

       Results: Neural signals produce ~10^-12 Pa acoustic pressure changes
       Detection threshold: ~10^-6 Pa (typical ultrasound sensor)

       SNR = signal/threshold = 10^-6 (extremely low)

       [Tool: update_claim]
       Updated c1 score to 2/10 - signal is 1 million times too weak

       This is a critical blocker. The approach seems infeasible because...
```

## Phase 3: Web Interface

### Architecture Changes

```
┌──────────────────────────────┐
│       Next.js Web App        │
│                              │
│  ┌────────────────────────┐  │
│  │   Chat Interface       │  │  Conversation with agent
│  │   - User messages      │  │
│  │   - Agent responses    │  │
│  │   - Approval buttons   │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │  Hypergraph Visualizer │  │  Live graph view
│  │  (embedded from        │  │  Updates as agent works
│  │   entailment_hypergraph)│  │  Click nodes → see code
│  └────────────────────────┘  │
└──────────────┬───────────────┘
               │ HTTP/WebSocket
               ▼
┌──────────────────────────────┐
│      Backend API (FastAPI)   │
│                              │
│  Reuses from Phase 1:        │
│  - AgentOrchestrator         │
│  - HypergraphManager         │
│  - Evidence parsers          │
│                              │
│  + Session management        │
│  + WebSocket streaming       │
└──────────────────────────────┘
```

### Key Additions

1. **Session persistence**: Store conversation history, hypergraph state in DB
2. **Real-time updates**: WebSocket for streaming agent responses as they type
3. **Visualization embedding**: Embed existing D3.js visualizer (already works standalone)
4. **Export**: Download approach as ZIP (hypergraph + sims + README)
5. **Authentication**: Simple password-based auth for personal use

### Web-specific Considerations

- **Sandboxing**: Run simulations in isolated containers (Docker)
- **Rate limiting**: Prevent abuse of Claude API
- **Authentication**: Simple auth (personal tool = just password)
- **Storage**: File system initially, could move to DB later
- **Cost tracking**: Monitor API usage per session

## Data Model

### Session
```python
@dataclass
class Session:
    id: str
    approach_name: str
    approach_dir: Path
    history: List[Message]
    created: datetime
    last_activity: datetime
```

### Hypergraph (already defined in JSON)
See `entailment_hypergraph/README.md` for full schema.

### Evidence Types
- **simulation**: Links to Python file + line numbers + extracted code
- **literature**: Citation + extracted quote
- **calculation**: Equations + Python calculation function

## Implementation Plan

### Sprint 1: Core Agent System (Terminal)
- [ ] Create `agent_system/` package structure
- [ ] Implement `HypergraphManager` with CRUD operations
- [ ] Implement evidence parsing helpers (`evidence_parser.py`)
- [ ] Set up Headless Claude Code integration
- [ ] Create `agent_orchestrator.py` (thin wrapper with system prompt)
- [ ] Build simple CLI REPL interface
- [ ] Create example system prompt with hypergraph instructions
- [ ] Test with example: "Detect neural signals with ultrasound"

### Sprint 2: Enhanced Interactions
- [ ] Add approval workflows for critical operations
- [ ] Implement conversation state management
- [ ] Add simulation result parsing and evidence extraction
- [ ] Create ASCII visualization of hypergraph for terminal
- [ ] Add command: `/visualize` to open browser with current graph
- [ ] Add command: `/status` to show current claims/scores

### Sprint 3: Web UI (Future)
- [ ] Set up Next.js frontend
- [ ] Create FastAPI backend wrapping orchestrator
- [ ] Implement WebSocket for streaming
- [ ] Embed hypergraph visualizer
- [ ] Add code preview/editor
- [ ] Add session management
- [ ] Deploy as personal tool

## Security & Sandboxing

### Phase 1 (Terminal)
- Simulations run in same Python environment
- **Risk**: Malicious code could access file system
- **Mitigation**: User reviews all code before running
- **Acceptable** for personal tool

### Phase 3 (Web)
- **Must sandbox**: Use Docker containers or `RestrictedPython`
- Limit: CPU time, memory, network access
- Prevent: File system access outside workspace
- Example: RunPod, Modal, or custom Docker setup

## Technology Stack

### Current
- Python 3.12
- JSON for data storage
- Pixi for package management
- D3.js for visualization

### Phase 1 Additions
- Headless Claude Code (via SDK)
- MCP tools (optional, for literature search)

### Phase 3 Additions
- **Frontend**: Next.js, React, TypeScript
- **Backend**: FastAPI, Python
- **Real-time**: WebSockets
- **Deployment**: Vercel (frontend) + Railway/Fly.io (backend)
- **Sandboxing**: Docker or Modal

## Open Questions

1. **Literature search**: Use MCP tool, web scraping, or API (Semantic Scholar)?
2. **Cost management**: How to handle Claude API costs in web version?
3. **Collaboration**: Eventually support multiple users working on same hypergraph?
4. **Simulation limits**: Max execution time? Max file size? Allowed imports?
5. **Export format**: Just JSON? Include generated README? Jupyter notebooks?

## Success Metrics

### Phase 1
- User can start with claim, end with complete hypergraph
- Agent writes valid simulations that execute successfully
- Hypergraph passes type checking
- User can visualize final graph in browser

### Phase 3
- Multiple users can use system simultaneously
- Session persistence works across page reloads
- Real-time graph updates as agent works
- Clean, intuitive UI for conversation + visualization

## Next Steps

1. Review this architecture - does it align with your vision?
2. Create project structure for `agent_system/`
3. Start with `HypergraphManager` - build CRUD operations
4. Test hypergraph operations independently
5. Integrate Headless Claude Code
6. Build simple CLI loop
