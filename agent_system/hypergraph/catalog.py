#!/usr/bin/env python3
"""
Auto-generate hypergraph catalog from filesystem.

Scans approach folders in approaches/ and generates a catalog JSON file.
"""

import json
from pathlib import Path

# Project root (3 levels up from agent_system/hypergraph/catalog.py)
ROOT = Path(__file__).parent.parent.parent


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
    catalog_path = ROOT / "backend" / "static" / "hypergraph_catalog.json"

    # Build catalog
    catalog = {
        "approaches": scan_approaches()
    }

    # Write catalog
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Updated {catalog_path}")
    print(f"  Approaches: {len(catalog['approaches'])}")


if __name__ == "__main__":
    update_catalog()
