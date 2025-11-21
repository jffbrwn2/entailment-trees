"""
Type checker for entailment hypergraphs.

Validates:
- Required fields exist with correct types
- Scores are in valid range
- Evidence types are allowed (simulation, literature, calculation)
- Structure is valid (claims and implications)
- References are valid (premise/conclusion IDs exist)
- No duplicate IDs
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple


# Allowed values (must match typecheck_tree.py)
ALLOWED_EVIDENCE_TYPES = {'simulation', 'literature', 'calculation'}
ALLOWED_IMPLICATION_TYPES = {'AND', 'OR'}

# Evidence type schemas - defines required fields for each type
EVIDENCE_SCHEMAS = {
    'literature': {
        'required': ['source', 'reference_text'],
        'optional': []
    },
    'simulation': {
        'required': ['source', 'lines'],
        'optional': []
    },
    'calculation': {
        'required': ['equations', 'program'],
        'optional': []
    }
}


class TypeCheckError(Exception):
    """Custom exception for type checking errors."""
    pass


class HypergraphTypeChecker:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.claim_ids: Set[str] = set()
        self.implication_ids: Set[str] = set()

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
            'name': str,
            'description': str,
        }

        for field, expected_type in required.items():
            if field not in metadata:
                self.error(path, f"Missing required field '{field}'")
            else:
                self.check_type(path, metadata[field], expected_type, field)

        # Optional fields
        if 'created' in metadata:
            self.check_type(path, metadata['created'], str, 'created')
        if 'last_updated' in metadata:
            self.check_type(path, metadata['last_updated'], str, 'last_updated')
        if 'version' in metadata:
            self.check_type(path, metadata['version'], str, 'version')

    def check_evidence(self, path: str, evidence: List[Dict[str, Any]]) -> None:
        """Validate evidence array with strict type schemas."""
        if not isinstance(evidence, list):
            self.error(path, "'evidence' must be a list")
            return

        for i, item in enumerate(evidence):
            item_path = f"{path}[{i}]"

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

    def check_claim(self, claim: Dict[str, Any], index: int) -> None:
        """Validate a claim."""
        path = f"claims[{index}]"

        if not isinstance(claim, dict):
            self.error(path, "Claim must be an object")
            return

        # Required: id
        if 'id' not in claim:
            self.error(path, "Missing required field 'id'")
        else:
            claim_id = claim['id']
            if not isinstance(claim_id, str):
                self.error(path, "'id' must be a string")
            else:
                # Check for duplicate IDs
                if claim_id in self.claim_ids:
                    self.error(path, f"Duplicate claim ID '{claim_id}'")
                self.claim_ids.add(claim_id)

        # Required: text
        if 'text' not in claim:
            self.error(path, "Missing required field 'text'")
        elif not isinstance(claim['text'], str):
            self.error(path, "'text' must be a string")
        elif len(claim['text']) == 0:
            self.error(path, "'text' cannot be empty")

        # Required: score
        if 'score' not in claim:
            self.error(path, "Missing required field 'score'")
        else:
            score = claim['score']
            if not isinstance(score, (int, float)):
                self.error(path, f"'score' must be a number, got {type(score).__name__}")
            elif not (0 <= score <= 10):
                self.error(path, f"'score' must be between 0 and 10, got {score}")

        # Optional but validated if present
        if 'evidence' in claim:
            self.check_evidence(f"{path}.evidence", claim['evidence'])

        if 'reasoning' in claim:
            if not isinstance(claim['reasoning'], str):
                self.error(path, "'reasoning' must be a string")
            elif len(claim['reasoning']) == 0:
                self.warning(path, "'reasoning' is empty")

        if 'uncertainties' in claim:
            if not isinstance(claim['uncertainties'], list):
                self.error(path, "'uncertainties' must be a list")
            else:
                for i, uncertainty in enumerate(claim['uncertainties']):
                    if not isinstance(uncertainty, str):
                        self.error(f"{path}.uncertainties[{i}]", "Must be a string")

        if 'tags' in claim:
            if not isinstance(claim['tags'], list):
                self.error(path, "'tags' must be a list")
            else:
                for i, tag in enumerate(claim['tags']):
                    if not isinstance(tag, str):
                        self.error(f"{path}.tags[{i}]", "Must be a string")

    def check_implication(self, implication: Dict[str, Any], index: int) -> None:
        """Validate an implication."""
        path = f"implications[{index}]"

        if not isinstance(implication, dict):
            self.error(path, "Implication must be an object")
            return

        # Required: id
        if 'id' not in implication:
            self.error(path, "Missing required field 'id'")
        else:
            impl_id = implication['id']
            if not isinstance(impl_id, str):
                self.error(path, "'id' must be a string")
            else:
                # Check for duplicate IDs
                if impl_id in self.implication_ids:
                    self.error(path, f"Duplicate implication ID '{impl_id}'")
                self.implication_ids.add(impl_id)

        # Required: premises
        if 'premises' not in implication:
            self.error(path, "Missing required field 'premises'")
        else:
            premises = implication['premises']
            if not isinstance(premises, list):
                self.error(path, "'premises' must be a list")
            elif len(premises) == 0:
                self.error(path, "'premises' cannot be empty")
            else:
                for i, premise_id in enumerate(premises):
                    if not isinstance(premise_id, str):
                        self.error(f"{path}.premises[{i}]", "Premise ID must be a string")

        # Required: conclusion
        if 'conclusion' not in implication:
            self.error(path, "Missing required field 'conclusion'")
        elif not isinstance(implication['conclusion'], str):
            self.error(path, "'conclusion' must be a string")

        # Required: type
        if 'type' not in implication:
            self.error(path, "Missing required field 'type'")
        else:
            impl_type = implication['type']
            if impl_type not in ALLOWED_IMPLICATION_TYPES:
                self.error(
                    path,
                    f"Invalid implication type '{impl_type}'. "
                    f"Must be one of: {', '.join(sorted(ALLOWED_IMPLICATION_TYPES))}"
                )

        # Optional: reasoning
        if 'reasoning' in implication:
            if not isinstance(implication['reasoning'], str):
                self.error(path, "'reasoning' must be a string")
            elif len(implication['reasoning']) == 0:
                self.warning(path, "'reasoning' is empty")

    def check_references(self, implications: List[Dict[str, Any]]) -> None:
        """Validate that all premise/conclusion references exist."""
        for i, impl in enumerate(implications):
            path = f"implications[{i}]"

            # Check premises
            if 'premises' in impl and isinstance(impl['premises'], list):
                for j, premise_id in enumerate(impl['premises']):
                    if isinstance(premise_id, str) and premise_id not in self.claim_ids:
                        self.error(
                            f"{path}.premises[{j}]",
                            f"Reference to non-existent claim '{premise_id}'"
                        )

            # Check conclusion
            if 'conclusion' in impl and isinstance(impl['conclusion'], str):
                if impl['conclusion'] not in self.claim_ids:
                    self.error(
                        f"{path}.conclusion",
                        f"Reference to non-existent claim '{impl['conclusion']}'"
                    )

    def check_hypergraph(self, hypergraph_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Main entry point for type checking.
        Returns (errors, warnings).
        """
        # Check top-level structure
        if not isinstance(hypergraph_data, dict):
            self.error("root", "Hypergraph must be a JSON object")
            return self.errors, self.warnings

        # Check metadata
        if 'metadata' not in hypergraph_data:
            self.error("root", "Missing 'metadata' section")
        else:
            self.check_metadata(hypergraph_data['metadata'])

        # Check claims
        if 'claims' not in hypergraph_data:
            self.error("root", "Missing 'claims' array")
        else:
            claims = hypergraph_data['claims']
            if not isinstance(claims, list):
                self.error("claims", "Must be an array")
            else:
                for i, claim in enumerate(claims):
                    self.check_claim(claim, i)

        # Check implications
        if 'implications' not in hypergraph_data:
            self.error("root", "Missing 'implications' array")
        else:
            implications = hypergraph_data['implications']
            if not isinstance(implications, list):
                self.error("implications", "Must be an array")
            else:
                for i, impl in enumerate(implications):
                    self.check_implication(impl, i)

                # Check references after collecting all IDs
                self.check_references(implications)

        return self.errors, self.warnings


def typecheck_hypergraph(json_path: str) -> Tuple[List[str], List[str]]:
    """
    Type check an entailment hypergraph JSON file.
    Returns (errors, warnings).
    """
    try:
        with open(json_path, 'r') as f:
            hypergraph_data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"], []
    except FileNotFoundError:
        return [f"File not found: {json_path}"], []

    checker = HypergraphTypeChecker()
    return checker.check_hypergraph(hypergraph_data)


def typecheck_directory(directory: str) -> Dict[str, Tuple[List[str], List[str]]]:
    """
    Type check all JSON files in a directory.
    Returns dict mapping filename to (errors, warnings).
    """
    results = {}
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return results

    json_files = list(dir_path.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {directory}")
        return results

    for json_file in sorted(json_files):
        errors, warnings = typecheck_hypergraph(str(json_file))
        results[json_file.name] = (errors, warnings)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python typecheck_hypergraph.py <json_file_or_directory>")
        print()
        print("Examples:")
        print("  python typecheck_hypergraph.py entailment_hypergraph/steam_engine_example.json")
        print("  python typecheck_hypergraph.py entailment_hypergraph/")
        sys.exit(1)

    target = sys.argv[1]

    # Check if target is a directory or file
    target_path = Path(target)
    if target_path.is_dir():
        # Check all JSON files in directory
        print(f"Type checking all JSON files in: {target}\n")
        results = typecheck_directory(target)

        total_errors = 0
        total_warnings = 0
        failed_files = []

        for filename, (errors, warnings) in results.items():
            print(f"{'='*60}")
            print(f"File: {filename}")
            print(f"{'='*60}")

            if errors:
                print(f"❌ FAILED with {len(errors)} error(s):")
                for error in errors:
                    print(f"  ERROR: {error}")
                print()
                failed_files.append(filename)
                total_errors += len(errors)

            if warnings:
                print(f"⚠️  {len(warnings)} warning(s):")
                for warning in warnings:
                    print(f"  WARNING: {warning}")
                print()
                total_warnings += len(warnings)

            if not errors and not warnings:
                print("✓ PASSED")
                print()

        print(f"{'='*60}")
        print(f"Summary: {len(results)} file(s) checked")
        print(f"{'='*60}")
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")

        if failed_files:
            print(f"\n❌ Failed files: {', '.join(failed_files)}")
            sys.exit(1)
        else:
            if total_warnings > 0:
                print("\n✓ All files PASSED (with warnings)")
            else:
                print("\n✓ All files PASSED!")
            sys.exit(0)

    else:
        # Check single file
        errors, warnings = typecheck_hypergraph(target)

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
