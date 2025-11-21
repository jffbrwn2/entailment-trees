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

## JSON Structure

```json
{
  "metadata": {
    "name": "Example Name",
    "description": "...",
    "created": "YYYY-MM-DD",
    "last_updated": "YYYY-MM-DD",
    "version": "1.0"
  },
  "claims": [
    {
      "id": "c1",
      "text": "The claim statement",
      "score": 10,
      "evidence": [
        {
          "type": "literature",
          "source": "path/to/paper.pdf",
          "reference_text": "Exact quote from source"
        }
      ],
      "reasoning": "Why this score",
      "uncertainties": ["Known unknowns affecting this claim"],
      "tags": ["optional", "tags"]
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

### Field Specifications

**Metadata** (required):
- `name` (string, required): Name of the hypergraph
- `description` (string, required): Brief description
- `created` (string, optional): Creation date
- `last_updated` (string, optional): Last modification date
- `version` (string, optional): Version number

**Claims** (required array):
- `id` (string, required): Unique identifier, no duplicates allowed
- `text` (string, required): Non-empty claim statement
- `score` (number, required): Must be 0-10 (integers or floats)
- `evidence` (array, optional): See Evidence Structure below
- `reasoning` (string, optional): Explanation for the score
- `uncertainties` (array of strings, optional): Known unknowns
- `tags` (array of strings, optional): Categorical tags

**Implications** (required array):
- `id` (string, required): Unique identifier, no duplicates allowed
- `premises` (array of strings, required): Non-empty list of claim IDs
- `conclusion` (string, required): Claim ID that follows from premises
- `type` (string, required): Must be `"AND"` or `"OR"`
- `reasoning` (string, optional): Explanation of logical connection

**Evidence Structure** (if using detailed validation):

Each evidence item must have a `type` field and type-specific required fields:

1. **Literature** - Papers, citations, published data
   ```json
   {
     "type": "literature",
     "source": "citations/paper.pdf",
     "reference_text": "Exact quote from the source"
   }
   ```
   - `source` (string, required): File path or citation reference
   - `reference_text` (string, required): Exact quoted text
   - `lines` (string, optional): If source is a file, line spec like "12-45"

2. **Simulation** - Results from simulation code
   ```json
   {
     "type": "simulation",
     "source": "simulations/my_sim.py",
     "lines": "145-170",
     "code": "# Exact code from those lines"
   }
   ```
   - `source` (string, required): Path to simulation script
   - `lines` (string, required): Line numbers (e.g., "145-170" or "10-15, 20-25")
   - `code` (string, required): Extracted code from those lines

3. **Calculation** - Analytical estimates, back-of-envelope math
   ```json
   {
     "type": "calculation",
     "equations": "E = mc^2, F = ma",
     "program": "def calculate(): return result"
   }
   ```
   - `equations` (string, required): LaTeX or text formulas
   - `program` (string, required): Python function performing calculation

## Advantages

1. **Reusability**: Same atomic claim can be used in multiple implications
2. **Compositionality**: Build complex arguments from simple claims
3. **Graph analysis**: Can use standard graph algorithms (paths, cycles, etc.)
4. **Modularity**: Add/remove implications without restructuring the entire graph
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

This hypergraph approach is ideal for:
- Multiple independent paths to the same conclusion
- Reusing atomic claims across different arguments
- Modeling "if-then" reasoning explicitly
- Applying graph-theoretic analysis (paths, cycles, connectivity)
- Building a knowledge base of reusable claims
- Complex logical dependencies with multiple derivation paths
- Compositional reasoning where claims build on each other

## Type Checking

Hypergraph files must follow strict validation rules. Use the type checker to validate:

```bash
# Check a single file
python typecheck_hypergraph.py entailment_hypergraph/steam_engine_example.json

# Check all JSON files in directory
python typecheck_hypergraph.py entailment_hypergraph/
```

### Validation Rules

The type checker enforces:

**1. Required Top-Level Structure:**
- `metadata` object with `name` (string) and `description` (string)
- `claims` array with at least one claim
- `implications` array (can be empty)

**2. Claim Validation:**
- `id` (string, required) - must be unique across all claims
- `text` (string, required) - cannot be empty
- `score` (number, required) - must be between 0 and 10 (inclusive)
- `evidence` (array, optional) - if present, each item must match evidence schemas
- `reasoning` (string, optional) - cannot be empty if present
- `uncertainties` (array of strings, optional)
- `tags` (array of strings, optional)

**3. Implication Validation:**
- `id` (string, required) - must be unique across all implications
- `premises` (array of strings, required) - cannot be empty, all IDs must reference existing claims
- `conclusion` (string, required) - must reference an existing claim
- `type` (string, required) - must be `"AND"` or `"OR"`
- `reasoning` (string, optional) - cannot be empty if present

**4. Evidence Type Validation:**
If a claim has an `evidence` array, each item must be one of these types with required fields:

- **`literature`**: `source` (string), `reference_text` (string)
- **`simulation`**: `source` (string), `lines` (string), `code` (string)
- **`calculation`**: `equations` (string), `program` (string)

Additional fields not in the schema will generate warnings.

**5. Source Code Verification:**
For `simulation` and `literature` evidence types, the type checker verifies that:
- The source file exists
- The `code` or `reference_text` exactly matches the content at the specified lines
- Line specifications support formats like `"145-170"` or `"10-15, 20-25"`

This prevents drift between evidence and source files.

**6. Reference Integrity:**
- All premise IDs must reference existing claims
- All conclusion IDs must reference existing claims
- No dangling references allowed

**Exit Codes:**
- `0` - Passed (or passed with warnings only)
- `1` - Failed with errors

### Example Output

**Success:**
```
✓ Type checking PASSED!
```

**With Warnings:**
```
⚠️  1 warning(s):
  WARNING: claims[0].evidence[0]: Unexpected field 'description' for evidence type 'literature'.
           Allowed fields: type, source, reference_text

✓ Type checking PASSED (with warnings)
```

**With Errors:**
```
❌ Type checking FAILED with 2 error(s):
  ERROR: claims[0].evidence[0]: Invalid evidence type 'experiment'.
         Must be one of: calculation, literature, simulation
  ERROR: claims[0].evidence[0].code does not match source simulations/test.py:10-15
```

**Directory Check:**
```
Type checking all JSON files in: entailment_hypergraph/

============================================================
File: water_boiling_example.json
============================================================
✓ PASSED

============================================================
File: steam_engine_example.json
============================================================
✓ PASSED

============================================================
Summary: 2 file(s) checked
============================================================
Total errors: 0
Total warnings: 0

✓ All files PASSED!
```

## Future Extensions

- **Score propagation**: Automatically compute conclusion scores from premises
- **Cycle detection**: Identify circular reasoning
- **Path analysis**: Find all ways to derive a conclusion
- **Claim library**: Reusable database of atomic claims
- **Multiple example types**: Beyond just water boiling
