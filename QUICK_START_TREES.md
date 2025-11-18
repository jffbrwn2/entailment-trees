# Entailment Trees - Quick Start

## What We Built

**Simplified, type-safe entailment trees for evaluating simulation feasibility.**

## The Simplifications

1. ✓ **Removed node `type` field** - Tree structure shows hierarchy naturally
2. ✓ **Only 3 evidence types** - `simulation`, `literature`, `calculation`
3. ✓ **Strong type checking** - Catches errors before they cause problems

## Essential Commands

```bash
# Always start here - validate your tree
python typecheck_tree.py <json_file>

# Quick feasibility check
python entailment_tree_tools.py summary <json_file>

# Find what's blocking feasibility
python entailment_tree_tools.py blockers <json_file>

# Visualize the tree structure
python entailment_tree_tools.py tree <json_file>
```

## Required Node Fields

```json
{
  "id": "unique_identifier",
  "claim": "What needs to be true",
  "score": 0-10,
  "evidence": [
    {
      "type": "simulation|literature|calculation",
      "source": "file.py or paper citation",
      "description": "what this proves"
    }
  ],
  "reasoning": "Why this score",
  "children_relationship": "AND|OR",  // if has children
  "children": []
}
```

## Type Checker Validates

- ✓ All required fields present
- ✓ Scores in range [0, 10]
- ✓ Evidence types are valid
- ✓ No duplicate IDs
- ✓ Valid JSON syntax
- ✓ Proper tree structure

## Example Workflow

```bash
# 1. Create initial tree (before simulation)
# Fill in TBD scores, document assumptions

# 2. Type check it
python typecheck_tree.py my_approach/entailment_tree.json

# 3. Run simulations, update scores with evidence

# 4. Check feasibility
python entailment_tree_tools.py summary my_approach/entailment_tree.json

# 5. If low score, find blockers
python entailment_tree_tools.py blockers my_approach/entailment_tree.json
```

## The Point

**Instant, rigorous answer to: "Will this idea work and why/why not?"**

No hand-waving. Every claim has:
- A score backed by evidence
- Links to simulation/literature/calculation
- Clear reasoning
- Documented uncertainties

The type checker ensures you can't cheat - evidence types are restricted, scores must be justified, structure must be valid.
