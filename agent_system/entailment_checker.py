"""
Entailment Checker - Validates logical implications in hypergraphs.

Checks whether "if all premises are true, then the conclusion is true" holds
for each implication in the hypergraph.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from anthropic import Anthropic
from .config import DEFAULT_CONFIG


class EntailmentChecker:
    """
    Checks logical entailment for implications in hypergraphs.

    Uses Claude to evaluate whether premises logically entail conclusions.
    """

    def __init__(self, model: Optional[str] = None):
        """
        Initialize entailment checker.

        Args:
            model: Claude model to use for entailment checking
                   (defaults to config.evaluation_model)
        """
        self.client = Anthropic()
        self.model = model or DEFAULT_CONFIG.evaluation_model

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
        # Build prompt for Claude (WITHOUT scores - only logical relationships matter)
        premise_texts = "\n".join([
            f"- [{p['id']}] {p['text']}"
            for p in premises
        ])

        operator = "AND" if implication_type == "AND" else "OR"

        # For AND relationships, check minimality and non-degeneracy
        minimality_instruction = ""
        if implication_type == "AND":
            minimality_instruction = """
**CRITICAL for AND relationships:** Check two properties:

1. **MINIMAL premise set**: A premise is redundant if removing it doesn't break the entailment
   - The premise set should contain ONLY necessary premises
   - If any premise can be removed while still reaching the conclusion, flag it

2. **NON-DEGENERATE entailment**: Premises must be MORE SPECIFIC than conclusion
   - Check if conclusion entails any individual premise (if C → Pi, that's degenerate)
   - Premises should decompose/refine the conclusion, not restate it
   - This prevents trivial entailments like "C → C" or "C ∧ D → C"

Include in your response:
REDUNDANT_PREMISES: [comma-separated list of premise IDs that are redundant, or "None"]
DEGENERATE_PREMISES: [comma-separated list of premise IDs where conclusion → premise, or "None"]"""

        prompt = f"""You are a logic checker. Your job is to determine whether a logical entailment is valid.

**Premises ({operator} relationship):**
{premise_texts}

**Proposed Conclusion:**
[{conclusion['id']}] {conclusion['text']}

**Question:** If all the premises are TRUE, must the conclusion be TRUE?

For AND relationships: All premises must be true for the conclusion to follow.
For OR relationships: At least one premise must be true for the conclusion to follow.

**Important:** Ignore any scores or evidence. Focus ONLY on the logical relationship between the claim statements themselves.

Analyze this carefully:
1. Does the conclusion logically follow from the premises?
2. Are there any logical gaps?
3. Do we need intermediate claims to bridge the gap?
{minimality_instruction}

Respond using these XML tags:
<analysis>Your detailed analysis here</analysis>
<valid>YES or NO</valid>
<redundant_premises>comma-separated premise IDs, or None</redundant_premises>
<degenerate_premises>comma-separated premise IDs, or None</degenerate_premises>
<suggestions>If invalid, what could fix it? Otherwise None</suggestions>"""

        # Query Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse XML tags from response
            def extract_tag(text: str, tag: str) -> str:
                """Extract content between XML tags."""
                pattern = f'<{tag}>(.*?)</{tag}>'
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                return match.group(1).strip() if match else ""

            valid_text = extract_tag(response_text, 'valid')
            is_valid = valid_text.upper() == "YES"

            # Parse redundant and degenerate premises for AND relationships
            redundant = []
            degenerate = []

            if implication_type == "AND":
                # Parse redundant premises
                redundant_text = extract_tag(response_text, 'redundant_premises')
                if redundant_text and redundant_text.lower() != "none":
                    redundant = [r.strip() for r in redundant_text.split(',') if r.strip()]

                # Parse degenerate premises
                degenerate_text = extract_tag(response_text, 'degenerate_premises')
                if degenerate_text and degenerate_text.lower() != "none":
                    degenerate = [d.strip() for d in degenerate_text.split(',') if d.strip()]

            # Combine redundant and degenerate into single list for error reporting
            all_problematic = redundant + degenerate
            return is_valid, response_text, all_problematic

        except Exception as e:
            return False, f"Entailment check failed: {str(e)}", []

    def check_hypergraph(
        self,
        hypergraph_path: Path,
        force_check: bool = False,
        implication_ids: Optional[List[str]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Check implications in a hypergraph that need checking.

        Args:
            hypergraph_path: Path to hypergraph.json
            force_check: If True, check all implications (or all in implication_ids).
                        If False, only check implications that haven't been checked
                        or where premises have been modified since last check.
            implication_ids: Optional list of specific implication IDs to check.
                            If provided, only checks these implications.

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

        # Track which implications were checked and their results
        check_results = {}  # impl_id -> {status, explanation}

        # Check each implication
        for impl in hypergraph.get('implications', []):
            impl_id = impl.get('id', 'unknown')
            premise_ids = impl.get('premises', [])
            conclusion_id = impl.get('conclusion')
            impl_type = impl.get('type', 'AND')

            # Filter by specific implication IDs if provided
            if implication_ids is not None and impl_id not in implication_ids:
                continue  # Skip this implication

            # Determine if this implication needs checking
            needs_checking = force_check
            if not needs_checking:
                last_checked = impl.get('last_checked')
                if last_checked is None:
                    # Never been checked
                    needs_checking = True
                else:
                    # Check if any premise has been modified since last check
                    from dateutil import parser
                    last_checked_dt = parser.isoparse(last_checked)

                    for pid in premise_ids + [conclusion_id]:
                        if pid in claims:
                            modified_at = claims[pid].get('modified_at')
                            if modified_at:
                                modified_dt = parser.isoparse(modified_at)
                                if modified_dt > last_checked_dt:
                                    needs_checking = True
                                    break

            if not needs_checking:
                continue  # Skip this implication

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

            # Determine status
            if not is_valid:
                status = "failed"
            elif redundant_premises:
                status = "failed"  # Issues with premise set
            else:
                status = "passed"

            # Store result
            check_results[impl_id] = {
                'status': status,
                'explanation': explanation
            }

            if not is_valid:
                errors.append(
                    f"Implication {impl_id} ({impl_type}): Entailment check failed\n"
                    f"  Premises: {premise_ids}\n"
                    f"  Conclusion: {conclusion_id}\n"
                    f"  {explanation}"
                )
            else:
                # Check for problematic premises (redundant or degenerate)
                if redundant_premises:
                    errors.append(
                        f"Implication {impl_id} ({impl_type}): Premise set has issues\n"
                        f"  Problematic premises: {redundant_premises}\n"
                        f"  (May be redundant or degenerate - check explanation)\n"
                        f"  {explanation}"
                    )

                # Valid, but add any suggestions as warnings
                if "SUGGESTIONS:" in explanation and "None" not in explanation:
                    warnings.append(
                        f"Implication {impl_id}: {explanation.split('SUGGESTIONS:')[1].strip()}"
                    )

        # Update check results for implications that were checked
        if check_results:
            from datetime import datetime
            timestamp = datetime.now().isoformat()

            # Update implications with check results
            for impl in hypergraph.get('implications', []):
                impl_id = impl.get('id')
                if impl_id in check_results:
                    impl['last_checked'] = timestamp
                    impl['entailment_status'] = check_results[impl_id]['status']
                    impl['entailment_explanation'] = check_results[impl_id]['explanation']

            # Save updated hypergraph
            try:
                with open(hypergraph_path, 'w') as f:
                    json.dump(hypergraph, f, indent=2)
            except Exception as e:
                warnings.append(f"Failed to update check results: {e}")

        return errors, warnings


def check_entailment_skill(
    hypergraph_path: str,
    force_check: bool = False,
    implication_ids: Optional[str] = None
) -> str:
    """
    Skill function for Claude to check entailment.

    Args:
        hypergraph_path: Path to hypergraph.json file
        force_check: If True, re-check all implications even if already checked
        implication_ids: Comma-separated list of specific implication IDs to check (e.g., "i1,i3,i5")

    Returns:
        Validation results as formatted string
    """
    checker = EntailmentChecker()

    path = Path(hypergraph_path)
    if not path.exists():
        return f"❌ Hypergraph not found: {hypergraph_path}"

    # Parse implication_ids if provided
    ids_list = None
    if implication_ids:
        ids_list = [id.strip() for id in implication_ids.split(',')]

    errors, warnings = checker.check_hypergraph(path, force_check=force_check, implication_ids=ids_list)

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
