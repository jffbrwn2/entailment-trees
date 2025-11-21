#!/usr/bin/env python3
"""
Migrate evidence format to new strict schemas.

Converts old format to new format:
- literature: needs 'reference_text' (cannot auto-generate, marks as TODO)
- simulation: renames 'description' issues, ensures 'lines' exists
- calculation: needs 'equations' and 'program' (marks as TODO)
- Removes 'description' field from all
- Flags items that need manual work
"""

import json
import sys
from pathlib import Path
import re


def read_source_lines(source_path, lines_spec):
    """
    Read specific lines from a source file.

    Args:
        source_path: Path to the file
        lines_spec: Line specification like "3-18", "145-170", or "56-64, 152-156"

    Returns:
        Extracted text or None if file not found
    """
    try:
        with open(source_path, 'r') as f:
            all_lines = f.readlines()

        result_lines = []

        # Handle multiple ranges separated by commas
        for range_spec in lines_spec.split(','):
            range_spec = range_spec.strip()

            if '-' in range_spec:
                start, end = map(int, range_spec.split('-'))
                # Convert to 0-indexed
                selected_lines = all_lines[start-1:end]
                result_lines.extend(selected_lines)
            else:
                # Single line
                line_num = int(range_spec)
                result_lines.append(all_lines[line_num-1])

        return ''.join(result_lines).strip()
    except (FileNotFoundError, IndexError, ValueError):
        return None


def migrate_evidence_item(item, claim_id, evidence_index, base_path=None):
    """Migrate a single evidence item to new format."""
    issues = []

    if 'type' not in item:
        issues.append(f"Missing 'type' field")
        return item, issues

    evidence_type = item['type']
    new_item = {'type': evidence_type}

    if evidence_type == 'literature':
        # Required: source, reference_text
        if 'source' in item:
            new_item['source'] = item['source']
        else:
            issues.append(f"Missing 'source' for literature")
            new_item['source'] = "TODO: Add source citation or file"

        # reference_text is NEW and required
        if 'reference_text' in item:
            new_item['reference_text'] = item['reference_text']
        else:
            # Try to extract from source file if we have lines
            extracted = None
            if 'lines' in item and 'source' in item and base_path:
                source_file = base_path / item['source']
                if source_file.exists():
                    extracted = read_source_lines(source_file, item['lines'])
                    if extracted:
                        new_item['reference_text'] = extracted
                    else:
                        issues.append(f"Could not read lines {item['lines']} from {item['source']}")

            # If extraction failed, try to use description
            if not extracted:
                if 'description' in item:
                    new_item['reference_text'] = item['description']
                    issues.append(f"Used description as reference_text (no source file found)")
                else:
                    new_item['reference_text'] = f"TODO: Add exact quote from {new_item['source']}"
                    issues.append(f"Needs 'reference_text' - exact quote from literature")

    elif evidence_type == 'simulation':
        # Required: source, lines
        if 'source' in item:
            new_item['source'] = item['source']
        else:
            issues.append(f"Missing 'source' for simulation")
            new_item['source'] = "TODO: Add simulation script path"

        if 'lines' in item:
            new_item['lines'] = item['lines']
        else:
            issues.append(f"Missing 'lines' for simulation")
            new_item['lines'] = "TODO: Add line numbers"

    elif evidence_type == 'calculation':
        # Required: equations, program
        if 'equations' not in item:
            new_item['equations'] = "TODO: Add LaTeX equations"
            issues.append(f"Needs 'equations' - LaTeX formula")
        else:
            new_item['equations'] = item['equations']

        if 'program' not in item:
            new_item['program'] = "TODO: Add Python function that executes calculation"
            issues.append(f"Needs 'program' - Python function")
        else:
            new_item['program'] = item['program']

    else:
        issues.append(f"Unknown evidence type '{evidence_type}'. Valid types: literature, simulation, calculation")
        return item, issues

    # Warn about removed fields
    removed_fields = set(item.keys()) - set(new_item.keys()) - {'type'}
    if removed_fields:
        issues.append(f"Removed fields: {', '.join(removed_fields)}")

    return new_item, issues


def migrate_tree_node(node, path, base_path, total_issues, total_evidence_count):
    """Recursively migrate evidence in tree nodes."""
    if 'evidence' in node:
        new_evidence = []
        for j, item in enumerate(node['evidence']):
            total_evidence_count[0] += 1
            new_item, issues = migrate_evidence_item(item, node.get('id', 'unknown'), j, base_path)
            new_evidence.append(new_item)

            if issues:
                for issue in issues:
                    total_issues.append(f"{path}.evidence[{j}]: {issue}")

        node['evidence'] = new_evidence

    # Recurse to children
    if 'children' in node:
        for i, child in enumerate(node['children']):
            migrate_tree_node(child, f"{path}.children[{i}]", base_path, total_issues, total_evidence_count)


def migrate_hypergraph(input_path, output_path, dry_run=False):
    """Migrate a hypergraph or tree file to new evidence format."""

    input_path = Path(input_path)
    base_path = input_path.parent  # Directory containing the JSON file

    with open(input_path, 'r') as f:
        data = json.load(f)

    total_issues = []
    total_evidence_count = [0]  # Use list to allow mutation in nested function

    # Check if this is a hypergraph or tree format
    if 'claims' in data:
        # Hypergraph format
        for i, claim in enumerate(data['claims']):
            if 'evidence' in claim:
                new_evidence = []
                for j, item in enumerate(claim['evidence']):
                    total_evidence_count[0] += 1
                    new_item, issues = migrate_evidence_item(item, claim['id'], j, base_path)
                    new_evidence.append(new_item)

                    if issues:
                        for issue in issues:
                            total_issues.append(f"claims[{i}] ({claim['id']}).evidence[{j}]: {issue}")

                claim['evidence'] = new_evidence

    elif 'tree' in data:
        # Tree format - recursively process nodes
        migrate_tree_node(data['tree'], 'tree', base_path, total_issues, total_evidence_count)

    # Handle alternative_hypotheses (in both formats)
    if 'alternative_hypotheses' in data:
        for i, alt in enumerate(data['alternative_hypotheses']):
            if 'evidence' in alt:
                new_evidence = []
                for j, item in enumerate(alt['evidence']):
                    total_evidence_count[0] += 1
                    new_item, issues = migrate_evidence_item(item, alt.get('id', f'alt_{i}'), j, base_path)
                    new_evidence.append(new_item)

                    if issues:
                        for issue in issues:
                            total_issues.append(f"alternative_hypotheses[{i}].evidence[{j}]: {issue}")

                alt['evidence'] = new_evidence

    # Print report
    print(f"{'='*60}")
    print(f"Migration Report: {input_path}")
    print(f"{'='*60}")
    print(f"Total evidence items: {total_evidence_count[0]}")
    print(f"Issues found: {len(total_issues)}")
    print()

    if total_issues:
        print("Issues requiring attention:")
        for issue in total_issues:
            print(f"  - {issue}")
        print()

    if not dry_run:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Migrated file written to: {output_path}")
        print()
        print("⚠️  IMPORTANT: Review all 'TODO' markers and replace with actual content!")
    else:
        print("DRY RUN - No files written")

    return len(total_issues)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_evidence_format.py <input.json> [output.json]")
        print()
        print("If output.json not specified, will overwrite input file")
        print("Add --dry-run to see what would change without writing")
        sys.exit(1)

    input_file = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    if len(sys.argv) >= 3 and sys.argv[2] != '--dry-run':
        output_file = sys.argv[2]
    else:
        output_file = input_file

    issues = migrate_hypergraph(input_file, output_file, dry_run)

    if issues > 0:
        sys.exit(1)
    else:
        sys.exit(0)
