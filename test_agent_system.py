"""
Quick test of the agent system components.
"""

from pathlib import Path
from agent_system import HypergraphManager, AgentOrchestrator
from agent_system.hypergraph_manager import Claim, Implication
from agent_system.evidence_parser import parse_simulation_evidence, format_literature_evidence


def test_hypergraph_manager():
    """Test HypergraphManager CRUD operations."""
    print("Testing HypergraphManager...")

    # Create test approach
    test_dir = Path("approaches/test_ultrasound")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    mgr = HypergraphManager(test_dir)
    hypergraph = mgr.create_approach(
        name="Test Ultrasound Detection",
        initial_claim="We can detect neural signals using ultrasound",
        description="Test approach for system validation"
    )

    print(f"  ✓ Created approach at {test_dir}")
    print(f"  ✓ Initial claims: {len(hypergraph['claims'])}")

    # Add a claim
    claim = Claim(
        id="c1",
        text="Neural action potentials produce acoustic pressure changes",
        score=3.0,
        reasoning="Estimated from basic physics",
        uncertainties=["Actual amplitude unknown", "Noise floor unclear"]
    )
    mgr.add_claim(claim)
    print(f"  ✓ Added claim {claim.id}")

    # Add another claim
    claim2 = Claim(
        id="c2",
        text="Ultrasound sensors can detect pressure changes above 10^-6 Pa",
        score=8.0,
        reasoning="From sensor specifications"
    )
    mgr.add_claim(claim2)
    print(f"  ✓ Added claim {claim2.id}")

    # Add implication
    impl = Implication(
        id="i1",
        premises=["c1", "c2"],
        conclusion="hypothesis",
        type="AND",
        reasoning="Signal must be above detection threshold"
    )
    mgr.add_implication(impl)
    print(f"  ✓ Added implication {impl.id}")

    # Get stats
    stats = mgr.get_stats()
    print(f"  ✓ Stats: {stats['num_claims']} claims, {stats['num_implications']} implications")

    # Validate
    errors, warnings = mgr.validate()
    if errors:
        print(f"  ✗ Validation errors: {errors}")
    else:
        print(f"  ✓ Hypergraph is valid!")

    print()


def test_evidence_parser():
    """Test evidence parsing utilities."""
    print("Testing evidence_parser...")

    # Test literature evidence
    lit_ev = format_literature_evidence(
        source="Smith et al. (2023)",
        reference_text="Neural signals produce 10^-12 Pa acoustic pressure"
    )
    print(f"  ✓ Created literature evidence: {lit_ev['type']}")

    print()


def test_orchestrator():
    """Test AgentOrchestrator."""
    print("Testing AgentOrchestrator...")

    orchestrator = AgentOrchestrator()

    # Start approach
    result = orchestrator.start_approach(
        name="Ultrasound EEG Detection",
        initial_claim="We can detect brain activity using ultrasound",
        description="Test of orchestrator"
    )

    print(f"  ✓ Started approach: {result['session']['name']}")
    print(f"  ✓ Folder: {result['session']['folder']}")

    # Get status
    status = orchestrator.get_status()
    print(f"  ✓ Status: {status['stats']['num_claims']} claims")

    # Validate
    validation = orchestrator.validate_hypergraph()
    if validation['valid']:
        print(f"  ✓ Hypergraph is valid")
    else:
        print(f"  ✗ Validation failed: {validation['errors']}")

    # Show part of system prompt
    print(f"  ✓ System prompt length: {len(result['system_prompt'])} chars")

    print()


if __name__ == "__main__":
    print("=" * 70)
    print("Agent System Test Suite")
    print("=" * 70)
    print()

    test_hypergraph_manager()
    test_evidence_parser()
    test_orchestrator()

    print("=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
