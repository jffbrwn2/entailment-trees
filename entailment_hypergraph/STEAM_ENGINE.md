# Steam Engine Feasibility Hypergraph

A multi-level entailment hypergraph demonstrating how fundamental physical principles combine to justify the feasibility of steam-powered engines.

## Structure Overview

### Level 1: Fundamental Physical Claims
**Basic thermodynamics and mechanics:**
- c1: Water can be heated to 100°C
- c2: Water at 100°C produces steam
- c3: Steam expands when heated
- c4: Expanding gas creates pressure
- c5: Pressure creates force (F = P × A)
- c6: Force can do work
- c7: Linear motion → rotational motion (crankshaft)
- c8: Materials can withstand steam pressure/temperature
- c9: Seals can contain pressurized steam

### Level 2: Intermediate Conclusions
**Combining basic principles:**
- **intermediate_1**: "Steam can be reliably produced from water"
  - From: c1 ∧ c2

- **intermediate_2**: "Confined steam creates usable pressure"
  - From: c3 ∧ c4

- **intermediate_3**: "Pressure can perform mechanical work"
  - From: c5 ∧ c6

### Level 3: Higher-Level Integration
- **intermediate_4**: "Steam pressure can produce controlled mechanical motion"
  - From: intermediate_1 ∧ intermediate_2 ∧ intermediate_3

### Level 4: Final Conclusion
- **conclusion**: "A steam-powered engine is physically feasible and can be constructed"
  - From: intermediate_4 ∧ c7 ∧ c8 ∧ c9

## Hypergraph Structure

```
            c1 ───┐
                  ├──→ ∧ ──→ intermediate_1 ──┐
            c2 ───┘                            │
                                               │
            c3 ───┐                            │
                  ├──→ ∧ ──→ intermediate_2 ───┤
            c4 ───┘                            │
                                               ├──→ ∧ ──→ intermediate_4 ──┐
            c5 ───┐                            │                            │
                  ├──→ ∧ ──→ intermediate_3 ───┘                            │
            c6 ───┘                                                         │
                                                                            │
            c7 ────────────────────────────────────────────────────────────┤
            c8 ────────────────────────────────────────────────────────────┼──→ ∧ ──→ conclusion
            c9 ────────────────────────────────────────────────────────────┘
```

## Key Features

### Multi-Level Reasoning
Unlike the simple water boiling example, this demonstrates:
- **Hierarchical composition**: Basic claims → intermediate conclusions → final conclusion
- **Multiple junction points**: 5 different AND operations
- **Scalability**: Shows how complex arguments can be built from simple premises

### Scores
- **Fundamental claims (c1-c7)**: All score 10/10 - well-established physics
- **Material constraints (c8-c9)**: Slightly lower (9/10, 8/10) - practical engineering challenges
- **Final conclusion**: 9.5/10 - feasible but with practical implementation challenges

### Why This Structure Matters

1. **Modularity**: Each intermediate claim can be challenged or verified independently
2. **Transparency**: Clear logical flow from principles to conclusion
3. **Reusability**: Intermediate claims (like "pressure can do work") can be used in other arguments
4. **Testability**: Each junction represents a testable logical connection

## Interactive Visualization

Visit the visualizer and select "Steam Engine Feasibility (Complex)" from the dropdown:

```bash
http://localhost:8765/entailment_hypergraph/
```

You'll see:
- **9 green bubbles** (fundamental claims - all highly confident)
- **4 intermediate nodes** (derived conclusions)
- **5 blue junctions** (AND operations)
- **Smooth flowing curves** connecting everything
- **Multiple levels** of reasoning depth

**Try the expand/collapse feature!**
- Click on the **conclusion** node (top-level claim) - it has a **−** indicator
- Watch as all 13 supporting nodes collapse recursively
- Click again (+) to expand and see just the intermediate nodes
- Click on intermediate nodes to drill down into specific reasoning branches
- View the argument at different levels of detail!

Drag nodes around to see the structure! The intermediate nodes act as "stepping stones" from fundamental physics to the engineering conclusion.

## Comparison to Water Boiling Example

| Aspect | Water Boiling | Steam Engine |
|--------|---------------|--------------|
| Nodes | 4 claims | 14 claims (9 basic + 4 intermediate + 1 conclusion) |
| Junctions | 1 AND operation | 5 AND operations |
| Levels | 1 level | 4 levels deep |
| Complexity | Simple direct proof | Multi-stage hierarchical reasoning |
| Purpose | Demonstrate structure | Demonstrate scalability |

## Applications

This structure shows how to model:
- **Engineering feasibility**: Breaking down "can we build X?" into testable components
- **Technology assessment**: Evaluating if fundamental principles support a technology
- **Hierarchical reasoning**: Building complex conclusions from simple premises
- **Assumption tracking**: Each node's score tracks confidence at that level

The steam engine scored 9.5/10 - historically accurate! It was feasible and was built, though with practical challenges in efficiency and sealing.
