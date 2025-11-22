"""
Integration tests for Edison Scientific with entailment hypergraph system.

These tests require a valid EDISON_API_KEY environment variable.
They make real API calls to Edison Scientific.

Run with: pytest tests/test_edison_integration.py -v -s
Skip with: pytest tests/ -v --ignore=tests/test_edison_integration.py
"""

import pytest
import os
from pathlib import Path
from edison_client import EdisonClient, JobNames
from agent_system.hypergraph_manager import HypergraphManager, Claim


# Skip all tests in this module if no API key is set
pytestmark = pytest.mark.skipif(
    not os.getenv("EDISON_API_KEY"),
    reason="EDISON_API_KEY not set - skipping Edison integration tests"
)


class TestEdisonLiteratureSearch:
    """Test Edison literature search integration with hypergraph."""

    @pytest.mark.anyio
    async def test_literature_search_basic(self):
        """Test basic literature search functionality."""
        api_key = os.getenv("EDISON_API_KEY")
        client = EdisonClient(api_key=api_key)

        print("\n📚 Testing Edison literature search...")

        task_data = {
            "name": JobNames.LITERATURE,
            "query": "What is the typical signal-to-noise ratio in EEG recordings?"
        }

        print(f"Query: {task_data['query']}")
        response = await client.arun_tasks_until_done(task_data)

        # Handle list response (Edison sometimes returns list)
        if isinstance(response, list):
            response = response[0]

        # Verify response structure
        assert hasattr(response, 'answer')
        assert response.answer is not None
        assert len(response.answer) > 0

        print(f"\n✓ Got answer ({len(response.answer)} chars)")
        print(f"  First 200 chars: {response.answer[:200]}...")

    @pytest.mark.anyio
    async def test_literature_search_for_claim_evidence(self, test_approach_dir):
        """Test using literature search to gather evidence for a claim."""
        # Set up hypergraph with a claim needing evidence
        mgr = HypergraphManager(test_approach_dir)
        mgr.create_approach(
            name="EEG Signal Detection",
            initial_claim="EEG signals can be detected non-invasively",
            description="Test approach for Edison integration"
        )

        # Add a claim that needs literature evidence
        claim = Claim(
            id="c1",
            text="Typical EEG signal amplitude is 10-100 microvolts",
            score=5.0,  # Unsure - needs evidence
            reasoning="Need to verify typical EEG signal ranges from literature"
        )
        mgr.add_claim(claim)

        # Use Edison to find evidence
        api_key = os.getenv("EDISON_API_KEY")
        client = EdisonClient(api_key=api_key)

        print("\n🔍 Searching literature for EEG signal amplitudes...")
        task_data = {
            "name": JobNames.LITERATURE,
            "query": "What is the typical amplitude range of EEG signals in microvolts?"
        }

        response = await client.arun_tasks_until_done(task_data)
        if isinstance(response, list):
            response = response[0]

        # Verify we got useful information
        assert response.answer is not None
        answer_lower = response.answer.lower()

        # Check that answer mentions relevant terms
        relevant_terms = ["eeg", "microvolt", "amplitude", "signal"]
        found_terms = [term for term in relevant_terms if term in answer_lower]

        print(f"\n✓ Found {len(found_terms)}/{len(relevant_terms)} relevant terms")
        print(f"  Answer preview: {response.answer[:300]}...")

        assert len(found_terms) >= 2, f"Answer should mention EEG signal properties"


class TestEdisonPrecedentSearch:
    """Test Edison precedent search integration with hypergraph."""

    @pytest.mark.anyio
    async def test_precedent_search_basic(self):
        """Test basic precedent search functionality."""
        api_key = os.getenv("EDISON_API_KEY")
        client = EdisonClient(api_key=api_key)

        print("\n🔎 Testing Edison precedent search...")

        task_data = {
            "name": JobNames.PRECEDENT,
            "query": "Has ultrasound been used to modulate neural activity?"
        }

        print(f"Query: {task_data['query']}")
        response = await client.arun_tasks_until_done(task_data)

        # Handle list response
        if isinstance(response, list):
            response = response[0]

        # Verify response structure
        assert hasattr(response, 'answer')
        assert response.answer is not None
        assert len(response.answer) > 0

        print(f"\n✓ Got answer ({len(response.answer)} chars)")
        print(f"  First 200 chars: {response.answer[:200]}...")

    @pytest.mark.anyio
    async def test_precedent_search_for_novelty_assessment(self, test_approach_dir):
        """Test using precedent search to assess novelty of an approach."""
        # Set up hypergraph with novel approach claim
        mgr = HypergraphManager(test_approach_dir)
        mgr.create_approach(
            name="Novel Neural Interface",
            initial_claim="Acoustic modulation of neural activity via ultrasound is feasible",
            description="Test approach for precedent checking"
        )

        # Add a novelty claim
        novelty_claim = Claim(
            id="novelty",
            text="Using focused ultrasound for neural stimulation is novel",
            score=5.0,  # Unknown - needs precedent check
            reasoning="Need to check if this approach has been attempted before"
        )
        mgr.add_claim(novelty_claim)

        # Use Edison to check for precedents
        api_key = os.getenv("EDISON_API_KEY")
        client = EdisonClient(api_key=api_key)

        print("\n🔍 Checking for precedents of ultrasound neural stimulation...")
        task_data = {
            "name": JobNames.PRECEDENT,
            "query": "Has focused ultrasound been used for neural stimulation or neuromodulation?"
        }

        response = await client.arun_tasks_until_done(task_data)
        if isinstance(response, list):
            response = response[0]

        # Verify we got useful precedent information
        assert response.answer is not None
        answer_lower = response.answer.lower()

        # Check that answer addresses precedent
        precedent_indicators = ["yes", "no", "has been", "have been", "prior", "previous"]
        found_indicators = [ind for ind in precedent_indicators if ind in answer_lower]

        print(f"\n✓ Found precedent indicators: {found_indicators}")
        print(f"  Answer preview: {response.answer[:300]}...")

        assert len(found_indicators) >= 1, "Answer should indicate whether precedents exist"


class TestEdisonHypergraphWorkflow:
    """Test complete workflow of using Edison with hypergraph system."""

    @pytest.mark.anyio
    async def test_complete_evidence_gathering_workflow(self, test_approach_dir):
        """Test a complete workflow: create claims, gather evidence with Edison, update scores."""
        # Create approach
        mgr = HypergraphManager(test_approach_dir)
        mgr.create_approach(
            name="Test Evidence Workflow",
            initial_claim="Hypothesis to test",
            description="Complete workflow test"
        )

        # Add claims needing evidence
        claims = [
            Claim(
                id="c1",
                text="EEG signals have specific frequency bands",
                score=5.0,
                reasoning="Need evidence on EEG frequency characteristics"
            ),
            Claim(
                id="c2",
                text="Brain activity produces measurable electrical fields",
                score=5.0,
                reasoning="Need evidence on neural electrical activity"
            )
        ]

        for claim in claims:
            mgr.add_claim(claim)

        print(f"\n✓ Created hypergraph with {len(claims)} claims needing evidence")

        # Use Edison to gather evidence for first claim
        api_key = os.getenv("EDISON_API_KEY")
        client = EdisonClient(api_key=api_key)

        print("\n📚 Gathering evidence with Edison...")
        task_data = {
            "name": JobNames.LITERATURE,
            "query": "What are the main frequency bands in EEG signals (delta, theta, alpha, beta, gamma)?"
        }

        response = await client.arun_tasks_until_done(task_data)
        if isinstance(response, list):
            response = response[0]

        print(f"✓ Got evidence: {len(response.answer)} chars")

        # Verify evidence is relevant
        answer_lower = response.answer.lower()
        frequency_bands = ["delta", "theta", "alpha", "beta", "gamma"]
        found_bands = [band for band in frequency_bands if band in answer_lower]

        print(f"✓ Found {len(found_bands)}/5 EEG frequency bands mentioned")
        assert len(found_bands) >= 3, "Should find most common EEG frequency bands"

        # In a real workflow, you would now:
        # 1. Parse the Edison response
        # 2. Extract key facts and citations
        # 3. Update claim scores based on evidence
        # 4. Add evidence to claim's evidence list

        print("\n✓ Complete workflow test passed")


if __name__ == "__main__":
    # Run with: python tests/test_edison_integration.py
    pytest.main([__file__, "-v", "-s"])
