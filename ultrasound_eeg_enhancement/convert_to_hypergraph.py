#!/usr/bin/env python3
"""
Convert nested entailment tree format to flat hypergraph format for visualization.
"""

import json
from pathlib import Path


def extract_claims_and_implications(node, claims, implications, parent_impl_id=None):
    """
    Recursively extract claims and implications from nested tree structure.

    Args:
        node: Current node in the tree
        claims: List to accumulate claim objects
        implications: List to accumulate implication objects
        parent_impl_id: ID of the implication that leads to this node
    """
    # Extract claim from this node
    claim = {
        "id": node["id"],
        "text": node["claim"],
        "score": node["score"]
    }

    # Add evidence if present
    if "evidence" in node and node["evidence"]:
        # Convert evidence format: the tree uses array of evidence objects,
        # hypergraph just needs the type from first evidence item for now
        # We'll include full evidence details in reasoning
        claim["evidence"] = node["evidence"]

    # Add reasoning if present
    if "reasoning" in node:
        claim["reasoning"] = node["reasoning"]

    # Add uncertainties if present
    if "uncertainties" in node:
        claim["uncertainties"] = node["uncertainties"]

    # Add tags if present
    if "tags" in node:
        claim["tags"] = node["tags"]

    claims.append(claim)

    # If this node has children, create an implication
    if "children" in node and node["children"]:
        # Create implication ID
        impl_id = f"impl_{node['id']}"

        # Extract premise IDs from children
        premise_ids = [child["id"] for child in node["children"]]

        # Determine implication type
        impl_type = node.get("children_relationship", "AND")

        # Create implication
        implication = {
            "id": impl_id,
            "premises": premise_ids,
            "conclusion": node["id"],
            "type": impl_type,
            "reasoning": node.get("reasoning", "")
        }

        implications.append(implication)

        # Recursively process children
        for child in node["children"]:
            extract_claims_and_implications(child, claims, implications)


def convert_tree_to_hypergraph(tree_path, output_path):
    """Convert nested tree JSON to flat hypergraph JSON."""

    # Load the tree
    with open(tree_path, 'r') as f:
        tree_data = json.load(f)

    claims = []
    implications = []

    # Extract the root node
    root = tree_data["tree"]

    # Process the tree
    extract_claims_and_implications(root, claims, implications)

    # Create hypergraph structure
    hypergraph = {
        "metadata": {
            "name": tree_data["metadata"]["approach"],
            "description": tree_data["metadata"]["description"],
            "created": tree_data["metadata"]["created"],
            "last_updated": tree_data["metadata"]["last_updated"],
            "version": tree_data["metadata"]["version"]
        },
        "claims": claims,
        "implications": implications
    }

    # Write output
    with open(output_path, 'w') as f:
        json.dump(hypergraph, f, indent=2)

    print(f"Converted {len(claims)} claims and {len(implications)} implications")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    tree_path = Path(__file__).parent / "entailment_tree.json"
    output_path = Path(__file__).parent / "entailment_hypergraph.json"

    convert_tree_to_hypergraph(tree_path, output_path)
