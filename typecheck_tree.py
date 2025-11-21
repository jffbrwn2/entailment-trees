"""
Type checker for entailment trees.

Validates:
- Required fields exist with correct types
- Scores are in valid range
- Evidence types are allowed
- Structure is valid (no cycles, proper nesting)
- References are valid
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple, Optional


# Allowed values
ALLOWED_EVIDENCE_TYPES = {'simulation', 'literature', 'calculation'}
ALLOWED_RELATIONSHIPS = {'AND', 'OR'}

# Evidence type schemas - defines required fields for each type
EVIDENCE_SCHEMAS = {
    'literature': {
        'required': ['source', 'reference_text'],
        'optional': []
    },
    'simulation': {
        'required': ['source', 'lines', 'code'],
        'optional': []
    },
    'calculation': {
        'required': ['equations', 'program'],
        'optional': []
    }
}


def read_source_lines(source_path: Path, lines_spec: str) -> Optional[str]:
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


class TypeCheckError(Exception):
    """Custom exception for type checking errors."""
    pass


class TreeTypeChecker:
    def __init__(self, base_path: Optional[Path] = None):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.node_ids: Set[str] = set()
        self.base_path = base_path

    def error(self, path: str, message: str):
        """Record an error."""
        self.errors.append(f"{path}: {message}")

    def warning(self, path: str, message: str):
        """Record a warning."""
        self.warnings.append(f"{path}: {message}")

    def check_type(self, path: str, value: Any, expected_type: type, field_name: str):
        """Check if value has expected type."""
        if not isinstance(value, expected_type):
            self.error(path, f"'{field_name}' must be {expected_type.__name__}, got {type(value).__name__}")
            return False
        return True

    def check_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate metadata section."""
        path = "metadata"

        # Required fields
        required = {
            'approach': str,
            'created': str,
            'last_updated': str,
            'version': str
        }

        for field, expected_type in required.items():
            if field not in metadata:
                self.error(path, f"Missing required field '{field}'")
            else:
                self.check_type(path, metadata[field], expected_type, field)

    def check_evidence(self, path: str, evidence: List[Dict[str, Any]]) -> None:
        """Validate evidence array with strict type schemas."""
        if not isinstance(evidence, list):
            self.error(path, "'evidence' must be a list")
            return

        for i, item in enumerate(evidence):
            item_path = f"{path}.evidence[{i}]"

            if not isinstance(item, dict):
                self.error(item_path, "Evidence item must be an object")
                continue

            # Check type field
            if 'type' not in item:
                self.error(item_path, "Missing 'type' field")
                continue

            evidence_type = item['type']
            if evidence_type not in ALLOWED_EVIDENCE_TYPES:
                self.error(
                    item_path,
                    f"Invalid evidence type '{evidence_type}'. "
                    f"Must be one of: {', '.join(sorted(ALLOWED_EVIDENCE_TYPES))}"
                )
                continue

            # Get schema for this evidence type
            schema = EVIDENCE_SCHEMAS[evidence_type]

            # Check required fields
            for required_field in schema['required']:
                if required_field not in item:
                    self.error(
                        item_path,
                        f"Missing required field '{required_field}' for evidence type '{evidence_type}'"
                    )
                elif not isinstance(item[required_field], str):
                    self.error(
                        item_path,
                        f"Field '{required_field}' must be a string"
                    )

            # Check optional fields if present
            for optional_field in schema['optional']:
                if optional_field in item and not isinstance(item[optional_field], str):
                    self.error(
                        item_path,
                        f"Optional field '{optional_field}' must be a string"
                    )

            # Check for disallowed fields
            allowed_fields = {'type'} | set(schema['required']) | set(schema['optional'])
            for field in item.keys():
                if field not in allowed_fields:
                    self.warning(
                        item_path,
                        f"Unexpected field '{field}' for evidence type '{evidence_type}'. "
                        f"Allowed fields: {', '.join(sorted(allowed_fields))}"
                    )

            # Verify code/reference_text matches source file
            if self.base_path and evidence_type in ('literature', 'simulation'):
                source = item.get('source')
                if source and not source.startswith('TODO'):
                    source_file = self.base_path / source
                    if source_file.exists():
                        if evidence_type == 'literature' and 'lines' in item:
                            # Verify reference_text matches source
                            lines_spec = item['lines']
                            expected = read_source_lines(source_file, lines_spec)
                            actual = item.get('reference_text', '').strip()
                            if expected and actual != expected:
                                self.error(
                                    item_path,
                                    f"reference_text does not match source {source}:{lines_spec}"
                                )
                        elif evidence_type == 'simulation':
                            # Verify code matches source
                            lines_spec = item.get('lines')
                            if lines_spec and not lines_spec.startswith('TODO'):
                                expected = read_source_lines(source_file, lines_spec)
                                actual = item.get('code', '').strip()
                                if expected and actual != expected:
                                    self.error(
                                        item_path,
                                        f"code does not match source {source}:{lines_spec}"
                                    )

    def check_node(self, node: Dict[str, Any], path: str = "tree") -> None:
        """Recursively validate a node."""
        if not isinstance(node, dict):
            self.error(path, "Node must be an object")
            return

        # Required fields
        if 'id' not in node:
            self.error(path, "Missing required field 'id'")
        else:
            node_id = node['id']
            if not isinstance(node_id, str):
                self.error(path, "'id' must be a string")
            else:
                # Check for duplicate IDs
                if node_id in self.node_ids:
                    self.error(path, f"Duplicate node ID '{node_id}'")
                self.node_ids.add(node_id)

        if 'claim' not in node:
            self.error(path, "Missing required field 'claim'")
        elif not isinstance(node['claim'], str):
            self.error(path, "'claim' must be a string")
        elif len(node['claim']) == 0:
            self.error(path, "'claim' cannot be empty")

        if 'score' not in node:
            self.error(path, "Missing required field 'score'")
        else:
            score = node['score']
            if not isinstance(score, (int, float)):
                self.error(path, f"'score' must be a number, got {type(score).__name__}")
            elif not (0 <= score <= 10):
                self.error(path, f"'score' must be between 0 and 10, got {score}")

        # Optional but validated if present
        if 'combined_score' in node:
            combined = node['combined_score']
            if not isinstance(combined, (int, float)):
                self.error(path, "'combined_score' must be a number")

        if 'evidence' in node:
            self.check_evidence(path, node['evidence'])

        if 'reasoning' in node:
            if not isinstance(node['reasoning'], str):
                self.error(path, "'reasoning' must be a string")
            elif len(node['reasoning']) == 0:
                self.warning(path, "'reasoning' is empty")

        if 'uncertainties' in node:
            if not isinstance(node['uncertainties'], list):
                self.error(path, "'uncertainties' must be a list")
            else:
                for i, uncertainty in enumerate(node['uncertainties']):
                    if not isinstance(uncertainty, str):
                        self.error(f"{path}.uncertainties[{i}]", "Must be a string")

        if 'tags' in node:
            if not isinstance(node['tags'], list):
                self.error(path, "'tags' must be a list")
            else:
                for i, tag in enumerate(node['tags']):
                    if not isinstance(tag, str):
                        self.error(f"{path}.tags[{i}]", "Must be a string")

        # Children validation
        children = node.get('children', [])
        if not isinstance(children, list):
            self.error(path, "'children' must be a list")
        elif len(children) > 0:
            # If has children, must have relationship
            if 'children_relationship' not in node:
                self.error(path, "Node has children but missing 'children_relationship'")
            else:
                relationship = node['children_relationship']
                if relationship not in ALLOWED_RELATIONSHIPS:
                    self.error(
                        path,
                        f"Invalid relationship '{relationship}'. "
                        f"Must be one of: {', '.join(sorted(ALLOWED_RELATIONSHIPS))}"
                    )

            # Recurse to children
            for i, child in enumerate(children):
                child_path = f"{path}.children[{i}]"
                self.check_node(child, child_path)

        # Warn if has relationship but no children
        if 'children_relationship' in node and len(children) == 0:
            self.warning(path, "Has 'children_relationship' but no children")

    def check_alternative_hypotheses(self, alternatives: List[Dict[str, Any]]) -> None:
        """Validate alternative hypotheses."""
        if not isinstance(alternatives, list):
            self.error("alternative_hypotheses", "Must be a list")
            return

        for i, alt in enumerate(alternatives):
            path = f"alternative_hypotheses[{i}]"

            if not isinstance(alt, dict):
                self.error(path, "Must be an object")
                continue

            # Required fields
            if 'claim' not in alt:
                self.error(path, "Missing 'claim'")
            elif not isinstance(alt['claim'], str):
                self.error(path, "'claim' must be a string")

            if 'score' not in alt:
                self.error(path, "Missing 'score'")
            elif not isinstance(alt['score'], (int, float)):
                self.error(path, "'score' must be a number")
            elif not (0 <= alt['score'] <= 10):
                self.error(path, f"'score' must be between 0 and 10, got {alt['score']}")

            # Optional fields
            if 'evidence' in alt:
                self.check_evidence(path, alt['evidence'])

    def check_tree(self, tree_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Main entry point for type checking.
        Returns (errors, warnings).
        """
        # Check top-level structure
        if not isinstance(tree_data, dict):
            self.error("root", "Tree must be a JSON object")
            return self.errors, self.warnings

        # Check metadata
        if 'metadata' not in tree_data:
            self.error("root", "Missing 'metadata' section")
        else:
            self.check_metadata(tree_data['metadata'])

        # Check tree
        if 'tree' not in tree_data:
            self.error("root", "Missing 'tree' section")
        else:
            self.check_node(tree_data['tree'], "tree")

        # Check alternative hypotheses (optional)
        if 'alternative_hypotheses' in tree_data:
            self.check_alternative_hypotheses(tree_data['alternative_hypotheses'])

        return self.errors, self.warnings


def typecheck_tree(json_path: str) -> Tuple[List[str], List[str]]:
    """
    Type check an entailment tree JSON file.
    Returns (errors, warnings).
    """
    try:
        json_path_obj = Path(json_path)
        with open(json_path_obj, 'r') as f:
            tree_data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"], []
    except FileNotFoundError:
        return [f"File not found: {json_path}"], []

    base_path = json_path_obj.parent
    checker = TreeTypeChecker(base_path=base_path)
    return checker.check_tree(tree_data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python typecheck_tree.py <json_file>")
        sys.exit(1)

    json_file = sys.argv[1]
    errors, warnings = typecheck_tree(json_file)

    # Print results
    if errors:
        print(f"❌ Type checking FAILED with {len(errors)} error(s):\n")
        for error in errors:
            print(f"  ERROR: {error}")
        print()

    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):\n")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        print()

    if not errors and not warnings:
        print("✓ Type checking PASSED!")
        sys.exit(0)
    elif errors:
        sys.exit(1)
    else:
        print("✓ Type checking PASSED (with warnings)")
        sys.exit(0)
