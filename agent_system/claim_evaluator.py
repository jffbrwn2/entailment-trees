"""
Claim Evaluator - Tool for evaluating claims with evidence and scoring.

Uses Claude to analyze evidence and determine scores autonomously.
Separates claim evaluation (gathering evidence, assigning scores) from
logical entailment (building the graph structure).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from anthropic import Anthropic
import os
from .config import DEFAULT_CONFIG


def _evaluate_evidence_with_claude(claim_text: str, evidence_list: list) -> tuple[float, str]:
    """
    Use Claude to evaluate evidence and determine claim score.

    Args:
        claim_text: The claim being evaluated
        evidence_list: List of evidence items

    Returns:
        Tuple of (score, reasoning)
    """
    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = Anthropic(api_key=api_key)

    # Format evidence for Claude
    evidence_text = json.dumps(evidence_list, indent=2)

    # Prompt for Claude
    prompt = f"""Evaluate the following claim based on the provided evidence.

Claim: "{claim_text}"

Evidence:
{evidence_text}

Your task:
1. Analyze the evidence carefully
2. Determine how well the evidence supports the claim
3. Assign a score from 0-10 where:
   - 0 = Evidence disproves the claim or shows it's clearly false
   - 1-3 = Evidence strongly suggests the claim is unlikely
   - 4-6 = Evidence is mixed or inconclusive
   - 7-8 = Evidence supports the claim but with some limitations
   - 9-10 = Evidence strongly supports the claim

4. Provide clear reasoning for your score

Respond in this exact format:
SCORE: [number 0-10]
REASONING: [your explanation]"""

    # Call Claude with configured model
    response = client.messages.create(
        model=DEFAULT_CONFIG.evaluation_model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    # Parse response
    response_text = response.content[0].text

    # Extract score and reasoning
    try:
        lines = response_text.strip().split('\n')
        score_line = next(line for line in lines if line.startswith('SCORE:'))
        score = float(score_line.split(':')[1].strip())

        reasoning_start = response_text.index('REASONING:') + len('REASONING:')
        reasoning = response_text[reasoning_start:].strip()

        # Validate score
        if not (0 <= score <= 10):
            raise ValueError(f"Score {score} out of range")

        return score, reasoning

    except Exception as e:
        raise ValueError(f"Failed to parse Claude response: {e}\nResponse: {response_text}")


def evaluate_claim_skill(
    hypergraph_path: str,
    claim_id: str,
    evidence: Optional[str] = None,
    uncertainties: Optional[str] = None,
    tags: Optional[str] = None
) -> str:
    """
    Evaluate a claim based on its evidence using Claude.

    Claude analyzes the evidence and determines:
    - Score (0-10): How well the evidence supports the claim
    - Reasoning: Why this score was assigned

    If no evidence exists, score defaults to 0.
    Tracks when evidence was last modified.

    Args:
        hypergraph_path: Path to hypergraph.json file
        claim_id: ID of claim to evaluate (e.g., "c1")
        evidence: JSON array string of evidence items (required to score > 0)
        uncertainties: Comma-separated list of uncertainties (optional)
        tags: Comma-separated list of tags like "CRITICAL_BLOCKER" (optional)

    Returns:
        Confirmation message with score and reasoning, or error
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

        # Parse and update evidence if provided
        evidence_changed = False
        evidence_list = []
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
        else:
            # Use existing evidence if any
            evidence_list = claim.get('evidence', [])

        # If no evidence exists, score = 0
        if not evidence_list:
            score = 0.0
            reasoning = "No evidence provided for this claim"
        else:
            # Use Claude to evaluate the evidence and determine score
            try:
                score, reasoning = _evaluate_evidence_with_claude(
                    claim_text=claim['text'],
                    evidence_list=evidence_list
                )
            except Exception as e:
                return f"❌ Error evaluating evidence with Claude: {e}"

        # Update last_evidence_modified timestamp if evidence changed
        if evidence_changed:
            claim['last_evidence_modified'] = datetime.now().isoformat()

        # Update claim with evaluated score and reasoning
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
