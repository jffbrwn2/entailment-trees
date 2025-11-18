# Entailment Trees - Quick Reference

## What Are Entailment Trees?

Entailment trees are structured logical representations where:
- Parent claims are TRUE if and only if all child claims are TRUE (for AND relationships)
- Each node has a score from 0 (False) to 10 (True), with 5 = Unsure
- Scores are based on simulations, literature, physical laws, or reasoning
- Combined scores propagate from children to parents using information-theoretic formulas

## File Structure

Each simulation approach has:
- `entailment_tree.json` - Machine-readable structured data
- `entailment_tree.md` (optional) - Human-readable visualization

## Using the Tools

### Basic Commands

```bash
# Type check: Validate structure and types (RECOMMENDED FIRST STEP)
python typecheck_tree.py <json_file>

# Validate tree structure (uses type checker internally)
python entailment_tree_tools.py validate <json_file>

# Generate summary report
python entailment_tree_tools.py summary <json_file>

# Display tree visualization
python entailment_tree_tools.py tree <json_file>

# Find critical blockers (low-scoring nodes)
python entailment_tree_tools.py blockers <json_file>

# Recalculate all combined scores
python entailment_tree_tools.py recalculate <json_file>

# Compare multiple approaches
python entailment_tree_tools.py compare <json1> <json2> ...
```

### Example Usage

```bash
# Check if your tree is valid
python entailment_tree_tools.py validate ultrasound_eeg_enhancement/entailment_tree.json

# Get a quick summary
python entailment_tree_tools.py summary ultrasound_eeg_enhancement/entailment_tree.json

# Identify what's blocking feasibility
python entailment_tree_tools.py blockers ultrasound_eeg_enhancement/entailment_tree.json
```

## Score Propagation Formulas

### AND Relationship (all children must be true)
```
combined_score = sum_i(-log₁₀(score_i/10))
```
- Lower combined score = better (less uncertainty)
- Example: scores [8, 9, 7] → -log(0.8) + -log(0.9) + -log(0.7) = 0.223 + 0.105 + 0.357 = 0.685

### OR Relationship (any child can be true)
```
combined_score = max_i(-log₁₀(score_i/10))
```
- Best child determines the score
- Example: scores [3, 7, 5] → max(-log(0.3), -log(0.7), -log(0.5)) = 0.523

## JSON Schema (Simplified)

```json
{
  "metadata": {
    "approach": "Name of approach",
    "created": "YYYY-MM-DD",
    "last_updated": "YYYY-MM-DD",
    "version": "1.0"
  },
  "tree": {
    "id": "unique_id",
    "claim": "The claim being evaluated",
    "score": 0-10,
    "combined_score": calculated,
    "evidence": [
      {
        "type": "simulation|literature|calculation",
        "source": "file_path or citation",
        "lines": "line_numbers (optional)",
        "description": "what this evidence shows"
      }
    ],
    "reasoning": "Why this score was assigned",
    "uncertainties": ["list of unknowns"],
    "tags": ["CRITICAL_BLOCKER"],
    "children_relationship": "AND|OR",
    "children": [...]
  },
  "alternative_hypotheses": [...],
  "critical_unknowns": [...],
  "conclusions": {...}
}
```

### Key Simplifications
- **No `type` field on nodes** - Tree structure shows hierarchy
- **Only 3 evidence types** - `simulation`, `literature`, `calculation`
- **Type checked** - Use `typecheck_tree.py` to validate

### Type Checker Validates:
- Required fields exist with correct types
- Scores are in range [0, 10]
- Evidence types are allowed values only
- No duplicate node IDs
- Proper children/relationship structure
- Valid JSON syntax

## Workflow

### 1. Initial Tree (Before Simulation)
- Create hypothesis and main premises
- Identify what needs to be proven
- Mark scores as TBD or give initial estimates
- Document assumptions and uncertainties

### 2. During Simulation
- Update scores as evidence accumulates
- Add new sub-premises as understanding deepens
- Document evidence sources (file:line)
- Note critical unknowns discovered

### 3. After Simulation
- Finalize all scores with evidence
- Calculate combined scores: `python entailment_tree_tools.py recalculate`
- Generate summary: `python entailment_tree_tools.py summary`
- Document conclusions and next steps

## Interpreting Scores

| Score | Meaning | When to Use |
|-------|---------|-------------|
| 9-10 | Well-established | Multiple citations, physical laws |
| 7-8 | Likely true | Literature support, simulation confirms |
| 5-6 | Uncertain | Limited data, assumptions required |
| 3-4 | Unlikely | Evidence suggests problems |
| 0-2 | False/Infeasible | Clear evidence against |

## Tips

1. **Be specific**: "Signal exceeds noise by 10 dB" not "Signal is strong"
2. **Link evidence**: Always include file:line or citation
3. **Document reasoning**: Why did you assign this score?
4. **Mark blockers**: Tag critical issues with `"tags": ["CRITICAL_BLOCKER"]`
5. **Use sub-premises**: Break complex claims into logical components
6. **Update iteratively**: Tree evolves as you learn

## Example: Finding What's Wrong

```bash
# Quick check: Is my idea feasible?
python entailment_tree_tools.py summary my_approach/entailment_tree.json

# If score is low, find the blockers:
python entailment_tree_tools.py blockers my_approach/entailment_tree.json

# Examine the tree structure:
python entailment_tree_tools.py tree my_approach/entailment_tree.json
```

This immediately shows which specific assumptions are failing and why!
