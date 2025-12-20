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
from .path_utils import resolve_path
from .runtime_settings import get_settings


def _validate_evidence_format(evidence_item: dict) -> tuple[bool, Optional[str]]:
    """
    Validate evidence item format according to hypergraph schema.

    Args:
        evidence_item: Evidence dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check type field
    if 'type' not in evidence_item:
        return False, "Missing required field 'type'"

    evidence_type = evidence_item['type']
    allowed_types = ['simulation', 'literature', 'calculation']

    if evidence_type not in allowed_types:
        return False, f"Invalid evidence type '{evidence_type}'. Must be one of: {', '.join(allowed_types)}"

    # Type-specific validation
    if evidence_type == 'simulation':
        required = ['source', 'lines', 'code']
        for field in required:
            if field not in evidence_item:
                return False, f"Simulation evidence missing required field '{field}'"

    elif evidence_type == 'literature':
        required = ['source', 'reference_text']
        for field in required:
            if field not in evidence_item:
                return False, f"Literature evidence missing required field '{field}'"

    elif evidence_type == 'calculation':
        required = ['equations', 'program']
        for field in required:
            if field not in evidence_item:
                return False, f"Calculation evidence missing required field '{field}'"

    return True, None


def add_evidence_skill(
    hypergraph_path: str,
    claim_id: str,
    evidence: str
) -> str:
    """
    Add evidence to a claim in the hypergraph.

    Validates evidence format and adds it to the claim's evidence list.
    Updates last_evidence_modified timestamp.

    Args:
        hypergraph_path: Path to hypergraph.json file (can be relative to approach dir)
        claim_id: ID of claim to add evidence to (e.g., "c1")
        evidence: JSON string of evidence item or array of evidence items

    Returns:
        Confirmation message or error
    """
    try:
        # Resolve path (handles relative paths against approach directory)
        path = resolve_path(hypergraph_path)
        if not path.exists():
            return f"❌ Hypergraph not found: {hypergraph_path} (resolved to {path})"

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

        # Parse evidence JSON
        try:
            evidence_data = json.loads(evidence)
        except json.JSONDecodeError as e:
            return f"❌ Invalid evidence JSON: {e}"

        # Handle both single item and array
        if isinstance(evidence_data, dict):
            evidence_items = [evidence_data]
        elif isinstance(evidence_data, list):
            evidence_items = evidence_data
        else:
            return f"❌ Evidence must be a JSON object or array of objects"

        # Validate all evidence items
        for i, item in enumerate(evidence_items):
            is_valid, error = _validate_evidence_format(item)
            if not is_valid:
                return f"❌ Evidence item {i}: {error}"

        # Add evidence to claim
        if 'evidence' not in claim:
            claim['evidence'] = []

        claim['evidence'].extend(evidence_items)

        # Update timestamps
        claim['last_evidence_modified'] = datetime.now().isoformat()
        claim['modified_at'] = datetime.now().isoformat()
        hypergraph['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")

        # Save hypergraph
        with open(path, 'w') as f:
            json.dump(hypergraph, f, indent=2)

        count = len(evidence_items)
        item_word = "item" if count == 1 else "items"
        return f"✓ Added {count} evidence {item_word} to claim {claim_id}"

    except Exception as e:
        return f"❌ Error adding evidence: {e}"


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
    from .api_keys import get_api_key
    api_key = get_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set (via environment variable or session)")

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

    # Get evaluator model from runtime settings
    settings = get_settings()
    model = settings.evaluator_model or DEFAULT_CONFIG.evaluation_model

    # Call Claude with configured model
    response = client.messages.create(
        model=model,
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
    claim_id: str
) -> str:
    """
    Evaluate a claim based on its existing evidence using Claude.

    Claude analyzes the evidence already attached to the claim and determines:
    - Score (0-10): How well the evidence supports the claim
    - Reasoning: Why this score was assigned

    If no evidence exists, score defaults to 0.
    Use add_evidence_skill first to add evidence before evaluating.

    Args:
        hypergraph_path: Path to hypergraph.json file (can be relative to approach dir)
        claim_id: ID of claim to evaluate (e.g., "c1")

    Returns:
        Confirmation message with score and reasoning, or error
    """
    try:
        # Resolve path (handles relative paths against approach directory)
        path = resolve_path(hypergraph_path)
        if not path.exists():
            return f"❌ Hypergraph not found: {hypergraph_path} (resolved to {path})"

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

        # Get existing evidence
        evidence_list = claim.get('evidence', [])

        # If no evidence exists, score = 0
        if not evidence_list:
            score = 0.0
            reasoning = "No evidence provided for this claim. Use add_evidence to add evidence first."
        else:
            # Use Claude to evaluate the evidence and determine score
            try:
                score, reasoning = _evaluate_evidence_with_claude(
                    claim_text=claim['text'],
                    evidence_list=evidence_list
                )
            except Exception as e:
                return f"❌ Error evaluating evidence with Claude: {e}"

        # Update claim with evaluated score and reasoning
        claim['score'] = score
        claim['reasoning'] = reasoning
        claim['modified_at'] = datetime.now().isoformat()

        # Update last_updated timestamp
        hypergraph['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d")

        # Save hypergraph
        with open(path, 'w') as f:
            json.dump(hypergraph, f, indent=2)

        return f"✓ Evaluated claim {claim_id}: score={score}/10\n{reasoning}"

    except Exception as e:
        return f"❌ Error evaluating claim: {e}"
