"""
Clean up entailment tree to simplified structure.
- Remove 'type' field from nodes
- Standardize evidence types to: simulation, literature, calculation
"""

import json
import sys


EVIDENCE_TYPE_MAPPING = {
    'simulation': 'simulation',
    'literature': 'literature',
    'calculation': 'calculation',
    'estimate': 'calculation',
    'physics': 'literature',
    'technique': 'literature',
    'guideline': 'literature',
    'tool': 'simulation',
}


def cleanup_node(node):
    """Recursively clean up a node."""
    # Remove 'type' field
    if 'type' in node:
        del node['type']

    # Standardize evidence types
    if 'evidence' in node:
        for evidence in node['evidence']:
            old_type = evidence.get('type', '')
            if old_type in EVIDENCE_TYPE_MAPPING:
                evidence['type'] = EVIDENCE_TYPE_MAPPING[old_type]
            elif old_type and old_type not in ['simulation', 'literature', 'calculation']:
                print(f"Warning: Unknown evidence type '{old_type}' in node {node.get('id')}")
                evidence['type'] = 'literature'  # Default fallback

    # Recurse to children
    for child in node.get('children', []):
        cleanup_node(child)

    return node


def cleanup_tree(tree_data):
    """Clean up entire tree structure."""
    if 'tree' in tree_data:
        cleanup_node(tree_data['tree'])

    # Clean up alternative hypotheses
    for alt in tree_data.get('alternative_hypotheses', []):
        if 'type' in alt:
            del alt['type']
        if 'evidence' in alt:
            for evidence in alt['evidence']:
                old_type = evidence.get('type', '')
                if old_type in EVIDENCE_TYPE_MAPPING:
                    evidence['type'] = EVIDENCE_TYPE_MAPPING[old_type]

    return tree_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cleanup_tree.py <json_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Load
    with open(input_file, 'r') as f:
        tree = json.load(f)

    # Clean up
    tree = cleanup_tree(tree)

    # Save back
    with open(input_file, 'w') as f:
        json.dump(tree, f, indent=2)

    print(f"✓ Cleaned up {input_file}")
