# Entailment Tree Visualizer

Interactive web-based visualizer for entailment trees. Smooth, elegant, and deployable to any static host.

## Features

- 🎯 **Interactive expand/collapse** - Click nodes to see details
- 📊 **Score visualization** - Color-coded scores with badges
- 🏷️ **Tagged blockers** - Critical issues highlighted
- 📑 **Evidence tracking** - Links to simulations, literature, calculations
- 📱 **Responsive design** - Works on mobile and desktop
- ⚡ **Fast & lightweight** - Pure HTML/CSS/JS, no build step

## Local Development

**Important:** Serve from the parent directory (ai-simulations/) so the visualizer can access the JSON files:

```bash
# From ai-simulations/ directory
cd ai-simulations/

# Python
python -m http.server 8000

# Node
npx http-server

# PHP
php -S localhost:8000
```

Then visit `http://localhost:8000/tree_visualizer/`

## Adding New Trees

Edit the `TREES` array in `index.html`:

```javascript
const TREES = [
    {
        name: 'Ultrasound-Enhanced EEG',
        path: '/ultrasound_eeg_enhancement/entailment_tree.json'
    },
    {
        name: 'Your New Approach',
        path: '/your_approach/entailment_tree.json'
    }
];
```

**Note:** Paths start with `/` (absolute from server root) since the visualizer is at `/tree_visualizer/`.

## Deploy to Netlify

**Important:** Deploy the entire `ai-simulations/` directory so JSON files are accessible.

### Option 1: Drag & Drop
1. Go to [Netlify](https://netlify.com)
2. Drag the `ai-simulations` folder onto the deploy zone
3. Done! Visit `https://your-site.netlify.app/tree_visualizer/`

### Option 2: CLI
```bash
npm install -g netlify-cli
cd ai-simulations/
netlify deploy --prod
```

### Option 3: Git
1. Push to GitHub
2. Connect repo to Netlify
3. Publish directory: `.` (root)
4. Deploy! Visualizer will be at `/tree_visualizer/`

## Deploy to Vercel

### Option 1: CLI
```bash
npm install -g vercel
cd ai-simulations/
vercel --prod
```

### Option 2: Git
1. Push to GitHub
2. Import project in Vercel
3. Root directory: leave as `.` (project root)
4. Deploy! Visualizer will be at `/tree_visualizer/`

## Deploy Anywhere

This is a static site. It works on:
- Netlify
- Vercel
- GitHub Pages
- CloudFlare Pages
- AWS S3 + CloudFront
- Any static host

Just upload the files and you're done!

## File Structure

```
tree_visualizer/
├── index.html          # Main app (includes CSS & JS)
├── netlify.toml        # Netlify config
├── vercel.json         # Vercel config
└── README.md           # This file
```

## Usage

1. Select an approach from the dropdown
2. Click on any node to expand and see:
   - Reasoning for the score
   - Evidence (simulations, literature, calculations)
   - Uncertainties
3. Navigate the tree hierarchy
4. Identify critical blockers (highlighted in red)

## Customization

All styling is in the `<style>` tag in `index.html`. Color scheme uses CSS variables:

```css
--bg-primary: #0f1419;
--accent: #58a6ff;
--success: #3fb950;
--danger: #f85149;
```

Change these to match your preferences!
