# Try It Now!

## Quick Start

Start a server from the **parent directory** (ai-simulations/):

```bash
cd /Users/jbrown/Documents/alegria/ai-simulations/
python -m http.server 8765
```

Then open your browser and visit:
```
http://localhost:8765/tree_visualizer/
```

## What You'll See

### 1. **Header Stats**
- Main Score: 2.5/10 (color-coded red = poor)
- Combined Score: 2.956
- Total Nodes: 19
- Critical Blockers: 3 (highlighted)
- Average Score: 6.0/10

### 2. **Interactive Tree**
Every node shows:
- **Score badge** (color-coded: green=excellent, blue=good, yellow=uncertain, red=poor)
- **Node ID** (e.g., `premise_1_2`)
- **Claim text**
- **Tags** (CRITICAL_BLOCKER, AND/OR relationship, combined score)

### 3. **Click Any Node**
Expands to show:
- **Reasoning** - Why this score was assigned
- **Evidence** - Tagged by type (simulation/literature/calculation)
  - Links to source files with line numbers
  - Descriptions of what the evidence shows
- **Uncertainties** - Known unknowns affecting the score

### 4. **Smooth Navigation**
- Expand/collapse with smooth animations
- Color-coded everything
- Tree hierarchy with visual connectors
- Mobile-responsive

## Example Flow

1. **See the main hypothesis** (root node) - Score 2.5/10 (red = not feasible)
2. **Expand it** - See reasoning: "Signal 500× below noise floor"
3. **Look at Premise 1** - Score 2.0/10 (the main problem)
4. **Expand Premise 1** - See it has 4 sub-premises
5. **Find sub-premise 1.2** - Score 2.0/10, tagged CRITICAL_BLOCKER
6. **Expand it** - See the exact issue: "Natural neural currents are 1000× weaker than injected currents"

This immediately shows you **why** the idea doesn't work and **what would need to change**.

## Deploy It

When you're ready to share, deploy the **entire ai-simulations directory**:

```bash
# Netlify CLI:
npm install -g netlify-cli
cd ai-simulations/
netlify deploy --prod

# Vercel:
npm install -g vercel
cd ai-simulations/
vercel --prod
```

Or drag the entire `ai-simulations` folder to Netlify/Vercel.

You'll get a URL like `https://entailment-trees.netlify.app/tree_visualizer/` that anyone can access!

## Adding More Approaches

As you create more simulation approaches, just add them to the `TREES` array in `index.html`:

```javascript
const TREES = [
    {
        name: 'Ultrasound-Enhanced EEG',
        path: '/ultrasound_eeg_enhancement/entailment_tree.json'
    },
    {
        name: 'New Approach',
        path: '/new_approach/entailment_tree.json'
    }
];
```

**Note:** Use absolute paths starting with `/` since the visualizer is served from `/tree_visualizer/`.

The dropdown selector will automatically update!
