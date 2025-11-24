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
    Evaluate a claim based on its evidence.

    Score the claim according to how well the evidence supports it.
    If no evidence exists, score defaults to 0.
    Tracks when evidence was last modified.

    Args:
        hypergraph_path: Path to hypergraph.json file
        claim_id: ID of claim to evaluate (e.g., "c1")
        score: Score 0-10 based on evidence strength (0=false/no evidence, 10=true, 5=unsure)
        reasoning: Why this score was assigned based on the evidence
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

        # Check if evidence is being updated
        evidence_changed = False
        if evidence:
            try:
                evidence_list = json.loads(evidence)
                # Check if evidence actually changed
                old_evidence = claim.get('evidence', [])
                if evidence_list != old_evidence:
                    claim['evidence'] = evidence_list
                    evidence_changed = True
            except json.JSONDecodeError as e:
                return f"❌ Invalid evidence JSON: {e}"

        # If no evidence provided and claim has no existing evidence, score must be 0
        current_evidence = claim.get('evidence', [])
        if not current_evidence and not evidence:
            if score != 0:
                return f"❌ Claim has no evidence, score must be 0 (got {score}). Add evidence first."

        # Update last_evidence_modified timestamp if evidence changed
        if evidence_changed:
            claim['last_evidence_modified'] = datetime.now().isoformat()

        # Update claim score and reasoning
        claim['score'] = score
        claim['reasoning'] = reasoning
        claim['modified_at'] = datetime.now().isoformat()

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
