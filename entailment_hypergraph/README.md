# Entailment Hypergraph System

A more formal, mathematically rigorous approach to modeling entailments using **hypergraphs**.

## Key Concepts

### Atomic Claims (Nodes)
Individual statements that can be true or false. Each claim has:
- **ID**: Unique identifier (e.g., `c1`, `c2`)
- **Text**: The claim statement
- **Score**: 0-10 confidence/truth value
- **Evidence**: What supports this claim

### Implications (Hyperedges)
Logical rules connecting claims: **If premises P₁, P₂, ..., Pₙ are true, then conclusion C is true**

Represented as: `((P₁, P₂, ..., Pₙ), C)`

## Differences from Tree Structure

| Tree Approach | Hypergraph Approach |
|---------------|---------------------|
| Hierarchical parent-child relationships | Network of atomic claims + implications |
| Each node can have one parent | Claims can participate in multiple implications |
| Hypothesis includes conclusion | Hypothesis is a separate atomic claim |
| Structure is rigid | Structure is flexible, compositional |
| Good for linear reasoning | Good for complex logical dependencies |

## JSON Structure

```json
{
  "metadata": {
    "name": "Example Name",
    "description": "...",
    "created": "YYYY-MM-DD"
  },
  "claims": [
    {
      "id": "c1",
      "text": "The claim statement",
      "score": 10,
      "evidence_type": "simulation|literature|calculation",
      "reasoning": "Why this score"
    }
  ],
  "implications": [
    {
      "id": "i1",
      "premises": ["c1", "c2"],
      "conclusion": "c3",
      "type": "AND",
      "reasoning": "Logical connection explanation"
    }
  ]
}
```

## Advantages

1. **Reusability**: Same atomic claim can be used in multiple implications
2. **Compositionality**: Build complex arguments from simple claims
3. **Graph analysis**: Can use standard graph algorithms (paths, cycles, etc.)
4. **Modularity**: Add/remove implications without restructuring entire tree
5. **Multiple derivations**: A claim can be derived in multiple ways (multiple hyperedges pointing to it)

## Example: Water Boiling

**Atomic Claims:**
- c1: "Liquid water can be heated to 100°C"
- c2: "Water boils at 100°C (standard pressure)"
- c3: "Water transitions to gas at boiling point"
- c4: "Heating water to 100°C will make it turn to gas"

**Implication:**
- i1: `((c1, c2, c3), c4)` - If we can heat water to 100°C, and that's the boiling point, and water becomes gas at boiling point, then heating to 100°C produces gas

## Visualization

Open `index.html` in a browser (serve from parent directory):

```bash
cd ai-simulations/
python -m http.server 8765
# Visit: http://localhost:8765/entailment_hypergraph/
```

### Features:
- **True hypergraph visualization** - premises merge at junction nodes
- **Claim text on nodes** - see what each claim says directly on the graph
- **Smart text wrapping** - multi-line text automatically wraps to fit in circles
- **Smooth flowing curves** - cubic bezier paths that blend naturally into junctions
- **Scales beautifully** - handles any number of premises with automatic spacing
- **Subtle glow effects** - edges have soft blur for smooth visual blending
- **Junction nodes** (blue circles with ∧) represent AND operations
- **Color-coded claims** by score (green=high, yellow=medium, red=low)
- **Visual edge types**:
  - Gray curved edges: premises → junction (with perpendicular spread)
  - Thick blue arrow: junction → conclusion (gentle arc)
- **Interactive**:
  - **Expand/Collapse** - click conclusion nodes (with +/− indicator) to show/hide their premise subgraphs
    - Collapsing recursively hides all nested premises
    - Expanding shows immediate premises only
    - View the argument at multiple levels of resolution
  - **Full Text toggle** - switch between compact (truncated) and full text display
  - Hover over nodes to see full text and claim ID
  - Click non-conclusion claims to highlight connections
  - Drag nodes to rearrange
  - Mouse wheel to zoom in/out
  - Click and drag background to pan
  - Zoom buttons for precise control
- **Side panels** show full claim text and implication details
- **Toggle physics** to freeze/unfreeze layout

## Use Cases

This hypergraph approach is better when:
- Multiple independent paths to the same conclusion
- Want to reuse atomic claims across different arguments
- Need to model "if-then" reasoning explicitly
- Want to apply graph-theoretic analysis
- Building a knowledge base of reusable claims

The tree approach is better when:
- Linear hierarchical reasoning
- Clear parent-child decomposition
- Simpler visualization needs
- Each claim is unique to its position in the argument

## Future Extensions

- **Score propagation**: Automatically compute conclusion scores from premises
- **Cycle detection**: Identify circular reasoning
- **Path analysis**: Find all ways to derive a conclusion
- **Claim library**: Reusable database of atomic claims
- **Multiple example types**: Beyond just water boiling
