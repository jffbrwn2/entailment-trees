"""
Entailment Checker - Validates logical implications in hypergraphs.

Checks whether "if all premises are true, then the conclusion is true" holds
for each implication in the hypergraph.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from anthropic import Anthropic


class EntailmentChecker:
    """
    Checks logical entailment for implications in hypergraphs.

    Uses Claude to evaluate whether premises logically entail conclusions.
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize entailment checker.

        Args:
            model: Claude model to use for entailment checking
        """
        self.client = Anthropic()
        self.model = model

    def check_implication(
        self,
        premises: List[Dict[str, Any]],
        conclusion: Dict[str, Any],
        implication_type: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Check if premises entail the conclusion and if premise set is minimal.

        Args:
            premises: List of premise claims (each with id, text, score, reasoning)
            conclusion: Conclusion claim (with id, text, score, reasoning)
            implication_type: "AND" or "OR"

        Returns:
            (is_valid, explanation, redundant_premises) - whether entailment holds,
            why, and list of redundant premise IDs (for AND only)
        """
        # Build prompt for Claude
        premise_texts = "\n".join([
            f"- [{p['id']}] {p['text']} (Score: {p.get('score', 'N/A')}/10)"
            for p in premises
        ])

        operator = "AND" if implication_type == "AND" else "OR"

        # For AND relationships, check minimality
        minimality_instruction = ""
        if implication_type == "AND":
            minimality_instruction = """
**CRITICAL for AND relationships:** Check if the premise set is MINIMAL.
- A premise is redundant if removing it doesn't break the entailment
- The premise set should contain ONLY necessary premises
- If any premise can be removed while still reaching the conclusion, flag it

Include in your response:
REDUNDANT_PREMISES: [comma-separated list of premise IDs that are redundant, or "None"]"""

        prompt = f"""You are a logic checker. Your job is to determine whether a logical entailment is valid.

**Premises ({operator} relationship):**
{premise_texts}

**Proposed Conclusion:**
[{conclusion['id']}] {conclusion['text']} (Score: {conclusion.get('score', 'N/A')}/10)

**Question:** If all the premises are true, must the conclusion be true?

For AND relationships: All premises must be true for the conclusion to follow.
For OR relationships: At least one premise must be true for the conclusion to follow.

**Scoring context:** Scores represent confidence/truth (0=false, 10=true, 5=unsure).

Analyze this carefully:
1. Does the conclusion logically follow from the premises?
2. Are there any logical gaps?
3. Do we need intermediate claims to bridge the gap?
{minimality_instruction}

Respond in this format:
VALID: [YES/NO]
EXPLANATION: [1-2 sentence explanation]
SUGGESTIONS: [If invalid, what could fix it?]"""

        # Query Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse response
            is_valid = "VALID: YES" in response_text

            # Parse redundant premises for AND relationships
            redundant = []
            if implication_type == "AND" and "REDUNDANT_PREMISES:" in response_text:
                redundant_line = [
                    line for line in response_text.split('\n')
                    if line.startswith('REDUNDANT_PREMISES:')
                ]
                if redundant_line:
                    redundant_text = redundant_line[0].split(':', 1)[1].strip()
                    if redundant_text and redundant_text != "None":
                        # Parse comma-separated IDs
                        redundant = [r.strip() for r in redundant_text.split(',')]

            return is_valid, response_text, redundant

        except Exception as e:
            return False, f"Entailment check failed: {str(e)}", []

    def check_hypergraph(self, hypergraph_path: Path) -> Tuple[List[str], List[str]]:
        """
        Check all implications in a hypergraph.

        Args:
            hypergraph_path: Path to hypergraph.json

        Returns:
            (errors, warnings) - lists of validation messages
        """
        errors = []
        warnings = []

        try:
            with open(hypergraph_path) as f:
                hypergraph = json.load(f)
        except Exception as e:
            return [f"Failed to load hypergraph: {e}"], []

        # Build claim lookup
        claims = {c['id']: c for c in hypergraph.get('claims', [])}

        # Check each implication
        for impl in hypergraph.get('implications', []):
            impl_id = impl.get('id', 'unknown')
            premise_ids = impl.get('premises', [])
            conclusion_id = impl.get('conclusion')
            impl_type = impl.get('type', 'AND')

            # Validate references exist
            missing_premises = [pid for pid in premise_ids if pid not in claims]
            if missing_premises:
                errors.append(
                    f"Implication {impl_id}: Missing premise claims {missing_premises}"
                )
                continue

            if conclusion_id not in claims:
                errors.append(
                    f"Implication {impl_id}: Missing conclusion claim {conclusion_id}"
                )
                continue

            # Get claim objects
            premise_claims = [claims[pid] for pid in premise_ids]
            conclusion_claim = claims[conclusion_id]

            # Check entailment
            is_valid, explanation, redundant_premises = self.check_implication(
                premise_claims,
                conclusion_claim,
                impl_type
            )

            if not is_valid:
                errors.append(
                    f"Implication {impl_id} ({impl_type}): Entailment check failed\n"
                    f"  Premises: {premise_ids}\n"
                    f"  Conclusion: {conclusion_id}\n"
                    f"  {explanation}"
                )
            else:
                # Check for redundant premises (minimality violation)
                if redundant_premises:
                    errors.append(
                        f"Implication {impl_id} ({impl_type}): Premise set is not minimal\n"
                        f"  Redundant premises: {redundant_premises}\n"
                        f"  These premises can be removed without breaking the entailment.\n"
                        f"  {explanation}"
                    )

                # Valid, but add any suggestions as warnings
                if "SUGGESTIONS:" in explanation and "None" not in explanation:
                    warnings.append(
                        f"Implication {impl_id}: {explanation.split('SUGGESTIONS:')[1].strip()}"
                    )

        return errors, warnings


def check_entailment_skill(hypergraph_path: str) -> str:
    """
    Skill function for Claude to check entailment.

    Args:
        hypergraph_path: Path to hypergraph.json file

    Returns:
        Validation results as formatted string
    """
    checker = EntailmentChecker()

    path = Path(hypergraph_path)
    if not path.exists():
        return f"❌ Hypergraph not found: {hypergraph_path}"

    errors, warnings = checker.check_hypergraph(path)

    if not errors and not warnings:
        return "✓ All implications passed entailment checking!"

    result = []

    if errors:
        result.append(f"❌ {len(errors)} entailment error(s):")
        for error in errors:
            result.append(f"\n{error}")

    if warnings:
        result.append(f"\n\n⚠️  {len(warnings)} suggestion(s):")
        for warning in warnings:
            result.append(f"\n{warning}")

    return "\n".join(result)
