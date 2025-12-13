# Claude Guidelines for AI Simulations Project

## Purpose
This project tests Claude's ability to generate simulations of potential neural recording devices to evaluate their feasibility from first principles.

## Core Principles

### 1. Clarity and Truth
These are the most important values for all work in this project.

**Documentation Requirements:**
- Every simulation must have a document describing:
  - The implementation idea
  - ALL assumptions made
  - How assumptions connect to implementation details
  - Things I do not know, with ideas for how to obtain that information if possible

**Entailment Trees:**
Every approach must have an entailment tree to make feasibility assessment rigorous and transparent.

*What is an Entailment Tree?*
- A hierarchical tree of claims where: if all child claims are true, then the parent claim is true
- Each node has a score from 0 (False) to 10 (True), with 5 = Unsure
- Scores come from simulations, literature, physical laws, or reasoning

*Structure:*
```
┌─────────────────────────────────────────────┐
│          HYPOTHESIS (top claim)              │
│     Score: X | Evidence: [source]           │
└─────────────────────────────────────────────┘
                    ▲
                    │
          ┌─────────┴─────────┐
          │    ENTAILMENT     │
          │    (AND/OR)       │
          └─────────┬─────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───┴────┐    ┌────┴────┐    ┌────┴────┐
│PREMISE1│    │PREMISE2 │    │PREMISE3 │
│Score: X│    │Score: Y │    │Score: Z │
│Evidence│    │Evidence │    │Evidence │
└────────┘    └─────────┘    └─────────┘
```

*Score Propagation:*
- **AND relationship**: Combined score = sum_i(-log(score_i/10)) + entailment_penalty
  - All premises must be true for parent to be true
  - Lower combined score = better (less uncertainty)
- **OR relationship**: Combined score = min_i(-log(score_i/10)) + entailment_penalty
  - Any premise being true makes parent true (best premise wins)
  - Generally prefer separate trees for different approaches rather than OR nodes
- **Entailment validity**: The logical connection itself must be valid for truth to propagate
  - `entailment_status: 'passed'` or not yet checked → entailment_penalty = 0
  - `entailment_status: 'failed'` → entailment_penalty = +Infinity (truth cannot propagate through invalid logic)

*Documentation for Each Node:*
- Score value (0-10)
- Evidence source (simulation file:line, literature citation, physical law)
- Reasoning for why this score was assigned
- Uncertainties or assumptions affecting the score

*Workflow Integration:*
- Create initial tree BEFORE simulation (planning phase)
- Update scores as evidence accumulates from simulations/research
- Trees can be deeply nested - premises can have their own sub-premises
- No depth limit - capture all logical dependencies

*File Organization:*
- One `entailment_tree.json` file per approach folder (machine-readable format)
- Optional: `entailment_tree.md` for human-readable visualization
- Update throughout the investigation as understanding evolves

*JSON Structure:*
Each entailment tree should be a structured JSON with:
- `metadata`: Approach name, dates, version, description
- `tree`: Hierarchical node structure with:
  - `id`: Unique identifier for each node (required)
  - `claim`: The claim being evaluated (required)
  - `score`: 0-10 numerical score (required)
  - `combined_score`: Calculated from children using propagation formula (auto-computed)
  - `evidence`: Array of evidence items (required if leaf node)
    - `type`: Must be "simulation", "literature", or "calculation"
    - `source`: File path or citation reference
    - `lines`: Line numbers if applicable
    - `description`: What this evidence shows
  - `reasoning`: Why this score was assigned (required)
  - `uncertainties`: List of known unknowns affecting the score
  - `tags`: Optional tags like ["CRITICAL_BLOCKER"]
  - `children_relationship`: "AND" or "OR" (required if has children)
  - `children`: Array of child nodes
- `alternative_hypotheses`: Variants with different assumptions
- `critical_unknowns`: Highest-priority information gaps
- `conclusions`: Summary and verdicts

*Allowed Evidence Types (ONLY):*
- `literature` - Papers, citations, published data, standards, guidelines
  - Required fields: `type`, `source` (file or citation), `reference_text` (exact quote)
  - Type checker verifies `reference_text` matches source file if `lines` field present
- `simulation` - Results from simulation code
  - Required fields: `type`, `source` (script path), `lines` (line numbers, e.g., "145-170"), `code` (extracted code)
  - Type checker verifies `code` matches source file at specified lines
- `calculation` - Back-of-envelope math, analytical estimates
  - Required fields: `type`, `equations` (LaTeX formulas), `program` (Python function)

*Type Checking:*
Use `python typecheck_tree.py <file>` to validate structure and types.

This structure enables:
- Automated type checking and validation
- Automated score calculations
- Programmatic tree manipulation and updates
- Multiple visualization formats from single source
- Easy comparison between approaches

**Central Focus: Noise and Interference**
- Understanding how noise and the interference of many factors together is the CORE of whether ideas work
- Incorporating noise and interference into simulations is THE central goal
- Every simulation must rigorously model these real-world complexities

**Sanity Checks:**
Before accepting any simulation result, verify the following. When a check fails → investigate before proceeding.

*Physical Sanity:*
1. **Dimensional Analysis** - All equations must have consistent units. Check every term.
2. **Order of Magnitude** - Results within ~10x of related systems or literature values
3. **Limiting Cases** - Model behaves correctly when parameters → 0 or → ∞
4. **Physical Realizability** - All parameters within achievable ranges (cite safety limits, tech limits)
5. **Conservation Laws** - Energy/charge/mass conserved unless explicitly dissipated
6. **Sign Checks** - Are positive/negative values physically meaningful? (e.g., PSD cannot be negative)
7. **Noise Floors** - Compare signals to fundamental limits (thermal noise: ~4kT·R·Δf, shot noise)

*Computational Sanity:*
8. **Numerical Stability** - No NaN/Inf in results; check filter stability (poles inside unit circle)
9. **Sampling Theorem** - Sample rate ≥ 2× highest frequency of interest (avoid aliasing)
10. **Resolution vs Precision** - Is numerical precision sufficient for the signal levels involved?

*Model Validity:*
11. **Assumption Traceability** - Every assumption traces to literature citation OR marked "Unknown"
12. **Parameter Ranges** - All inputs physically/practically achievable with citations
13. **Symmetry Checks** - Model respects physical symmetries (time-reversal, spatial)
14. **Back-of-Envelope** - Can you estimate the answer within an order of magnitude with simple math?

*Results Interpretation:*
15. **SNR Reality Check** - Compare SNR to what's achievable in similar measurement systems
16. **Plausibility Testing** - If this worked easily, why hasn't it been done? What barriers exist?
17. **Error Propagation** - If key parameter has ±X% uncertainty, how does it affect conclusions?

Document any assumptions that cannot be validated. Clearly mark critical unknowns.

### 2. Organization
Critical for understanding and maintaining the work.

**Code Quality:**
- All code must be well-written
- Always follow the KISS principle (Keep It Simple, Stupid)
- Prefer clarity over cleverness

**Project Structure:**
- Each sufficiently distinct approach goes in a separate folder
- Each folder must contain:
  - README describing the idea and implementation interpretation
  - `entailment_tree.md` with the feasibility logic and scoring
  - Simulations of varying resolution in separate scripts OR distinct cells in Jupyter notebooks

### 3. Responsibility
Given the latitude provided in this project:

**Safety First:**
- Never do anything to harm the computer or the user
- Keep every additional thing within the environment we create
- No external dependencies or actions that could compromise system integrity



## Workflow
1. Understand the neural recording concept
2. Document assumptions and unknowns
3. Create initial entailment tree with hypothesis and premises (initial scores can be marked as TBD)
4. Design simulation with noise/interference as primary consideration
5. Implement following organizational structure
6. Test and validate
7. Update entailment tree with scores based on simulation results and literature
8. Document results and learnings

IMPORTANT! At the end, I want:
- A simulation that clearly establishes how the different parameters and assumptions interact to determine feasibility
- A complete entailment tree showing the logical structure and evidence-based scoring of the approach
