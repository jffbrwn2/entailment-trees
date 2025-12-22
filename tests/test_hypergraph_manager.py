"""
Tests for HypergraphManager.
"""

import pytest
import json
from pathlib import Path
from agent_system.hypergraph_manager import HypergraphManager, Claim, Implication


class TestHypergraphCreation:
    """Test creating new approaches and hypergraphs."""

    def test_create_approach(self, test_approach_dir):
        """Test creating a new approach."""
        mgr = HypergraphManager(test_approach_dir)
        hypergraph = mgr.create_approach(
            name="Test Approach",
            initial_claim="Test hypothesis",
            description="Test description"
        )

        # Check structure
        assert "metadata" in hypergraph
        assert "claims" in hypergraph
        assert "implications" in hypergraph

        # Check metadata
        assert hypergraph["metadata"]["name"] == "Test Approach"
        assert hypergraph["metadata"]["description"] == "Test description"

        # Check initial claim
        assert len(hypergraph["claims"]) == 1
        assert hypergraph["claims"][0]["id"] == "hypothesis"
        assert hypergraph["claims"][0]["text"] == "Test hypothesis"

        # Check files created
        assert (test_approach_dir / "hypergraph.json").exists()
        assert (test_approach_dir / "README.md").exists()
        assert (test_approach_dir / "simulations").exists()

        # Check catalog updated
        catalog_path = Path(__file__).parent.parent / "backend" / "static" / "hypergraph_catalog.json"
        if catalog_path.exists():
            with open(catalog_path) as f:
                catalog = json.load(f)
            # Should have added our test approach
            approach_names = [a['name'] for a in catalog.get('approaches', [])]
            assert "Test Approach" in approach_names

    def test_create_approach_updates_timestamp(self, test_approach_dir):
        """Test that timestamps are set correctly."""
        mgr = HypergraphManager(test_approach_dir)
        hypergraph = mgr.create_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        assert "created" in hypergraph["metadata"]
        assert "last_updated" in hypergraph["metadata"]


class TestClaimOperations:
    """Test adding and updating claims."""

    def test_add_claim(self, hypergraph_manager):
        """Test adding a new claim."""
        # Create initial hypergraph
        hypergraph_manager.create_approach("Test", "Hypothesis")

        # Add claim
        claim = Claim(
            id="c1",
            text="Test claim",
            score=7.5,
            reasoning="Test reasoning"
        )
        claim_id = hypergraph_manager.add_claim(claim)

        assert claim_id == "c1"

        # Verify claim was added
        hypergraph = hypergraph_manager.load_hypergraph()
        assert len(hypergraph["claims"]) == 2  # hypothesis + c1

        added_claim = next(c for c in hypergraph["claims"] if c["id"] == "c1")
        assert added_claim["text"] == "Test claim"
        assert added_claim["score"] == 7.5
        assert added_claim["reasoning"] == "Test reasoning"

    def test_add_claim_with_evidence(self, hypergraph_manager):
        """Test adding claim with evidence."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        claim = Claim(
            id="c1",
            text="Claim with evidence",
            score=8.0,
            reasoning="Based on simulation",
            evidence=[{
                "type": "simulation",
                "source": "test.py",
                "lines": "1-10",
                "code": "test code"
            }]
        )
        hypergraph_manager.add_claim(claim)

        hypergraph = hypergraph_manager.load_hypergraph()
        added_claim = next(c for c in hypergraph["claims"] if c["id"] == "c1")
        assert "evidence" in added_claim
        assert len(added_claim["evidence"]) == 1
        assert added_claim["evidence"][0]["type"] == "simulation"

    def test_add_claim_with_uncertainties_and_tags(self, hypergraph_manager):
        """Test adding claim with uncertainties and tags."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        claim = Claim(
            id="c1",
            text="Uncertain claim",
            score=5.0,
            reasoning="Needs investigation",
            uncertainties=["Unknown parameter X", "Unclear interaction"],
            tags=["CRITICAL_BLOCKER"]
        )
        hypergraph_manager.add_claim(claim)

        hypergraph = hypergraph_manager.load_hypergraph()
        added_claim = next(c for c in hypergraph["claims"] if c["id"] == "c1")
        assert added_claim["uncertainties"] == ["Unknown parameter X", "Unclear interaction"]
        assert added_claim["tags"] == ["CRITICAL_BLOCKER"]

    def test_add_duplicate_claim_id_fails(self, hypergraph_manager):
        """Test that adding duplicate claim ID raises error."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        claim1 = Claim(id="c1", text="First", score=5.0, reasoning="Test")
        hypergraph_manager.add_claim(claim1)

        claim2 = Claim(id="c1", text="Second", score=6.0, reasoning="Test")
        with pytest.raises(ValueError, match="already exists"):
            hypergraph_manager.add_claim(claim2)

    def test_update_claim(self, hypergraph_manager):
        """Test updating an existing claim."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        # Add claim
        claim = Claim(id="c1", text="Original", score=5.0, reasoning="Initial")
        hypergraph_manager.add_claim(claim)

        # Update it
        hypergraph_manager.update_claim("c1", score=8.0, reasoning="Updated reasoning")

        # Verify update
        hypergraph = hypergraph_manager.load_hypergraph()
        updated_claim = next(c for c in hypergraph["claims"] if c["id"] == "c1")
        assert updated_claim["score"] == 8.0
        assert updated_claim["reasoning"] == "Updated reasoning"
        assert updated_claim["text"] == "Original"  # Unchanged

    def test_update_nonexistent_claim_fails(self, hypergraph_manager):
        """Test that updating non-existent claim raises error."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        with pytest.raises(ValueError, match="not found"):
            hypergraph_manager.update_claim("nonexistent", score=5.0)

    def test_get_claim(self, hypergraph_manager):
        """Test retrieving a specific claim."""
        hypergraph_manager.create_approach("Test", "Hypothesis")
        claim = Claim(id="c1", text="Test", score=5.0, reasoning="Test")
        hypergraph_manager.add_claim(claim)

        retrieved = hypergraph_manager.get_claim("c1")
        assert retrieved is not None
        assert retrieved["id"] == "c1"
        assert retrieved["text"] == "Test"

    def test_get_nonexistent_claim_returns_none(self, hypergraph_manager):
        """Test that getting non-existent claim returns None."""
        hypergraph_manager.create_approach("Test", "Hypothesis")
        assert hypergraph_manager.get_claim("nonexistent") is None


class TestImplicationOperations:
    """Test adding implications (hyperedges)."""

    def test_add_implication(self, hypergraph_manager):
        """Test adding an implication."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        # Add premises
        c1 = Claim(id="c1", text="Premise 1", score=8.0, reasoning="Test")
        c2 = Claim(id="c2", text="Premise 2", score=7.0, reasoning="Test")
        hypergraph_manager.add_claim(c1)
        hypergraph_manager.add_claim(c2)

        # Add implication
        impl = Implication(
            id="i1",
            premises=["c1", "c2"],
            conclusion="hypothesis",
            type="AND",
            reasoning="Logical connection"
        )
        impl_id = hypergraph_manager.add_implication(impl)

        assert impl_id == "i1"

        # Verify
        hypergraph = hypergraph_manager.load_hypergraph()
        assert len(hypergraph["implications"]) == 1
        added_impl = hypergraph["implications"][0]
        assert added_impl["premises"] == ["c1", "c2"]
        assert added_impl["conclusion"] == "hypothesis"
        assert added_impl["type"] == "AND"

    def test_add_implication_with_invalid_premise_fails(self, hypergraph_manager):
        """Test that referencing non-existent premise fails."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        impl = Implication(
            id="i1",
            premises=["nonexistent"],
            conclusion="hypothesis",
            type="AND",
            reasoning="Test"
        )

        with pytest.raises(ValueError, match="does not exist"):
            hypergraph_manager.add_implication(impl)

    def test_add_implication_with_invalid_conclusion_fails(self, hypergraph_manager):
        """Test that referencing non-existent conclusion fails."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        c1 = Claim(id="c1", text="Premise", score=5.0, reasoning="Test")
        hypergraph_manager.add_claim(c1)

        impl = Implication(
            id="i1",
            premises=["c1"],
            conclusion="nonexistent",
            type="AND",
            reasoning="Test"
        )

        with pytest.raises(ValueError, match="does not exist"):
            hypergraph_manager.add_implication(impl)

    def test_add_duplicate_implication_id_fails(self, hypergraph_manager):
        """Test that duplicate implication ID raises error."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        c1 = Claim(id="c1", text="Premise", score=5.0, reasoning="Test")
        hypergraph_manager.add_claim(c1)

        impl1 = Implication(id="i1", premises=["c1"], conclusion="hypothesis", type="AND", reasoning="Test")
        hypergraph_manager.add_implication(impl1)

        impl2 = Implication(id="i1", premises=["c1"], conclusion="hypothesis", type="OR", reasoning="Test")
        with pytest.raises(ValueError, match="already exists"):
            hypergraph_manager.add_implication(impl2)


class TestStatistics:
    """Test hypergraph statistics."""

    def test_get_stats(self, hypergraph_manager):
        """Test getting hypergraph statistics."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        # Add some claims
        hypergraph_manager.add_claim(Claim(id="c1", text="Test", score=8.0, reasoning="Test"))
        hypergraph_manager.add_claim(Claim(id="c2", text="Test", score=6.0, reasoning="Test"))
        hypergraph_manager.add_claim(Claim(
            id="c3",
            text="Blocker",
            score=2.0,
            reasoning="Critical issue",
            tags=["CRITICAL_BLOCKER"]
        ))

        # Add implication
        hypergraph_manager.add_implication(Implication(
            id="i1",
            premises=["c1", "c2"],
            conclusion="c3",
            type="AND",
            reasoning="Test"
        ))

        stats = hypergraph_manager.get_stats()

        assert stats["num_claims"] == 4  # hypothesis + 3 added
        assert stats["num_implications"] == 1
        assert stats["min_score"] == 2.0
        assert stats["max_score"] == 8.0
        assert stats["critical_blockers"] == 1


class TestIDGeneration:
    """Test automatic ID generation."""

    def test_generate_next_claim_id(self, hypergraph_manager):
        """Test generating next claim ID."""
        hypergraph_manager.create_approach("Test", "Hypothesis")

        next_id = hypergraph_manager.generate_next_id('c')
        assert next_id == "c1"

        # Add claim and check next
        hypergraph_manager.add_claim(Claim(id="c1", text="Test", score=5.0, reasoning="Test"))
        next_id = hypergraph_manager.generate_next_id('c')
        assert next_id == "c2"

    def test_generate_next_implication_id(self, hypergraph_manager):
        """Test generating next implication ID."""
        hypergraph_manager.create_approach("Test", "Hypothesis")
        hypergraph_manager.add_claim(Claim(id="c1", text="Test", score=5.0, reasoning="Test"))

        next_id = hypergraph_manager.generate_next_id('i')
        assert next_id == "i1"

        # Add implication and check next
        hypergraph_manager.add_implication(Implication(
            id="i1",
            premises=["c1"],
            conclusion="hypothesis",
            type="AND",
            reasoning="Test"
        ))
        next_id = hypergraph_manager.generate_next_id('i')
        assert next_id == "i2"


class TestFileOperations:
    """Test file loading and saving."""

    def test_load_hypergraph(self, hypergraph_manager):
        """Test loading hypergraph from file."""
        hypergraph_manager.create_approach("Test", "Hypothesis")
        loaded = hypergraph_manager.load_hypergraph()

        assert "metadata" in loaded
        assert "claims" in loaded
        assert "implications" in loaded

    def test_load_nonexistent_hypergraph_fails(self, test_approach_dir):
        """Test that loading non-existent hypergraph raises error."""
        mgr = HypergraphManager(test_approach_dir)

        with pytest.raises(FileNotFoundError):
            mgr.load_hypergraph()

    def test_save_updates_timestamp(self, hypergraph_manager):
        """Test that saving updates last_updated timestamp."""
        hypergraph_manager.create_approach("Test", "Hypothesis")
        original = hypergraph_manager.load_hypergraph()
        original_timestamp = original["metadata"]["last_updated"]

        # Modify and reload
        hypergraph_manager.add_claim(Claim(id="c1", text="Test", score=5.0, reasoning="Test"))
        updated = hypergraph_manager.load_hypergraph()

        # Timestamp should be updated (or at least not earlier)
        assert updated["metadata"]["last_updated"] >= original_timestamp
