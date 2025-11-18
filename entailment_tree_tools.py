"""
Tools for working with entailment trees in JSON format.

This module provides utilities to:
- Validate entailment tree structure
- Calculate combined scores automatically
- Generate visualizations (text, markdown, graphviz)
- Compare multiple approaches
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple


def load_tree(json_path: str) -> Dict[str, Any]:
    """Load an entailment tree from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def calculate_combined_score_and(scores: List[float]) -> float:
    """
    Calculate combined score for AND relationship.
    Formula: sum_i(-log(score_i/10))
    Lower score = worse (more uncertainty)
    """
    if not scores:
        return 0.0
    return sum(-math.log10(max(s, 0.01) / 10) for s in scores)


def calculate_combined_score_or(scores: List[float]) -> float:
    """
    Calculate combined score for OR relationship.
    Formula: max_i(-log(score_i/10))
    Best child determines parent score
    """
    if not scores:
        return 0.0
    return max(-math.log10(max(s, 0.01) / 10) for s in scores)


def recalculate_scores(node: Dict[str, Any]) -> float:
    """
    Recursively recalculate combined scores for entire tree.
    Returns the combined score for this node.
    """
    # Base case: leaf node
    if not node.get('children'):
        return node.get('score', 5.0)

    # Recursive case: calculate children first
    child_scores = []
    for child in node['children']:
        child_combined = recalculate_scores(child)
        child_scores.append(child.get('score', 5.0))

    # Calculate combined score based on relationship type
    relationship = node.get('children_relationship', 'AND')
    if relationship == 'AND':
        combined = calculate_combined_score_and(child_scores)
    else:  # OR
        combined = calculate_combined_score_or(child_scores)

    node['combined_score'] = round(combined, 3)
    return combined


def validate_tree(tree: Dict[str, Any]) -> List[str]:
    """
    Validate tree structure and return list of issues found.
    Empty list means tree is valid.

    Note: This is a lightweight check. Use typecheck_tree.py for comprehensive validation.
    """
    from typecheck_tree import typecheck_tree as full_typecheck
    import tempfile
    import os

    # Write to temp file and run full type checker
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(tree, f)
        temp_path = f.name

    try:
        errors, warnings = full_typecheck(temp_path)
        return errors + warnings
    finally:
        os.unlink(temp_path)


def get_all_nodes(node: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Get all nodes in tree as flat list with paths.
    Returns list of (path, node) tuples.
    """
    nodes = [(node['id'], node)]
    for child in node.get('children', []):
        nodes.extend(get_all_nodes(child))
    return nodes


def find_critical_blockers(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find all nodes tagged as CRITICAL_BLOCKER."""
    blockers = []

    def search(node: Dict[str, Any]) -> None:
        tags = node.get('tags', [])
        if 'CRITICAL_BLOCKER' in tags:
            blockers.append({
                'id': node['id'],
                'claim': node['claim'],
                'score': node['score'],
                'reasoning': node.get('reasoning', 'N/A')
            })

        for child in node.get('children', []):
            search(child)

    search(tree['tree'])
    return blockers


def generate_text_tree(node: Dict[str, Any], indent: int = 0, prefix: str = "") -> str:
    """
    Generate text-based tree visualization.
    """
    lines = []

    # Node info
    score = node.get('score', 'N/A')
    combined = node.get('combined_score', 'N/A')
    claim = node['claim'][:80] + "..." if len(node['claim']) > 80 else node['claim']

    # Format with box drawing characters
    if indent == 0:
        lines.append(f"┌─ [{score}/10] {node['id']}")
        lines.append(f"│  {claim}")
        if combined != 'N/A':
            lines.append(f"│  Combined: {combined}")
    else:
        lines.append(f"{prefix}├─ [{score}/10] {node['id']}")
        lines.append(f"{prefix}│  {claim}")

    # Children
    children = node.get('children', [])
    if children:
        relationship = node.get('children_relationship', 'AND')
        lines.append(f"{prefix}│")
        lines.append(f"{prefix}└─ {relationship} ─┐")

        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            child_prefix = prefix + ("   " if is_last else "│  ")
            child_lines = generate_text_tree(child, indent + 1, child_prefix)
            lines.append(child_lines)

    return "\n".join(lines)


def generate_summary(tree_data: Dict[str, Any]) -> str:
    """Generate a summary report of the entailment tree."""
    summary_lines = []

    metadata = tree_data['metadata']
    tree = tree_data['tree']

    summary_lines.append(f"# Entailment Tree Summary: {metadata['approach']}")
    summary_lines.append(f"\nVersion: {metadata['version']}")
    summary_lines.append(f"Last Updated: {metadata['last_updated']}")
    summary_lines.append(f"\n## Main Hypothesis")
    summary_lines.append(f"**Score:** {tree['score']}/10")
    summary_lines.append(f"**Combined Score:** {tree.get('combined_score', 'N/A')}")
    summary_lines.append(f"**Verdict:** {tree.get('combined_score_interpretation', 'N/A')}")
    summary_lines.append(f"\n**Claim:** {tree['claim']}")

    # Count nodes
    all_nodes = get_all_nodes(tree)
    summary_lines.append(f"\n## Tree Statistics")
    summary_lines.append(f"- Total nodes: {len(all_nodes)}")
    summary_lines.append(f"- Main premises: {len(tree.get('children', []))}")

    # Score distribution
    scores = [n[1]['score'] for n in all_nodes if 'score' in n[1]]
    if scores:
        summary_lines.append(f"- Average score: {sum(scores)/len(scores):.1f}/10")
        summary_lines.append(f"- Min score: {min(scores)}/10")
        summary_lines.append(f"- Max score: {max(scores)}/10")

    # Critical blockers
    blockers = find_critical_blockers(tree_data)
    if blockers:
        summary_lines.append(f"\n## Critical Blockers ({len(blockers)})")
        for blocker in blockers:
            summary_lines.append(f"\n**{blocker['id']}** (Score: {blocker['score']}/10)")
            summary_lines.append(f"- {blocker['claim']}")

    # Alternative hypotheses
    alts = tree_data.get('alternative_hypotheses', [])
    if alts:
        summary_lines.append(f"\n## Alternative Hypotheses ({len(alts)})")
        for alt in alts:
            summary_lines.append(f"\n**{alt['claim']}**")
            summary_lines.append(f"- Score: {alt['score']}/10")

    # Conclusions
    conclusions = tree_data.get('conclusions', {})
    if conclusions:
        summary_lines.append(f"\n## Conclusions")
        for key, value in conclusions.items():
            if isinstance(value, dict):
                summary_lines.append(f"\n### {key.replace('_', ' ').title()}")
                summary_lines.append(f"**Verdict:** {value.get('verdict', 'N/A')}")
                summary_lines.append(f"**Reason:** {value.get('reason', 'N/A')}")

    return "\n".join(summary_lines)


def compare_approaches(json_paths: List[str]) -> str:
    """Compare multiple approaches side-by-side."""
    trees = [load_tree(path) for path in json_paths]

    lines = []
    lines.append("# Approach Comparison\n")
    lines.append("| Approach | Main Score | Combined Score | Verdict |")
    lines.append("|----------|------------|----------------|---------|")

    for tree in trees:
        name = tree['metadata']['approach']
        score = tree['tree']['score']
        combined = tree['tree'].get('combined_score', 'N/A')
        verdict = tree['tree'].get('combined_score_interpretation', 'N/A')
        lines.append(f"| {name} | {score}/10 | {combined} | {verdict} |")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python entailment_tree_tools.py <command> <json_file>")
        print("\nCommands:")
        print("  validate <file>        - Validate tree structure")
        print("  recalculate <file>     - Recalculate all combined scores")
        print("  summary <file>         - Generate summary report")
        print("  tree <file>            - Display tree structure")
        print("  blockers <file>        - List critical blockers")
        print("  compare <file1> <file2> ... - Compare multiple approaches")
        sys.exit(1)

    command = sys.argv[1]

    if command == "validate":
        tree = load_tree(sys.argv[2])
        issues = validate_tree(tree)
        if issues:
            print("Validation issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓ Tree is valid!")

    elif command == "recalculate":
        tree = load_tree(sys.argv[2])
        recalculate_scores(tree['tree'])
        # Save back to file
        output_path = sys.argv[2]
        with open(output_path, 'w') as f:
            json.dump(tree, f, indent=2)
        print(f"✓ Scores recalculated and saved to {output_path}")

    elif command == "summary":
        tree = load_tree(sys.argv[2])
        print(generate_summary(tree))

    elif command == "tree":
        tree = load_tree(sys.argv[2])
        print(generate_text_tree(tree['tree']))

    elif command == "blockers":
        tree = load_tree(sys.argv[2])
        blockers = find_critical_blockers(tree)
        if blockers:
            print(f"Found {len(blockers)} critical blocker(s):\n")
            for blocker in blockers:
                print(f"[{blocker['score']}/10] {blocker['id']}")
                print(f"  {blocker['claim']}")
                print(f"  Reasoning: {blocker['reasoning']}\n")
        else:
            print("No critical blockers found!")

    elif command == "compare":
        json_files = sys.argv[2:]
        print(compare_approaches(json_files))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
