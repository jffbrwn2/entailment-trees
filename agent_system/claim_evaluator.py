"""
Claim Evaluator - Tool for evaluating claims with evidence and scoring.

Separates claim evaluation (gathering evidence, assigning scores) from
logical entailment (building the graph structure).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def evaluate_claim_skill(
    hypergraph_path: str,
    claim_id: str,
    score: float,
    reasoning: str,
    evidence: Optional[str] = None,
    uncertainties: Optional[str] = None,
    tags: Optional[str] = None
) -> str:
    """
    Evaluate a claim by assigning a score and evidence.

    This is Phase 2 of the process - after building logical structure,
    evaluate individual claims based on evidence.

    Args:
        hypergraph_path: Path to hypergraph.json file
        claim_id: ID of claim to evaluate (e.g., "c1")
        score: Score 0-10 (0=false, 10=true, 5=unsure)
        reasoning: Why this score was assigned
        evidence: JSON array string of evidence items (optional)
        uncertainties: Comma-separated list of uncertainties (optional)
        tags: Comma-separated list of tags like "CRITICAL_BLOCKER" (optional)

    Returns:
        Confirmation message or error
    """
    try:
        path = Path(hypergraph_path)
        if not path.exists():
            return f"❌ Hypergraph not found: {hypergraph_path}"

        # Load hypergraph
        with open(path) as f:
            hypergraph = json.load(f)

        # Find the claim
        claim = None
        for c in hypergraph.get('claims', []):
            if c['id'] == claim_id:
                claim = c
                break

        if not claim:
            return f"❌ Claim '{claim_id}' not found in hypergraph"

        # Validate score
        if not (0 <= score <= 10):
            return f"❌ Score must be between 0 and 10, got {score}"

        # Update claim
        claim['score'] = score
        claim['reasoning'] = reasoning
        claim['modified_at'] = datetime.now().isoformat()

        # Parse and update evidence if provided
        if evidence:
            try:
                evidence_list = json.loads(evidence)
                claim['evidence'] = evidence_list
            except json.JSONDecodeError as e:
                return f"❌ Invalid evidence JSON: {e}"

        # Parse and update uncertainties if provided
        if uncertainties:
            claim['uncertainties'] = [u.strip() for u in uncertainties.split(',')]

        # Parse and update tags if provided
        if tags:
            claim['tags'] = [t.strip() for t in tags.split(',')]

        # Update last_updated timestamp
        hypergraph['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")

        # Save hypergraph
        with open(path, 'w') as f:
            json.dump(hypergraph, f, indent=2)

        return f"✓ Evaluated claim {claim_id}: score={score}/10\n{reasoning}"

    except Exception as e:
        return f"❌ Error evaluating claim: {e}"
