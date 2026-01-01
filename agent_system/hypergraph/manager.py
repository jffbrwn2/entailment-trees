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
        self.apply_costs_to_claims(hypergraph)

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

        If text is changed, all connected implications are marked as unevaluated.

        Args:
            claim_id: ID of claim to update
            **updates: Fields to update (text, uncertainties, tags - NOT reasoning/score)

        Returns:
            Dict with 'validation' results and 'invalidated_implications' list
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

        # Check if text is being changed
        text_changed = 'text' in updates and updates['text'] != claim.get('text')

        # Update fields
        for key, value in updates.items():
            if value is not None:
                claim[key] = value

        # Update modified timestamp
        claim['modified_at'] = datetime.now().isoformat()

        # If text changed, mark connected implications as unevaluated
        invalidated_implications = []
        if text_changed:
            for impl in hypergraph.get('implications', []):
                if claim_id in impl.get('premises', []) or impl.get('conclusion') == claim_id:
                    impl['entailment_status'] = None
                    impl['last_checked'] = None
                    impl['entailment_explanation'] = None
                    invalidated_implications.append(impl['id'])

        validation = self._save_hypergraph(hypergraph)
        return {
            'validation': validation,
            'invalidated_implications': invalidated_implications
        }

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
        Delete a claim and update related implications.

        - If claim is a CONCLUSION of an implication → delete the implication
        - If claim is a PREMISE of an implication → remove from premises, mark unevaluated

        Args:
            claim_id: ID of the claim to delete

        Returns:
            Dict with 'deleted_claim', 'deleted_implications', and 'updated_implications'

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

        # Handle implications:
        # - Delete if claim is conclusion
        # - Update (remove premise, mark unevaluated) if claim is premise
        deleted_implications = []
        updated_implications = []
        remaining_implications = []

        for impl in hypergraph.get('implications', []):
            if impl.get('conclusion') == claim_id:
                # Claim is conclusion → delete entire implication
                deleted_implications.append(impl)
            elif claim_id in impl.get('premises', []):
                # Claim is premise → remove from premises and mark unevaluated
                impl['premises'] = [p for p in impl['premises'] if p != claim_id]
                impl['entailment_status'] = None
                impl['last_checked'] = None
                impl['entailment_explanation'] = None
                updated_implications.append(impl['id'])
                remaining_implications.append(impl)
            else:
                remaining_implications.append(impl)

        hypergraph['implications'] = remaining_implications

        validation = self._save_hypergraph(hypergraph)

        return {
            'deleted_claim': deleted_claim,
            'deleted_implications': deleted_implications,
            'updated_implications': updated_implications,
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

    def delete_implication(self, implication_id: str) -> Dict[str, Any]:
        """
        Delete an implication from the hypergraph.

        Args:
            implication_id: ID of the implication to delete

        Returns:
            Dict with 'deleted_implication' and 'validation' results

        Raises:
            ValueError: If implication doesn't exist
        """
        hypergraph = self.load_hypergraph()

        # Find and remove the implication
        deleted_implication = None
        remaining_implications = []

        for impl in hypergraph.get('implications', []):
            if impl['id'] == implication_id:
                deleted_implication = impl
            else:
                remaining_implications.append(impl)

        if deleted_implication is None:
            raise ValueError(f"Implication '{implication_id}' not found")

        hypergraph['implications'] = remaining_implications
        validation = self._save_hypergraph(hypergraph)

        return {
            'deleted_implication': deleted_implication,
            'validation': validation
        }

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

    @staticmethod
    def _serialize_cost(value: Optional[float]) -> Any:
        """Serialize a cost value for JSON (handles Infinity)."""
        if value is None:
            return None
        elif value == float('inf'):
            return "Infinity"
        elif value == float('-inf'):
            return "-Infinity"
        else:
            return value

    def apply_costs_to_claims(self, hypergraph: Dict[str, Any]) -> None:
        """
        Calculate and apply all cost components to claims in-place.

        Modifies the hypergraph dict directly, adding to each claim:
        - evidence_epistemic_cost: -log2(score/10) from evidence
        - experimental_epistemic_cost: 0 if testable, Infinity if not
        - cost: total (sum of both components)
        """
        costs = self.calculate_costs(hypergraph)
        for claim in hypergraph.get('claims', []):
            claim_id = claim['id']
            if claim_id in costs:
                cost_data = costs[claim_id]
                claim['evidence_epistemic_cost'] = self._serialize_cost(cost_data['evidence_epistemic_cost'])
                claim['experimental_epistemic_cost'] = self._serialize_cost(cost_data['experimental_epistemic_cost'])
                claim['cost'] = self._serialize_cost(cost_data['cost'])

    def calculate_costs(self, hypergraph: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Optional[float]]]:
        """
        Calculate cost scores for all claims.

        Cost has two components for leaf nodes:
        - evidence_epistemic_cost = -log2(score/10) based on evidence strength
        - experimental_epistemic_cost = 0 if testability=1, infinity if testability=0 or not evaluated
        - total cost = evidence_epistemic_cost + experimental_epistemic_cost

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
            Dict mapping claim_id -> {evidence_epistemic_cost, experimental_epistemic_cost, cost}
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
                # Return just the total cost for aggregation, not the full dict
                return costs[claim_id]['cost']

            visited.add(claim_id)

            # Find the claim
            claim = None
            for c in claims:
                if c['id'] == claim_id:
                    claim = c
                    break

            if not claim:
                # Claim not found, return default
                costs[claim_id] = {
                    'evidence_epistemic_cost': float('inf'),
                    'experimental_epistemic_cost': float('inf'),
                    'cost': float('inf')
                }
                return float('inf')

            score = claim.get('score')
            evidence = claim.get('evidence', [])
            testability = claim.get('testability')  # 0, 1, or None (not evaluated)

            # Check if this is a leaf node (not a conclusion of any implication)
            if claim_id not in conclusion_to_implication:
                # Leaf node: only compute cost if it has evidence
                if not evidence:
                    # No evidence = not yet evaluated
                    costs[claim_id] = {
                        'evidence_epistemic_cost': None,
                        'experimental_epistemic_cost': None,
                        'cost': None
                    }
                    return None

                # Evidence epistemic cost: -log2(score/10)
                effective_score = score if score is not None else 5
                if effective_score <= 0:
                    evidence_cost = float('inf')
                else:
                    evidence_cost = -math.log2(effective_score / 10.0)

                # Experimental epistemic cost: 0 if testable, infinity if not
                # testability=1 means there's an experiment that could resolve this
                if testability == 1:
                    experimental_cost = 0.0
                else:
                    # Not testable or not yet evaluated = infinite cost
                    experimental_cost = float('inf')

                total_cost = evidence_cost + experimental_cost
                costs[claim_id] = {
                    'evidence_epistemic_cost': evidence_cost,
                    'experimental_epistemic_cost': experimental_cost,
                    'cost': total_cost
                }
                return total_cost

            # Non-leaf node: get children and aggregate
            impl_info = conclusion_to_implication[claim_id]
            premise_ids = impl_info['premises']
            impl_type = impl_info['type']
            entailment_status = impl_info['entailment_status']

            # Recursively calculate children (returns total cost, but we need full cost data)
            for premise_id in premise_ids:
                calculate_node(premise_id)

            # Get full cost data for children
            children_data = [costs.get(p, {}) for p in premise_ids]

            # Aggregate based on type, handling None (unevaluated) children
            if impl_type == 'AND':
                # AND: sum of all children's costs (need all to be evaluated)
                evidence_costs = [d.get('evidence_epistemic_cost') for d in children_data]
                experimental_costs = [d.get('experimental_epistemic_cost') for d in children_data]

                if any(c is None for c in evidence_costs):
                    evidence_cost = None
                else:
                    evidence_cost = sum(evidence_costs)

                if any(c is None for c in experimental_costs):
                    experimental_cost = None
                else:
                    experimental_cost = sum(experimental_costs)

            elif impl_type == 'OR':
                # OR: use the best (minimum total cost) child's costs
                # Filter to children with evaluated total cost
                evaluated_children = [
                    d for d in children_data
                    if d.get('cost') is not None
                ]
                if not evaluated_children:
                    evidence_cost = None
                    experimental_cost = None
                else:
                    # Find child with minimum total cost
                    best_child = min(evaluated_children, key=lambda d: d.get('cost', float('inf')))
                    evidence_cost = best_child.get('evidence_epistemic_cost')
                    experimental_cost = best_child.get('experimental_epistemic_cost')
            else:
                # Unknown type, treat as AND
                evidence_costs = [d.get('evidence_epistemic_cost') for d in children_data]
                experimental_costs = [d.get('experimental_epistemic_cost') for d in children_data]

                if any(c is None for c in evidence_costs):
                    evidence_cost = None
                else:
                    evidence_cost = sum(evidence_costs)

                if any(c is None for c in experimental_costs):
                    experimental_cost = None
                else:
                    experimental_cost = sum(experimental_costs)

            # Calculate total cost
            if evidence_cost is None or experimental_cost is None:
                node_cost = None
            else:
                node_cost = evidence_cost + experimental_cost

            # Apply entailment penalty: if implication is invalid, truth cannot propagate
            if entailment_status == 'failed' and node_cost is not None:
                node_cost = float('inf')
                evidence_cost = float('inf')
                experimental_cost = float('inf')

            costs[claim_id] = {
                'evidence_epistemic_cost': evidence_cost,
                'experimental_epistemic_cost': experimental_cost,
                'cost': node_cost
            }
            return node_cost

        # Calculate for all claims
        for claim in claims:
            calculate_node(claim['id'])

        return costs

    def update_costs(self) -> None:
        """
        Calculate and update all cost fields for all claims.
        """
        hypergraph = self.load_hypergraph()
        self.apply_costs_to_claims(hypergraph)
        self._save_hypergraph(hypergraph)

    def compute_warnings(self, hypergraph: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Compute warnings for the hypergraph.

        Checks for:
        - Leaf nodes without evidence
        - Leaf nodes with evidence but missing testability evaluation
        - Failed entailments
        - Unchecked entailments

        Args:
            hypergraph: Optional hypergraph dict. If None, loads from disk.

        Returns:
            List of warning strings
        """
        if hypergraph is None:
            hypergraph = self.load_hypergraph()

        warnings = []

        # Find claims that are conclusions of implications (non-leaf nodes)
        conclusions = set(impl.get('conclusion') for impl in hypergraph.get('implications', []))

        # Check leaf nodes for missing evidence or testability
        for claim in hypergraph.get('claims', []):
            claim_id = claim.get('id')
            is_leaf = claim_id not in conclusions
            if is_leaf:
                evidence = claim.get('evidence', [])
                if not evidence:
                    warnings.append(f"{claim_id}: Leaf node without evidence")
                elif claim.get('testability') is None:
                    warnings.append(f"{claim_id}: Testability not evaluated")

        # Check implications for entailment status
        for impl in hypergraph.get('implications', []):
            impl_id = impl.get('id')
            status = impl.get('entailment_status')
            if status == 'failed':
                warnings.append(f"{impl_id}: Entailment failed")
            elif not status:
                warnings.append(f"{impl_id}: Entailment not checked")

        return warnings

    def get_summary_view(self) -> Dict[str, Any]:
        """
        Return hypergraph with minimal claim fields for navigation.

        This returns a truncated view suitable for understanding tree structure
        without overwhelming context. Evidence details are omitted.

        For each claim, keeps: id, text, cost components
        Removes: score, tags, evidence, uncertainties, timestamps, testability details

        Returns:
            Dict with metadata, truncated claims, implications, and warnings
        """
        hypergraph = self.load_hypergraph()

        # Truncate claims - keep only essential navigation fields
        truncated_claims = []
        for claim in hypergraph.get('claims', []):
            truncated_claim = {
                'id': claim.get('id'),
                'text': claim.get('text'),
                'evidence_epistemic_cost': claim.get('evidence_epistemic_cost'),
                'experimental_epistemic_cost': claim.get('experimental_epistemic_cost'),
                'cost': claim.get('cost')
            }
            truncated_claims.append(truncated_claim)

        return {
            'metadata': hypergraph.get('metadata', {}),
            'claims': truncated_claims,
            'implications': hypergraph.get('implications', []),
            'warnings': self.compute_warnings(hypergraph),
            'notes': self.get_notes_for_context()
        }

    def get_claim_evidence(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full evidence details for a specific claim.

        Args:
            claim_id: ID of the claim (e.g., "c1", "hypothesis")

        Returns:
            Dict with claim id, text, and evidence array, or None if not found
        """
        hypergraph = self.load_hypergraph()

        for claim in hypergraph.get('claims', []):
            if claim.get('id') == claim_id:
                return {
                    'id': claim.get('id'),
                    'text': claim.get('text'),
                    'evidence': claim.get('evidence', [])
                }

        return None

    def load_notes(self) -> Dict[str, Any]:
        """
        Load notes from notes.json file.

        Returns:
            Dict mapping claim/implication IDs to note data, or empty dict if no notes file
        """
        notes_path = self.approach_dir / "notes.json"
        if notes_path.exists():
            with open(notes_path) as f:
                data = json.load(f)
                return data.get("notes", {})
        return {}

    def get_notes_for_context(self) -> List[Dict[str, Any]]:
        """
        Get notes formatted for inclusion in agent context.

        Enriches notes with status (item_exists, content_changed) and returns
        a list suitable for display to agents.

        Returns:
            List of note dicts with id, text, original_content, content_changed
        """
        notes = self.load_notes()
        if not notes:
            return []

        hypergraph = self.load_hypergraph()
        enriched_notes = []

        for item_id, note_data in notes.items():
            # Check if item still exists and if content changed
            current_content = None
            for claim in hypergraph.get("claims", []):
                if claim.get("id") == item_id:
                    current_content = claim.get("text", "")
                    break

            if current_content is None:
                for impl in hypergraph.get("implications", []):
                    if impl.get("id") == item_id:
                        current_content = f"({', '.join(impl['premises'])}) → {impl['conclusion']}"
                        break

            item_exists = current_content is not None
            content_changed = item_exists and current_content != note_data.get("original_content", "")

            if item_exists:  # Only include notes for items that still exist
                enriched_notes.append({
                    "id": item_id,
                    "note": note_data.get("text", ""),
                    "content_changed": content_changed
                })

        return enriched_notes
