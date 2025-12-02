"""
Hypergraph Manager - CRUD operations for entailment hypergraphs.

Handles creating, reading, updating, and validating hypergraph JSON files.
"""

import json
import subprocess
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
                "description": description or f"Evaluating: {initial_claim}",
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

    def _save_hypergraph(self, hypergraph: Dict[str, Any]) -> None:
        """Save hypergraph to JSON file with pretty formatting and version history."""
        # Update last_updated timestamp
        hypergraph['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")

        # Always compute and update propagated negative logs before saving
        propagated_logs = self.calculate_propagated_negative_logs(hypergraph)
        for claim in hypergraph.get('claims', []):
            claim_id = claim['id']
            if claim_id in propagated_logs:
                claim['propagated_negative_log'] = propagated_logs[claim_id]

        # Save to history before overwriting
        if self.hypergraph_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            history_file = self.history_dir / f"hypergraph_{timestamp}.json"

            # Copy current version to history
            with open(self.hypergraph_path, 'r') as f:
                current = json.load(f)
            with open(history_file, 'w') as f:
                json.dump(current, f, indent=2)

        # Save new version
        with open(self.hypergraph_path, 'w') as f:
            json.dump(hypergraph, f, indent=2)

    def add_claim(self, claim: Claim) -> str:
        """
        Add a new claim to the hypergraph.

        Args:
            claim: Claim object to add

        Returns:
            The claim ID
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
        self._save_hypergraph(hypergraph)

        return claim.id

    def update_claim(self, claim_id: str, **updates) -> None:
        """
        Update an existing claim.

        Args:
            claim_id: ID of claim to update
            **updates: Fields to update (score, reasoning, evidence, etc.)
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

        self._save_hypergraph(hypergraph)

    def add_implication(self, implication: Implication) -> str:
        """
        Add a logical implication (hyperedge).

        Args:
            implication: Implication object to add

        Returns:
            The implication ID
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
        self._save_hypergraph(hypergraph)

        return implication.id

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Get a claim by ID."""
        hypergraph = self.load_hypergraph()
        for claim in hypergraph['claims']:
            if claim['id'] == claim_id:
                return claim
        return None

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
        Validate hypergraph using typecheck_hypergraph.py.

        Returns:
            Tuple of (errors, warnings)
        """
        try:
            result = subprocess.run(
                ['python', 'typecheck_hypergraph.py', str(self.hypergraph_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse output for errors and warnings
            errors = []
            warnings = []

            for line in result.stdout.split('\n'):
                if 'ERROR:' in line:
                    errors.append(line.strip())
                elif 'WARNING:' in line:
                    warnings.append(line.strip())

            return errors, warnings

        except subprocess.TimeoutExpired:
            return ["Validation timed out"], []
        except Exception as e:
            return [f"Validation failed: {str(e)}"], []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the hypergraph."""
        hypergraph = self.load_hypergraph()

        claims = hypergraph['claims']
        implications = hypergraph['implications']

        scores = [c.get('score', 0) for c in claims]

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
        # Run the update_catalog.py script to auto-generate from filesystem
        update_script = Path(__file__).parent.parent / "update_catalog.py"

        try:
            subprocess.run(
                ['python', str(update_script)],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
        except Exception as e:
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

    def calculate_propagated_negative_logs(self, hypergraph: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Calculate propagated negative log scores for all claims.

        For leaf nodes: propagated_negative_log = -log2(score/10)
        For AND nodes: propagated_negative_log = sum(children_propagated_negative_log)
        For OR nodes: propagated_negative_log = min(children_propagated_negative_log)

        Args:
            hypergraph: Optional hypergraph dict. If None, loads from disk.

        Returns:
            Dict mapping claim_id -> propagated_negative_log value
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

            conclusion_to_implication[conclusion_id] = {
                'premises': premise_ids,
                'type': impl_type
            }

        # Calculate propagated negative logs using topological sort (bottom-up)
        propagated_logs = {}
        visited = set()

        def calculate_node(claim_id):
            if claim_id in visited:
                return propagated_logs[claim_id]

            visited.add(claim_id)

            # Find the claim
            claim = None
            for c in claims:
                if c['id'] == claim_id:
                    claim = c
                    break

            if not claim:
                # Claim not found, return default
                propagated_logs[claim_id] = float('inf')
                return float('inf')

            score = claim.get('score')

            # Check if this is a leaf node (not a conclusion of any implication)
            if claim_id not in conclusion_to_implication:
                # Leaf node: -log2(score/10)
                # Handle null/None scores as unevaluated (infinite uncertainty)
                if score is None or score <= 0:
                    neg_log = float('inf')
                else:
                    neg_log = -math.log2(score / 10.0)
                propagated_logs[claim_id] = neg_log
                return neg_log

            # Non-leaf node: get children and aggregate
            impl_info = conclusion_to_implication[claim_id]
            premise_ids = impl_info['premises']
            impl_type = impl_info['type']

            # Recursively calculate children
            children_logs = []
            for premise_id in premise_ids:
                child_log = calculate_node(premise_id)
                children_logs.append(child_log)

            # Aggregate based on type
            if impl_type == 'AND':
                # AND: sum of children negative logs
                propagated_log = sum(children_logs)
            elif impl_type == 'OR':
                # OR: min of children negative logs (best/most likely premise wins)
                propagated_log = min(children_logs) if children_logs else float('inf')
            else:
                # Unknown type, treat as AND
                propagated_log = sum(children_logs)

            propagated_logs[claim_id] = propagated_log
            return propagated_log

        # Calculate for all claims
        for claim in claims:
            calculate_node(claim['id'])

        return propagated_logs

    def update_propagated_negative_logs(self) -> None:
        """
        Calculate and update propagated_negative_log field for all claims.
        """
        propagated_logs = self.calculate_propagated_negative_logs()
        hypergraph = self.load_hypergraph()

        # Update each claim with its propagated negative log
        for claim in hypergraph['claims']:
            claim_id = claim['id']
            if claim_id in propagated_logs:
                claim['propagated_negative_log'] = propagated_logs[claim_id]

        self._save_hypergraph(hypergraph)
