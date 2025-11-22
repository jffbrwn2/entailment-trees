#!/usr/bin/env python3
"""
Auto-generate hypergraph catalog from filesystem.

Scans for:
- Example files in entailment_hypergraph/
- Approach folders in approaches/

Run this manually or as a pre-commit hook to keep catalog synced.
"""

import json
from pathlib import Path

# Project root
ROOT = Path(__file__).parent

# Fixed example files
EXAMPLE_FILES = [
    {
        "name": "Water Boiling (Simple)",
        "path": "/entailment_hypergraph/water_boiling_example.json",
        "category": "example"
    },
    {
        "name": "Steam Engine Feasibility (Complex)",
        "path": "/entailment_hypergraph/steam_engine_example.json",
        "category": "example"
    },
    {
        "name": "Ultrasound EEG Enhancement (Real Project)",
        "path": "/entailment_hypergraph/ultrasound_eeg_enhancement.json",
        "category": "example"
    }
]


def scan_approaches():
    """Scan approaches/ folder for hypergraph.json files."""
    approaches_dir = ROOT / "approaches"

    if not approaches_dir.exists():
        return []

    approaches = []

    for approach_dir in sorted(approaches_dir.iterdir()):
        if not approach_dir.is_dir():
            continue

        hypergraph_file = approach_dir / "hypergraph.json"
        if not hypergraph_file.exists():
            continue

        # Load hypergraph to get the name
        try:
            with open(hypergraph_file) as f:
                data = json.load(f)
                name = data.get("metadata", {}).get("name", approach_dir.name)
        except Exception:
            # Fallback to folder name if can't read
            name = approach_dir.name

        approaches.append({
            "name": name,
            "path": f"/approaches/{approach_dir.name}/hypergraph.json",
            "category": "approach"
        })

    return approaches


def update_catalog():
    """Update catalog with current filesystem state."""
    catalog_path = ROOT / "entailment_hypergraph" / "hypergraph_catalog.json"

    # Build catalog
    catalog = {
        "examples": EXAMPLE_FILES,
        "approaches": scan_approaches()
    }

    # Write catalog
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Updated {catalog_path}")
    print(f"  Examples: {len(catalog['examples'])}")
    print(f"  Approaches: {len(catalog['approaches'])}")

    for approach in catalog['approaches']:
        print(f"    - {approach['name']}")


if __name__ == "__main__":
    update_catalog()
