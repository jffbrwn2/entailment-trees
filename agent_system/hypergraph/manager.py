"""
Hypergraph Manager - CRUD operations for entailment hypergraphs.

Handles creating, reading, updating, and validating hypergraph JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Claim:
    """Represents an atomic claim in the hypergraph."""
    id: str
    text: str
    score: float
    reasoning: str
    evidence: Optional[List[Dict[str, Any]]] = None
    uncertainties: Optional[List[str]] = None
    tags: Optional[List[str]] = None


@dataclass
class Implication:
    """Represents a logical implication (hyperedge)."""
    id: str
    premises: List[str]
    conclusion: str
    type: str  # "AND" or "OR"
    reasoning: str


class HypergraphManager:
    """Manages hypergraph JSON files with validation."""

    def __init__(self, approach_dir: Path):
        """
        Initialize manager for a specific approach.

        Args:
            approach_dir: Path to the approach folder
        """
        self.approach_dir = Path(approach_dir)
        self.hypergraph_path = self.approach_dir / "hypergraph.json"
        self.simulations_dir = self.approach_dir / "simulations"
        self.references_dir = self.approach_dir / "references"
        self.history_dir = self.approach_dir / ".hypergraph_history"

        # Ensure directories exist
        self.approach_dir.mkdir(parents=True, exist_ok=True)
        self.simulations_dir.mkdir(exist_ok=True)
        self.references_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)

    def create_approach(self, name: str, initial_claim: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new approach with initial hypergraph.

        Args:
            name: Name of the approach
            initial_claim: The hypothesis/claim to evaluate
            description: Optional description

        Returns:
            The created hypergraph data
        """
        hypergraph = {
            "metadata": {
                "name": name,
                "description": description or initial_claim,
                "created": datetime.now().strftime("%Y-%m-%d"),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0"
            },
            "claims": [
                {
                    "id": "hypothesis",
                    "text": initial_claim,
                    "score": 5.0,  # Neutral starting point
                    "reasoning": "Initial hypothesis to be evaluated",
                    "uncertainties": ["Not yet investigated"],
                    "tags": ["HYPOTHESIS"]
                }
            ],
            "implications": []
        }

        self._save_hypergraph(hypergraph)
        self._create_readme(name, initial_claim)
        self._update_catalog(name)

        return hypergraph

    def load_hypergraph(self) -> Dict[str, Any]:
        """Load the hypergraph from JSON file."""
        if not self.hypergraph_path.exists():
            raise FileNotFoundError(f"Hypergraph not found at {self.hypergraph_path}")

        with open(self.hypergraph_path, 'r') as f:
            return json.load(f)

    def _save_hypergraph(self, hypergraph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save hypergraph to JSON file with pretty formatting and version history.

        Returns:
            Dict with 'errors' and 'warnings' from validation
        """
        # Update last_updated timestamp
        hypergraph['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")

        # Always compute and update costs before saving
        costs = self.calculate_costs(hypergraph)
        for claim in hypergraph.get('claims', []):
            claim_id = claim['id']
            if claim_id in costs:
                value = costs[claim_id]
                # Store Infinity as string for valid JSON
                if value == float('inf'):
                    claim['cost'] = "Infinity"
                elif value == float('-inf'):
                    claim['cost'] = "-Infinity"
                else:
                    claim['cost'] = value

        # Save to history before overwriting
        if self.hypergraph_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            history_file = self.history_dir / f"hypergraph_{timestamp}.json"

            # Copy current version to history
            with open(self.hypergraph_path, 'r') as f:
                current = json.load(f)
            with open(history_file, 'w') as f:
                json.dump(current, f, indent=2)

        # Run validation before saving
        from .typecheck import HypergraphTypeChecker
        checker = HypergraphTypeChecker(base_path=self.approach_dir)
        errors, warnings = checker.check_hypergraph(hypergraph)

        # Store validation results in metadata
        hypergraph['metadata']['validation'] = {
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0,
            'checked_at': datetime.now().isoformat()
        }

        # Save new version
        with open(self.hypergraph_path, 'w') as f:
            json.dump(hypergraph, f, indent=2)

        return {'errors': errors, 'warnings': warnings}

    def add_claim(self, claim: Claim) -> Dict[str, Any]:
        """
        Add a new claim to the hypergraph.

        Args:
            claim: Claim object to add

        Returns:
            Dict with 'id' and 'validation' results
        """
        hypergraph = self.load_hypergraph()

        # Check for duplicate ID
        existing_ids = {c['id'] for c in hypergraph['claims']}
        if claim.id in existing_ids:
            raise ValueError(f"Claim ID '{claim.id}' already exists")

        # Convert to dict, excluding None values
        timestamp = datetime.now().isoformat()
        claim_dict = {
            "id": claim.id,
            "text": claim.text,
            "score": claim.score if claim.score is not None else 0.0,
            "reasoning": claim.reasoning,
            "created_at": timestamp,
            "modified_at": timestamp
        }

        if claim.evidence:
            claim_dict["evidence"] = claim.evidence
        if claim.uncertainties:
            claim_dict["uncertainties"] = claim.uncertainties
        if claim.tags:
            claim_dict["tags"] = claim.tags

        hypergraph['claims'].append(claim_dict)
        validation = self._save_hypergraph(hypergraph)

        return {'id': claim.id, 'validation': validation}

    def update_claim(self, claim_id: str, **updates) -> Dict[str, Any]:
        """
        Update an existing claim.

        Args:
            claim_id: ID of claim to update
            **updates: Fields to update (score, reasoning, evidence, etc.)

        Returns:
            Dict with 'validation' results
        """
        hypergraph = self.load_hypergraph()

        # Find the claim
        claim = None
        for c in hypergraph['claims']:
            if c['id'] == claim_id:
                claim = c
                break

        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found")

        # Update fields
        for key, value in updates.items():
            if value is not None:
                claim[key] = value

        # Update modified timestamp
        claim['modified_at'] = datetime.now().isoformat()

        validation = self._save_hypergraph(hypergraph)
        return {'validation': validation}

    def add_implication(self, implication: Implication) -> Dict[str, Any]:
        """
        Add a logical implication (hyperedge).

        Args:
            implication: Implication object to add

        Returns:
            Dict with 'id' and 'validation' results
        """
        hypergraph = self.load_hypergraph()

        # Check for duplicate ID
        existing_ids = {i['id'] for i in hypergraph['implications']}
        if implication.id in existing_ids:
            raise ValueError(f"Implication ID '{implication.id}' already exists")

        # Verify that premise and conclusion IDs exist
        claim_ids = {c['id'] for c in hypergraph['claims']}
        for premise in implication.premises:
            if premise not in claim_ids:
                raise ValueError(f"Premise claim '{premise}' does not exist")
        if implication.conclusion not in claim_ids:
            raise ValueError(f"Conclusion claim '{implication.conclusion}' does not exist")

        # Add implication
        timestamp = datetime.now().isoformat()
        impl_dict = {
            "id": implication.id,
            "premises": implication.premises,
            "conclusion": implication.conclusion,
            "type": implication.type,
            "reasoning": implication.reasoning,
            "created_at": timestamp,
            "last_checked": None  # Will be set when first checked
        }

        hypergraph['implications'].append(impl_dict)
        validation = self._save_hypergraph(hypergraph)

        return {'id': implication.id, 'validation': validation}

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Get a claim by ID."""
        hypergraph = self.load_hypergraph()
        for claim in hypergraph['claims']:
            if claim['id'] == claim_id:
                return claim
        return None

    def delete_claim(self, claim_id: str) -> Dict[str, Any]:
        """
        Delete a claim and its related implications.

        Args:
            claim_id: ID of the claim to delete

        Returns:
            Dict with 'deleted_claim' and 'deleted_implications' lists

        Raises:
            ValueError: If claim doesn't exist or is the hypothesis
        """
        if claim_id == 'hypothesis':
            raise ValueError("Cannot delete the hypothesis node")

        hypergraph = self.load_hypergraph()

        # Check claim exists
        claim_exists = any(c['id'] == claim_id for c in hypergraph['claims'])
        if not claim_exists:
            raise ValueError(f"Claim '{claim_id}' not found")

        # Remove the claim
        deleted_claim = None
        for c in hypergraph['claims']:
            if c['id'] == claim_id:
                deleted_claim = c
                break
        hypergraph['claims'] = [c for c in hypergraph['claims'] if c['id'] != claim_id]

        # Remove implications where this claim is premise or conclusion
        deleted_implications = []
        remaining_implications = []
        for impl in hypergraph.get('implications', []):
            if claim_id in impl.get('premises', []) or impl.get('conclusion') == claim_id:
                deleted_implications.append(impl)
            else:
                remaining_implications.append(impl)
        hypergraph['implications'] = remaining_implications

        validation = self._save_hypergraph(hypergraph)

        return {
            'deleted_claim': deleted_claim,
            'deleted_implications': deleted_implications,
            'validation': validation
        }

    def get_all_claims(self) -> List[Dict[str, Any]]:
        """Get all claims."""
        hypergraph = self.load_hypergraph()
        return hypergraph['claims']

    def get_all_implications(self) -> List[Dict[str, Any]]:
        """Get all implications."""
        hypergraph = self.load_hypergraph()
        return hypergraph['implications']

    def validate(self) -> Tuple[List[str], List[str]]:
        """
        Validate hypergraph structure and types.

        Returns:
            Tuple of (errors, warnings)
        """
        try:
            from .typecheck import typecheck_hypergraph
            return typecheck_hypergraph(str(self.hypergraph_path))
        except Exception as e:
            return [f"Validation failed: {str(e)}"], []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the hypergraph."""
        hypergraph = self.load_hypergraph()

        claims = hypergraph['claims']
        implications = hypergraph['implications']

        scores = [c.get('score', 0) for c in claims if c.get('score') is not None]

        return {
            "num_claims": len(claims),
            "num_implications": len(implications),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "claims_with_evidence": sum(1 for c in claims if c.get('evidence')),
            "critical_blockers": sum(1 for c in claims if 'CRITICAL_BLOCKER' in c.get('tags', []))
        }

    def _create_readme(self, name: str, claim: str) -> None:
        """Create initial README for the approach."""
        readme_path = self.approach_dir / "README.md"

        content = f"""# {name}

## Hypothesis

{claim}

## Status

Under investigation - hypergraph being developed.

## Files

- `hypergraph.json` - Entailment hypergraph with claims, implications, and evidence
- `simulations/` - Python simulations testing key assumptions

## Visualization

To view the hypergraph interactively:

```bash
cd ../..
python -m http.server 8765
# Open: http://localhost:8765/entailment_hypergraph/?graph=approaches/{self.approach_dir.name}/hypergraph.json
```

## Created

{datetime.now().strftime("%Y-%m-%d")}
"""

        with open(readme_path, 'w') as f:
            f.write(content)

    def _update_catalog(self, name: str) -> None:
        """Regenerate catalog by scanning filesystem."""
        try:
            from .catalog import update_catalog
            update_catalog()
        except Exception:
            # Non-critical - catalog will be updated on next manual run
            pass

    def remove_unreachable_nodes(self) -> List[str]:
        """
        Remove claims that are not in the causal chain leading to the hypothesis.

        A claim is kept only if:
        - It is the hypothesis itself, OR
        - It is used as a premise in the chain leading to the hypothesis

        This removes both:
        1. Completely disconnected claims
        2. "Dangling conclusions" - claims that can be derived but are never used

        Returns:
            List of removed claim IDs
        """
        hypergraph = self.load_hypergraph()

        # Build reverse implication map: conclusion -> premises
        conclusion_to_premises = {}
        for impl in hypergraph.get('implications', []):
            conclusion = impl.get('conclusion')
            premises = impl.get('premises', [])
            if conclusion:
                if conclusion not in conclusion_to_premises:
                    conclusion_to_premises[conclusion] = []
                conclusion_to_premises[conclusion].extend(premises)

        # Perform backward reachability search from hypothesis
        # ONLY traverse through premises, not conclusions
        needed = set()
        to_visit = ['hypothesis']

        while to_visit:
            current = to_visit.pop()
            if current in needed:
                continue

            needed.add(current)

            # Add all premises that support this conclusion
            if current in conclusion_to_premises:
                for premise in conclusion_to_premises[current]:
                    if premise not in needed:
                        to_visit.append(premise)

        # Find unneeded claims
        unneeded = []
        claims = hypergraph.get('claims', [])
        for claim in claims:
            claim_id = claim.get('id')
            if claim_id not in needed:
                unneeded.append(claim_id)

        # Remove unneeded claims and their implications
        if unneeded:
            hypergraph['claims'] = [
                c for c in claims if c.get('id') not in unneeded
            ]

            # Also remove implications that conclude to unneeded claims
            hypergraph['implications'] = [
                i for i in hypergraph.get('implications', [])
                if i.get('conclusion') not in unneeded
            ]

            self._save_hypergraph(hypergraph)

        return unneeded

    def generate_next_id(self, prefix: str) -> str:
        """
        Generate next available ID with given prefix.

        Args:
            prefix: Prefix for ID (e.g., 'c' for claims, 'i' for implications)

        Returns:
            Next available ID like 'c1', 'c2', etc.
        """
        hypergraph = self.load_hypergraph()

        if prefix == 'c':
            existing = [c['id'] for c in hypergraph['claims'] if c['id'].startswith('c')]
        elif prefix == 'i':
            existing = [i['id'] for i in hypergraph['implications'] if i['id'].startswith('i')]
        else:
            existing = []

        # Extract numbers and find max
        numbers = []
        for item_id in existing:
            try:
                num = int(item_id[len(prefix):])
                numbers.append(num)
            except ValueError:
                continue

        next_num = max(numbers) + 1 if numbers else 1
        return f"{prefix}{next_num}"

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get list of historical versions.

        Returns:
            List of dicts with 'timestamp', 'filename', and 'path' for each version
        """
        history_files = sorted(self.history_dir.glob("hypergraph_*.json"))

        versions = []
        for file_path in history_files:
            # Parse timestamp from filename: hypergraph_20250122_143052_123456.json
            filename = file_path.name
            timestamp_str = filename.replace("hypergraph_", "").replace(".json", "")

            # Convert to readable format
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                readable = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                readable = timestamp_str

            versions.append({
                "timestamp": readable,
                "filename": filename,
                "path": str(file_path)
            })

        return versions

    def restore_version(self, history_filename: str) -> Dict[str, Any]:
        """
        Restore a historical version of the hypergraph.

        Args:
            history_filename: Filename from history (e.g., "hypergraph_20250122_143052_123456.json")

        Returns:
            The restored hypergraph data

        Raises:
            FileNotFoundError: If history file doesn't exist
        """
        history_file = self.history_dir / history_filename

        if not history_file.exists():
            raise FileNotFoundError(f"History file not found: {history_filename}")

        # Load historical version
        with open(history_file, 'r') as f:
            historical_hypergraph = json.load(f)

        # Save current version to history first (so we don't lose it)
        # Then overwrite with historical version
        self._save_hypergraph(historical_hypergraph)

        return historical_hypergraph

    def calculate_costs(self, hypergraph: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Calculate cost scores for all claims.

        For leaf nodes WITH evidence: cost = -log2(score/10)
        For leaf nodes WITHOUT evidence: cost = None (not yet evaluated)
        For AND nodes: cost = sum(children_cost) + entailment_penalty
                       If any child is None, result is None
        For OR nodes: cost = min(children_cost) + entailment_penalty
                      Ignores None children; if all are None, result is None

        The entailment_penalty is:
        - +Infinity if entailment_status == 'failed' (truth cannot propagate through invalid logic)
        - 0 if entailment_status == 'passed' or not yet checked

        Args:
            hypergraph: Optional hypergraph dict. If None, loads from disk.

        Returns:
            Dict mapping claim_id -> cost value (None for unevaluated claims)
        """
        import math

        if hypergraph is None:
            hypergraph = self.load_hypergraph()
        claims = hypergraph.get('claims', [])
        implications = hypergraph.get('implications', [])

        # Build conclusion->implication map
        conclusion_to_implication = {}
        for impl in implications:
            conclusion_id = impl.get('conclusion')
            premise_ids = impl.get('premises', [])
            impl_type = impl.get('type', 'AND')
            entailment_status = impl.get('entailment_status')  # 'passed', 'failed', or None

            conclusion_to_implication[conclusion_id] = {
                'premises': premise_ids,
                'type': impl_type,
                'entailment_status': entailment_status
            }

        # Calculate costs using topological sort (bottom-up)
        # Values can be: float (computed cost), None (not evaluated), or float('inf') (failed)
        costs = {}
        visited = set()

        def calculate_node(claim_id):
            if claim_id in visited:
                return costs[claim_id]

            visited.add(claim_id)

            # Find the claim
            claim = None
            for c in claims:
                if c['id'] == claim_id:
                    claim = c
                    break

            if not claim:
                # Claim not found, return default
                costs[claim_id] = float('inf')
                return float('inf')

            score = claim.get('score')
            evidence = claim.get('evidence', [])

            # Check if this is a leaf node (not a conclusion of any implication)
            if claim_id not in conclusion_to_implication:
                # Leaf node: only compute cost if it has evidence
                if not evidence:
                    # No evidence = not yet evaluated
                    costs[claim_id] = None
                    return None

                # Has evidence: -log2(score/10)
                effective_score = score if score is not None else 5
                # Score <= 0 means definitely false = infinite cost
                if effective_score <= 0:
                    node_cost = float('inf')
                else:
                    node_cost = -math.log2(effective_score / 10.0)
                costs[claim_id] = node_cost
                return node_cost

            # Non-leaf node: get children and aggregate
            impl_info = conclusion_to_implication[claim_id]
            premise_ids = impl_info['premises']
            impl_type = impl_info['type']
            entailment_status = impl_info['entailment_status']

            # Recursively calculate children
            children_costs = []
            for premise_id in premise_ids:
                child_cost = calculate_node(premise_id)
                children_costs.append(child_cost)

            # Aggregate based on type, handling None (unevaluated) children
            if impl_type == 'AND':
                # AND: sum of children costs
                # If any child is None, we can't compute the AND result
                if any(c is None for c in children_costs):
                    node_cost = None
                else:
                    node_cost = sum(children_costs)
            elif impl_type == 'OR':
                # OR: min of children costs (best/most likely premise wins)
                # Filter out None values - we only need ONE evaluated path
                evaluated_costs = [c for c in children_costs if c is not None]
                if not evaluated_costs:
                    # All children are unevaluated
                    node_cost = None
                else:
                    node_cost = min(evaluated_costs)
            else:
                # Unknown type, treat as AND
                if any(c is None for c in children_costs):
                    node_cost = None
                else:
                    node_cost = sum(children_costs)

            # Apply entailment penalty: if implication is invalid, truth cannot propagate
            if entailment_status == 'failed' and node_cost is not None:
                node_cost = float('inf')

            costs[claim_id] = node_cost
            return node_cost

        # Calculate for all claims
        for claim in claims:
            calculate_node(claim['id'])

        return costs

    def update_costs(self) -> None:
        """
        Calculate and update cost field for all claims.
        """
        costs = self.calculate_costs()
        hypergraph = self.load_hypergraph()

        # Update each claim with its cost
        for claim in hypergraph['claims']:
            claim_id = claim['id']
            if claim_id in costs:
                claim['cost'] = costs[claim_id]

        self._save_hypergraph(hypergraph)
