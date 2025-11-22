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
from .claude_client import ClaudeCodeClient, ClaudeResponse


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
        self.claude_client: Optional[ClaudeCodeClient] = None

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

        # Initialize Claude Code client with approach directory as working dir
        self.claude_client = ClaudeCodeClient(
            working_dir=approach_dir,
            allowed_tools=["Write", "Read", "Edit", "Bash", "WebSearch", "Glob", "Grep"],
            verbose=False
        )

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

        # Initialize Claude Code client with approach directory as working dir
        self.claude_client = ClaudeCodeClient(
            working_dir=approach_dir,
            allowed_tools=["Write", "Read", "Edit", "Bash", "WebSearch", "Glob", "Grep"],
            verbose=False
        )

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

        Raises:
            RuntimeError: If no active session
        """
        if not self.current_session or not self.claude_client:
            raise RuntimeError("No active session. Call start_approach() first.")

        # First turn - start conversation with system prompt
        if self.current_session.turn_count == 0:
            response = self.claude_client.start_conversation(
                initial_prompt=user_input,
                system_prompt=self.get_system_prompt()
            )
        else:
            # Continue existing conversation
            response = self.claude_client.continue_conversation(user_input)

        # Increment turn counter
        self.increment_turn()

        # Validate hypergraph if it might have been modified
        # (Claude might have edited hypergraph.json)
        if self.config.auto_validate:
            try:
                errors, warnings = self.hypergraph_mgr.validate()
                if errors:
                    # Append validation errors to response
                    response.content += f"\n\n⚠️  Hypergraph validation failed:\n" + "\n".join(errors)
            except Exception:
                pass  # Validation might fail if hypergraph doesn't exist yet

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
**Folder**: {self.current_session.approach_dir}
**Hypergraph**: {self.current_session.approach_dir}/hypergraph.json
**Simulations**: {self.current_session.approach_dir}/simulations/

## Your Role
Help the user evaluate their idea by:
1. Breaking the hypothesis into testable claims
2. Writing Python simulations to test physical/computational feasibility
3. Searching literature for relevant data and prior work
4. Organizing findings in a structured **entailment hypergraph**

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
  "reasoning": "Logical explanation"
}}
```

**IMPORTANT**: Every implication MUST have a unique `id` field (like "i1", "i2", etc.).
Check the hypergraph for existing IDs to avoid duplicates.

## Entailment Checking (CRITICAL)

You have access to an **entailment checker tool** that validates logical implications:

**Tool**: `mcp__entailment__check_entailment(hypergraph_path: str)`

This tool checks whether "if all premises are true, then conclusion is true" for each implication.

**Minimality Requirement for AND implications**:
- Premise sets must be **MINIMAL** - containing only necessary premises
- A premise is redundant if removing it doesn't break the entailment
- The checker will flag any redundant premises as errors

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

## Automatic Cleanup

**Unreachable nodes are automatically removed** after your turn completes.

An unreachable node is a claim that has **no directed path to the hypothesis**. The system performs backward reachability analysis from the hypothesis node - only claims that can be reached by following implications backward from the hypothesis are kept.

When your turn completes, the system will:
1. Perform reachability analysis from the hypothesis
2. Remove all unreachable claims
3. Print which nodes were removed
4. Validate remaining implications

This keeps the hypergraph clean and focused on logical chains that actually support the hypothesis.
To keep a claim, ensure it's connected to the hypothesis through a chain of implications.

## Workflow

1. **Read current hypergraph** - Always start by reading hypergraph.json to see current state

2. **Break down the hypothesis** - Identify key claims that need evaluation:
   - Physical constraints (signal strength, noise, etc.)
   - Technical feasibility (can we build this?)
   - Prior work (has this been tried?)

3. **Write simulations** - Create focused Python scripts:
   - One simulation per key question
   - Use realistic parameters from literature
   - Include noise and interference (CRITICAL!)
   - Print clear results

4. **Add claims + evidence** - After running simulations:
   - Add claims to hypergraph
   - Link simulation code as evidence
   - Score claims based on results (0=false, 10=true, 5=unsure)
   - Note uncertainties

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
6. Add evidence: simulation result with code excerpt
7. Add claim c2: "Ultrasound sensors detect >10^-6 Pa"
8. Add implication: If c1 AND c2, then SNR = 10^-6 (infeasible)
9. Conclude: Score hypothesis 2/10 - signal too weak by factor of 1 million

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
