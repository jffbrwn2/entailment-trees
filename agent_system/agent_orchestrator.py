"""
Agent Orchestrator - Thin wrapper around Headless Claude Code.

Provides hypergraph structure and context to Claude Code, which does the heavy lifting
of writing simulations, running them, and searching literature.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .hypergraph_manager import HypergraphManager
from .config import AgentConfig
from .claude_client import ClaudeCodeClient, ClaudeResponse, ClientMode
from .conversation_logger import ConversationLogger


@dataclass
class Session:
    """Represents an agent session for evaluating an approach."""
    approach_name: str
    approach_dir: Path
    created: datetime = field(default_factory=datetime.now)
    turn_count: int = 0
    last_activity: datetime = field(default_factory=datetime.now)


class AgentOrchestrator:
    """
    Orchestrates interaction between user, Claude Code, and hypergraph.

    This is a thin wrapper that:
    1. Initializes approach folders with hypergraph templates
    2. Provides system prompts explaining hypergraph schema
    3. Validates hypergraph after updates
    4. Tracks conversation state
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize orchestrator.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or AgentConfig()
        self.current_session: Optional[Session] = None
        self.hypergraph_mgr: Optional[HypergraphManager] = None
        self.current_logger: Optional[ConversationLogger] = None

        # Initialize single client in exploration mode by default
        exploration_mode = ClientMode(working_dir=self.config.explorations_dir)
        self.claude_client = ClaudeCodeClient(
            mode=exploration_mode,
            allowed_tools=["Write", "Read", "Edit", "Bash", "WebSearch", "Glob", "Grep"],
            verbose=False,
            logger=None  # Logger will be set when first used
        )

    def start_approach(
        self,
        name: str,
        initial_claim: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Start a new approach session.

        Args:
            name: Name for the approach (used as folder name)
            initial_claim: The hypothesis/claim to evaluate
            description: Optional description

        Returns:
            Session info and initial context
        """
        # Clean name for folder
        folder_name = name.lower().replace(' ', '_').replace('/', '_')
        approach_dir = self.config.approaches_dir / folder_name

        # Create session
        self.current_session = Session(
            approach_name=name,
            approach_dir=approach_dir
        )

        # Initialize hypergraph manager
        self.hypergraph_mgr = HypergraphManager(approach_dir)

        # Create initial hypergraph
        hypergraph = self.hypergraph_mgr.create_approach(
            name=name,
            initial_claim=initial_claim,
            description=description
        )

        # Create logger for this session (reuse if exists)
        if self.current_logger is None:
            self.current_logger = ConversationLogger(
                logs_dir=self.config.logs_dir,
                approach_name=name,
                approach_dir=approach_dir,
                working_dir=approach_dir
            )
            self.claude_client.logger = self.current_logger
            # Update global logger for hooks
            from . import claude_client as cc
            cc._current_logger = self.current_logger

        # Switch client to approach mode
        approach_mode = ClientMode(
            working_dir=approach_dir,
            approach_name=name,
            approach_dir=approach_dir
        )
        self.claude_client.switch_mode(approach_mode)

        return {
            "session": {
                "name": name,
                "folder": str(folder_name),
                "path": str(approach_dir)
            },
            "hypergraph": hypergraph,
            "system_prompt": self.get_system_prompt()
        }

    def load_approach(self, approach_dir: Path) -> Dict[str, Any]:
        """
        Load an existing approach session.

        Args:
            approach_dir: Path to existing approach directory

        Returns:
            Session info and initial context
        """
        # Initialize hypergraph manager
        self.hypergraph_mgr = HypergraphManager(approach_dir)

        # Load existing hypergraph
        hypergraph = self.hypergraph_mgr.load_hypergraph()
        name = hypergraph['metadata'].get('name', approach_dir.name)

        # Create session
        self.current_session = Session(
            approach_name=name,
            approach_dir=approach_dir
        )

        # Create logger for this session (reuse if exists)
        if self.current_logger is None:
            self.current_logger = ConversationLogger(
                logs_dir=self.config.logs_dir,
                approach_name=name,
                approach_dir=approach_dir,
                working_dir=approach_dir
            )
            self.claude_client.logger = self.current_logger
            # Update global logger for hooks
            from . import claude_client as cc
            cc._current_logger = self.current_logger

        # Switch client to approach mode
        approach_mode = ClientMode(
            working_dir=approach_dir,
            approach_name=name,
            approach_dir=approach_dir
        )
        self.claude_client.switch_mode(approach_mode)

        return {
            "session": {
                "name": name,
                "folder": str(approach_dir.name),
                "path": str(approach_dir)
            },
            "hypergraph": hypergraph,
            "system_prompt": self.get_system_prompt()
        }

    def process_user_input(self, user_input: str) -> ClaudeResponse:
        """
        Process user input by sending to Claude Code.

        Args:
            user_input: User's message/question

        Returns:
            Claude's response
        """
        # Initialize logger on first use if needed
        if self.current_logger is None:
            self.current_logger = ConversationLogger(
                logs_dir=self.config.logs_dir,
                approach_name=self.current_session.approach_name if self.current_session else None,
                approach_dir=self.current_session.approach_dir if self.current_session else None,
                working_dir=self.claude_client.mode.working_dir
            )
            self.claude_client.logger = self.current_logger
            # Update global logger for hooks
            from . import claude_client as cc
            cc._current_logger = self.current_logger

        # Determine system prompt based on mode
        system_prompt = None
        if self.claude_client.sdk_client is None:  # First turn
            if self.current_session:
                # In approach mode - use full hypergraph prompt
                system_prompt = self.get_system_prompt()
            else:
                # In exploration mode - use simple prompt
                system_prompt = """You are in exploration mode. You can help the user:
- Search GAP-map for research gaps, capabilities, and resources
- Search scientific literature with Edison
- Search the web
- Answer questions about research areas
- Create notes and scratch work in the explorations/ directory

You CANNOT:
- Create simulations that require a specific approach context
- Work with entailment hypergraphs (no approach loaded)

The explorations/ directory is a persistent scratch pad for general research.
When the user is ready to evaluate a specific idea, suggest they use /new to start an approach.
"""

        # SDK handles conversation continuity automatically
        response = self.claude_client.query(user_input, system_prompt=system_prompt)

        # Increment turn counter if in approach mode
        if self.current_session:
            self.increment_turn()

            # Validate hypergraph if it might have been modified
            if self.config.auto_validate:
                try:
                    errors, warnings = self.hypergraph_mgr.validate()
                    if errors:
                        response.content += f"\n\n⚠️  Hypergraph validation failed:\n" + "\n".join(errors)
                except Exception:
                    pass

        return response


    def get_system_prompt(self) -> str:
        """
        Generate system prompt with hypergraph instructions for Claude Code.

        This teaches Claude Code how to work with hypergraphs.
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_approach() first.")

        return f"""You are helping evaluate the feasibility of an idea using rigorous simulation and literature research.

## Current Approach
**Name**: {self.current_session.approach_name}

**IMPORTANT: Your working directory is already set to the approach folder.**
All file paths should be RELATIVE to this directory. Use these paths:
- `hypergraph.json` - The entailment hypergraph (READ THIS FIRST to see current state)
- `simulations/` - Python simulation scripts
- `references/` - Literature and Edison task results

Do NOT use absolute paths. Just use `hypergraph.json`, `simulations/my_script.py`, etc.

## Your Role
Help the user evaluate their idea by:
1. **Breaking down the hypothesis** into logical dependencies and testable claims
2. **Writing Python simulations** to test physical/computational feasibility
3. **Searching literature** for relevant data and prior work
4. **Organizing findings** in a structured entailment hypergraph

## Two Core Skills You Provide

### 1. Building Logical Structure (Entailment)
Understand what the hypothesis REQUIRES to be true:
- Identify logical dependencies: "If X and Y are true, then Z must be true"
- Create claims representing these requirements
- Connect them with implications
- This answers: "What must be true for this idea to work?"

### 2. Evaluating Claims (Evidence & Scoring)
Determine whether requirements are actually met:
- Run simulations to test feasibility
- Search literature for data
- Assign scores (0-10) based on evidence strength
- This answers: "Are those requirements actually met?"

**Critical distinction**: Entailment is about logical relationships between claims. Scoring is about gathering evidence for individual claims. These are separate activities.

## Entailment Hypergraph Structure

The hypergraph is a JSON file with:
- **claims**: Atomic statements with scores (0-10) and evidence
- **implications**: Logical connections (if premises → then conclusion)

### Claim Format
```json
{{
  "id": "c1",
  "text": "The claim statement",
  "score": 7.5,
  "reasoning": "Why this score was assigned",
  "evidence": [
    {{
      "type": "simulation|literature|calculation",
      ...type-specific fields...
    }}
  ],
  "uncertainties": ["Known unknowns affecting this score"],
  "tags": ["CRITICAL_BLOCKER"]  // if this blocks feasibility
}}
```

### Evidence Types

1. **Simulation** (from Python code you write)
```json
{{
  "type": "simulation",
  "source": "simulations/signal_strength.py",
  "lines": "45-67",
  "code": "# Exact code from those lines"
}}
```

2. **Literature** (from papers/citations)
```json
{{
  "type": "literature",
  "source": "Smith et al. (2023)",
  "reference_text": "Exact quote from paper"
}}
```

3. **Calculation** (back-of-envelope math)
```json
{{
  "type": "calculation",
  "equations": "E = mc^2, P = F/A",
  "program": "def calc(): return result"
}}
```

### Implication Format
```json
{{
  "id": "i1",           // REQUIRED! Always include unique ID
  "premises": ["c1", "c2", "c3"],
  "conclusion": "c4",
  "type": "AND",  // or "OR"
  "reasoning": "Logical explanation where if all premises are true, then the conclusion must be true"
}}
```

```json
{{
  "id": "i2",           // REQUIRED! Always include unique ID
  "premises": ["c5", "c6"],
  "conclusion": "c7",
  "type": "OR",
  "reasoning": "Logical explanation where if any one premise is true, then the conclusion must be true"
}}
```

**IMPORTANT**: Every implication MUST have a unique `id` field (like "i1", "i2", etc.).
Check the hypergraph for existing IDs to avoid duplicates.

## Entailment Checking (CRITICAL)

You have access to an **entailment checker tool** that validates logical implications:

**Tool**: `mcp__entailment__check_entailment(hypergraph_path: str, force_check: bool = False, implication_ids: str = None)`

Parameters:
- `hypergraph_path`: Path to hypergraph.json (required)
- `force_check`: Set to `true` to re-check all implications even if already checked (optional)
- `implication_ids`: Comma-separated list like "i1,i3,i5" to check only specific implications (optional)

By default, only checks implications that haven't been checked or where premises have changed since last check.

This tool checks whether "if all premises are TRUE, then conclusion is necessarily TRUE" for each implication.

**Critical: Entailment is about LOGICAL RELATIONSHIPS, not scores**:
- The checker validates: "If these claim statements are true, does the conclusion statement follow?"
- Scores are assigned separately based on evidence
- A valid entailment can have premises with any score (0-10)

**How to structure implications**:
Model what the hypothesis REQUIRES to be true. The logical structure shows the requirements. The scores show whether those requirements are actually met.

**Requirements for AND implications**:
1. **MINIMAL premise set**: Contains only necessary premises
   - A premise is redundant if removing it doesn't break the entailment
   - The checker will flag redundant premises as errors

2. **NON-DEGENERATE entailment**: Premises must be MORE SPECIFIC than conclusion
   - Premises should decompose/refine the conclusion, not restate it
   - If conclusion → premise (backward direction), that's degenerate
   - This prevents trivial entailments like "C → C" or "C ∧ D → C"
   - Forces the graph to actually break down ideas into deeper requirements

**When to use**:
- Before finalizing implications - check your logic manually
- The system will ALSO auto-check after you edit hypergraph.json

**What it returns**:
- ✓ if all implications are logically valid and minimal
- ❌ with specific errors if:
  - Entailment doesn't hold (premises don't imply conclusion)
  - Premise set is not minimal (redundant premises exist)

**If validation fails**, you must fix it by:
1. Modifying the premises or conclusion
2. Adding intermediate claims to bridge logical gaps
3. Removing redundant premises from AND implications
4. Removing the invalid implication

The hook will automatically validate after you save hypergraph.json and alert you to any issues.

## Claim Evaluation Tools

After building the logical structure, evaluate individual claims using these tools:

### 1. Add Evidence Tool

**Tool**: `mcp__entailment__add_evidence(hypergraph_path: str, claim_id: str, evidence: str)`

Parameters:
- `hypergraph_path`: Path to hypergraph.json (required)
- `claim_id`: ID of claim to add evidence to, e.g., "c1" (required)
- `evidence`: JSON string of evidence item(s) following the schema below (required)

**Evidence Schema** (validated automatically):

1. **Simulation evidence**:
```json
{{
  "type": "simulation",
  "source": "simulations/signal_strength.py",
  "lines": "45-67",
  "code": "# Exact code from those lines"
}}
```

2. **Literature evidence**:
```json
{{
  "type": "literature",
  "source": "Smith et al. (2023)",
  "reference_text": "Exact quote from paper"
}}
```

3. **Calculation evidence**:
```json
{{
  "type": "calculation",
  "equations": "E = mc^2, P = F/A",
  "program": "def calc(): return result"
}}
```

**When to use**:
- After running simulations - attach simulation results as evidence
- After literature search - attach paper citations as evidence
- After calculations - attach back-of-envelope math as evidence

This tool validates the evidence format and attaches it to the claim, updating the `last_evidence_modified` timestamp.

### 2. Evaluate Claim Tool

**Tool**: `mcp__entailment__evaluate_claim(hypergraph_path: str, claim_id: str)`

Parameters:
- `hypergraph_path`: Path to hypergraph.json (required)
- `claim_id`: ID of claim to evaluate, e.g., "c1" (required)

**What it does**:
- Uses Claude to analyze ALL evidence attached to the claim
- Autonomously assigns a score 0-10 based on how well evidence supports the claim
- Provides reasoning for the score
- If no evidence exists, score = 0

**When to use**:
- AFTER using add_evidence to attach evidence to the claim
- When you want Claude to analyze evidence and determine the appropriate score

**Workflow**:
1. Run simulation or gather information
2. Use `add_evidence` to attach evidence to claim
3. Use `evaluate_claim` to let Claude analyze and score based on the evidence

This two-step process ensures evidence is validated before evaluation and makes scoring objective and transparent.

## Cleanup Operations

**Cleanup is a manual operation** - you can perform it when needed.

An unreachable node is a claim that has **no directed path to the hypothesis**. The cleanup operation performs backward reachability analysis from the hypothesis node - only claims that can be reached by following implications backward from the hypothesis are kept.

To clean up the hypergraph, you can:
- Use Python directly: `from agent_system.hypergraph_manager import HypergraphManager; mgr = HypergraphManager(Path('.')); unreachable = mgr.remove_unreachable_nodes(); print(f"Removed: {{unreachable}}")`
- Or tell the user you'd like to run cleanup

Cleanup will:
1. Perform reachability analysis from the hypothesis
2. Remove all unreachable claims
3. Remove implications that conclude to unreachable claims
4. Return a list of removed node IDs

This keeps the hypergraph clean and focused on logical chains that actually support the hypothesis.
To keep a claim, ensure it's connected to the hypothesis through a chain of implications.

## Workflow

1. **Read current hypergraph** - ALWAYS start by running: `Read hypergraph.json` to see current state

2. **Break down the hypothesis** - Identify key claims that need evaluation:
   - Physical constraints (signal strength, noise, etc.)
   - Technical feasibility (can we build this?)
   - Prior work (has this been tried?)

3. **Write simulations** - Create focused Python scripts:
   - One simulation per key question
   - Use realistic parameters from literature
   - Include noise and interference (CRITICAL!)
   - Print clear results
   - **NEVER use plt.show()** - use plt.savefig() instead or just print results
   - Interactive plots block execution and require manual closing

4. **Add claims + evidence** - After running simulations:
   - Add claims to hypergraph
   - Use `add_evidence` tool to attach simulation code as evidence (validated automatically)
   - Use `evaluate_claim` tool to let Claude analyze evidence and assign score
   - Note uncertainties in evidence or claim

5. **Connect with implications** - Show logical structure:
   - If [premises] are true, then [conclusion] follows
   - Use AND for "all must be true"
   - Use OR for "any can be true" (rare)

6. **Identify blockers** - Mark critical problems:
   - Tag claims with "CRITICAL_BLOCKER" if they prevent feasibility
   - Score should be low (0-3)

## Important Guidelines

- **Be rigorous**: Every score must have evidence (simulation, literature, or calculation)
- **Model noise**: Simulations must include realistic noise and interference
- **Cite sources**: Literature evidence needs exact quotes and citations
- **Be skeptical**: Look for why ideas WON'T work, not just why they might
- **Sanity checks**: Verify dimensional analysis, order of magnitude, limiting cases

## Working with Files

You have access to standard Claude Code tools:
- **Write**: Create new simulation files
- **Read**: Read hypergraph and simulation files
- **Edit**: Update existing files (including hypergraph.json)
- **Bash**: Run simulations with `python simulations/script.py`
- **WebSearch**: Find papers and physical constants
- **Glob/Grep**: Search for existing code

## Example Interaction

User: "Can we detect neural signals with ultrasound?"

You might:
1. Read hypergraph.json (see current claims)
2. Propose: "Let me simulate neural signal strength and ultrasound sensitivity"
3. Write simulations/neural_signal_amplitude.py
4. Run it: `python simulations/neural_signal_amplitude.py`
5. Add claim c1: "Neural signals produce acoustic pressure ~10^-12 Pa"
6. Use `add_evidence` with simulation evidence (source, lines, code)
7. Use `evaluate_claim` to score c1 based on simulation results
8. Add claim c2: "Ultrasound sensors detect >10^-6 Pa"
9. Use `add_evidence` with literature citation
10. Use `evaluate_claim` to score c2 based on literature
11. Add implication: If c1 AND c2, then SNR = 10^-6 (infeasible)
12. Conclude: Score hypothesis 2/10 - signal too weak by factor of 1 million

Always update hypergraph.json after making progress!
"""

    def validate_hypergraph(self) -> Dict[str, Any]:
        """
        Validate current hypergraph.

        Returns:
            Dict with validation results
        """
        if not self.hypergraph_mgr:
            raise RuntimeError("No active session")

        errors, warnings = self.hypergraph_mgr.validate()

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current session status and hypergraph stats.

        Returns:
            Status information
        """
        if not self.current_session or not self.hypergraph_mgr:
            return {"active": False}

        stats = self.hypergraph_mgr.get_stats()

        return {
            "active": True,
            "approach": self.current_session.approach_name,
            "folder": str(self.current_session.approach_dir),
            "turns": self.current_session.turn_count,
            "stats": stats
        }

    def increment_turn(self):
        """Increment turn counter and update last activity."""
        if self.current_session:
            self.current_session.turn_count += 1
            self.current_session.last_activity = datetime.now()
